"""
普通用户绑定学号（设计说明书 4.3）。

教师导入名单时已经为学号创建了账号（用户名为学号，初始密码为学号后六位）。
普通用户若在学校名单中，可用「学号 + 初始密码」完成验证，把自己的账号升级为在校学生：

- 学号对应的导入账号必须仍是初始密码状态（学生还没有登录改过密码）；
- 普通用户账号上的全部数据（提交记录、班级、成绩、考试参加记录）转到本账号上，历史保留；
- 导入账号随后删除，学号不再作为登录用户名，之后用注册时的用户名或邮箱登录。
"""

from django.db import transaction

from account.models import StudentProfile, User
from account.throttle import clear, ensure_not_locked, record_failure
from classroom.models import ClassMember, ScoreRecord
from contest.models import ExamParticipant
from submission.models import Submission
from utils.exceptions import BusinessError

BIND_SCOPE = "bind"
# 凭据错误统一提示，不区分学号不存在与密码错误，避免探测学号
WRONG_CREDENTIALS = "学号或初始密码不正确"


def bind_student(user, student_no, initial_password):
    """把普通用户 user 绑定为学号 student_no 的在校学生，返回 user。"""
    if user.role != User.Role.REGULAR:
        raise BusinessError("当前账号已是在校学生或教师，无需绑定学号")

    ensure_not_locked(BIND_SCOPE, user.id)
    profile = StudentProfile.objects.select_related("user").filter(student_no=student_no).first()
    placeholder = profile.user if profile else None
    # 验证失败都计入锁定次数，即使学号本身不存在
    if placeholder is None or not placeholder.check_password(initial_password) or not placeholder.is_initial_password:
        record_failure(BIND_SCOPE, user.id)
        raise BusinessError(WRONG_CREDENTIALS)

    with transaction.atomic():
        placeholder = User.objects.select_for_update().get(pk=placeholder.pk)
        if not placeholder.is_initial_password:
            # 并发情况下刚被激活
            raise BusinessError(WRONG_CREDENTIALS)
        _transfer_account(placeholder, user)
        user.role = User.Role.STUDENT
        user.save(update_fields=["role"])
    clear(BIND_SCOPE, user.id)
    return user


def _transfer_account(source, target):
    """把 source（导入的学号账号）的数据转到 target，然后删除 source。"""
    assignment_ids, exam_ids = set(), set()

    # 学号账号上的成绩与参加记录：与目标账号冲突时以目标账号为准，之后统一重算
    for record in ScoreRecord.objects.filter(student=source):
        if record.assignment_id:
            assignment_ids.add(record.assignment_id)
        if record.exam_id:
            exam_ids.add(record.exam_id)
    ScoreRecord.objects.filter(student=source).delete()

    for participant in ExamParticipant.objects.filter(student=source):
        if ExamParticipant.objects.filter(exam_id=participant.exam_id, student=target).exists():
            participant.delete()
        else:
            participant.student = target
            participant.save(update_fields=["student"])
        exam_ids.add(participant.exam_id)

    for membership in ClassMember.objects.filter(student=source):
        if ClassMember.objects.filter(class_group_id=membership.class_group_id, student=target).exists():
            membership.delete()
        else:
            membership.student = target
            membership.save(update_fields=["student"])

    for submission in Submission.objects.filter(user=source):
        if submission.assignment_id:
            assignment_ids.add(submission.assignment_id)
        if submission.exam_id:
            exam_ids.add(submission.exam_id)
    Submission.objects.filter(user=source).update(user=target)

    # 学生档案：先从学号账号上解除，再挂到目标账号上
    StudentProfile.objects.filter(user=source).update(user=target)

    User.objects.filter(pk=source.pk).delete()

    _recalculate(target, assignment_ids, exam_ids)


def _recalculate(user, assignment_ids, exam_ids):
    # 延迟导入，避免 account 与 classroom、contest 之间的循环依赖
    from classroom.models import Assignment
    from classroom.scoring import recalculate_score
    from contest.models import Exam
    from contest.scoring import recalculate_exam_score

    for assignment in Assignment.objects.filter(pk__in=assignment_ids):
        recalculate_score(assignment, user.id)
    for exam in Exam.objects.filter(pk__in=exam_ids):
        recalculate_exam_score(exam, user.id)
