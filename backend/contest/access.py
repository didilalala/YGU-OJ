"""
考试的访问控制（设计说明书 9.3、10.1）：

- 课堂考试只有班级学生能参加，公开竞赛所有登录用户都能参加；
  进入时需在允许的 IP 段内，设了口令的还需输入口令；
- 课堂考试进行中（且开启了锁定题库），学生只能访问本场考试的题目，
  不能浏览题库、做作业或查看历史代码，其他接口返回 403 与考试编号，前端据此跳转到考场。
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound

from utils.exceptions import BusinessError
from utils.request import get_client_ip

from .models import Exam, ExamParticipant

EXAM_LOCKED_CODE = 40301
IP_NOT_ALLOWED_CODE = 40302


class ExamLocked(BusinessError):
    status_code = status.HTTP_403_FORBIDDEN


def _member_exams(user):
    return Exam.objects.filter(
        is_published=True,
        class_group__members__student=user,
        class_group__members__is_removed=False,
    )


def active_exam(user):
    """学生当前正在进行、且锁定题库的考试；没有则为 None。教师与管理员不受限制。"""
    if not (user and user.is_authenticated) or user.role != user.Role.STUDENT:
        return None
    now = timezone.now()
    return (
        _member_exams(user)
        .filter(lock_problem_bank=True, start_time__lte=now, end_time__gte=now)
        .order_by("end_time")
        .first()
    )


def ensure_not_locked(user, allowed_exam_id=None):
    """考试期间访问考试以外的内容时抛出 ExamLocked。"""
    exam = active_exam(user)
    if exam is not None and exam.id != allowed_exam_id:
        raise ExamLocked(
            f"考试「{exam.title}」进行中，只能访问本场考试的题目",
            code=EXAM_LOCKED_CODE,
            data={"exam_id": exam.id, "title": exam.title},
        )


def student_exam(user, exam_id, allow_anonymous=False):
    """
    参加者可访问的考试或竞赛，否则一律视为不存在：
    - 课堂考试：已发布、且学生仍在该班级中；
    - 公开竞赛（不限班级）：已发布即可，所有登录用户都能参加；allow_anonymous 时访客也能查看。
    """
    logged_in = bool(user and user.is_authenticated)
    exam = Exam.objects.filter(pk=exam_id, is_published=True).select_related("class_group").first()
    if exam is None:
        raise NotFound("考试不存在")
    if exam.is_public:
        if not (logged_in or allow_anonymous):
            raise NotFound("考试不存在")
        return exam
    if not logged_in or not _member_exams(user).filter(pk=exam_id).exists():
        raise NotFound("考试不存在")
    return exam


def check_ip(exam, request):
    ip = get_client_ip(request)
    if not exam.ip_allowed(ip):
        raise BusinessError(f"当前 IP（{ip}）不在本场考试允许的范围内，请在指定机房参加考试", code=IP_NOT_ALLOWED_CODE)


def exam_problem(request, exam_id, problem_id, for_submit=False):
    """
    在考试中访问题目：
    - 考试进行中：须已进入考试且在允许的 IP 段内；提交时还要求未交卷；
    - 考试结束后：公布成绩后可查看题目（复盘），不能再提交。
    返回考试。
    """
    exam = student_exam(request.user, exam_id)
    if not exam.items.filter(problem_id=problem_id).exists():
        raise NotFound("该题目不在此考试中")

    status_ = exam.status_at(timezone.now())
    if status_ == "not_started":
        raise BusinessError("考试尚未开始")
    if status_ == "ended":
        if for_submit:
            raise BusinessError("考试已结束，不能再提交")
        if not exam.is_score_published:
            raise BusinessError("考试已结束，公布成绩后可查看题目")
        return exam

    participant = ExamParticipant.objects.filter(exam=exam, student=request.user).first()
    if participant is None:
        raise BusinessError("请先进入考试")
    check_ip(exam, request)
    if for_submit and participant.finished_at:
        raise BusinessError("你已交卷，不能再提交")
    return exam
