"""学生访问作业及作业中题目的权限检查，提交接口与题目详情接口共用。"""

from django.utils import timezone
from rest_framework.exceptions import NotFound

from utils.exceptions import BusinessError

from .models import Assignment


def student_assignment(user, assignment_id):
    """已发布、且学生仍在该班级中的作业；否则一律视为不存在。"""
    if not (user and user.is_authenticated):
        raise NotFound("作业不存在")
    assignment = (
        Assignment.objects.filter(
            pk=assignment_id,
            is_published=True,
            class_group__members__student=user,
            class_group__members__is_removed=False,
        )
        .select_related("class_group")
        .first()
    )
    if assignment is None:
        raise NotFound("作业不存在")
    return assignment


def assignment_problem(user, assignment_id, problem_id, for_submit=False):
    """
    学生在作业中访问题目：作业须已开始且包含该题；私有题目也可见。
    提交时还要求未截止，或截止后允许迟交。返回作业。
    """
    assignment = student_assignment(user, assignment_id)
    if not assignment.items.filter(problem_id=problem_id).exists():
        raise NotFound("该题目不在此作业中")
    status = assignment.status_at(timezone.now())
    if status == "not_started":
        raise BusinessError("作业尚未开始")
    if for_submit and status == "ended":
        raise BusinessError("作业已截止，不能再提交")
    return assignment
