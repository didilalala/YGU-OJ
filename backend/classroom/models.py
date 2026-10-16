import secrets

from django.conf import settings
from django.db import models

# 去掉易混淆的 0/O、1/I/L
_INVITE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generate_invite_code():
    return "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(8))


class ClassGroup(models.Model):
    """班级（M9），由教师创建，学生经 Excel 导入加入。"""

    name = models.CharField("班级名称", max_length=64)
    course = models.CharField("课程", max_length=64, blank=True)
    semester = models.CharField("学期", max_length=32, blank=True)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="teaching_classes", verbose_name="教师"
    )
    # 预留给学生凭邀请码加入班级
    invite_code = models.CharField("邀请码", max_length=8, unique=True, default=generate_invite_code)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "class_group"
        ordering = ["-id"]
        verbose_name = verbose_name_plural = "班级"

    def __str__(self):
        return self.name

    def can_manage(self, user):
        """管理员可管理全部班级，教师只能管理自己的班级。"""
        if not (user and user.is_authenticated):
            return False
        return user.role == user.Role.ADMIN or self.teacher_id == user.id


class ClassMemberQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_removed=False)


class ClassMember(models.Model):
    """
    班级成员。移出班级只做标记（is_removed），历史成绩保留，
    但不再出现在该班后续统计中（设计说明书 4.3）。
    """

    class_group = models.ForeignKey(
        ClassGroup, on_delete=models.CASCADE, related_name="members", db_column="class_id", verbose_name="班级"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="class_memberships", verbose_name="学生"
    )
    joined_at = models.DateTimeField("加入时间", auto_now_add=True)
    is_removed = models.BooleanField("已移出", default=False)
    removed_at = models.DateTimeField("移出时间", null=True, blank=True)

    objects = ClassMemberQuerySet.as_manager()

    class Meta:
        db_table = "class_member"
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["class_group", "student"], name="uniq_class_member")]
        verbose_name = verbose_name_plural = "班级成员"


class Assignment(models.Model):
    """
    作业（M10）。发布后班级学生可见；开始后可提交，截止后若允许迟交仍可提交，
    迟交得分按 late_penalty 扣减（0.2 表示扣 20%）。每题取学生的最高得分。
    """

    class_group = models.ForeignKey(
        ClassGroup, on_delete=models.PROTECT, related_name="assignments", db_column="class_id", verbose_name="班级"
    )
    title = models.CharField("标题", max_length=128)
    description = models.TextField("说明", blank=True)
    start_time = models.DateTimeField("开始时间")
    end_time = models.DateTimeField("截止时间")
    allow_late = models.BooleanField("允许迟交", default=False)
    late_penalty = models.FloatField("迟交扣分比例", default=0)
    is_published = models.BooleanField("已发布", default=False)
    problems = models.ManyToManyField(
        "problem.Problem", through="AssignmentProblem", related_name="assignments", verbose_name="题目"
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "assignment"
        ordering = ["-end_time", "-id"]
        verbose_name = verbose_name_plural = "作业"

    def __str__(self):
        return self.title

    def status_at(self, now):
        """not_started 未开始、in_progress 进行中、late 截止后允许迟交、ended 已截止。"""
        if now < self.start_time:
            return "not_started"
        if now <= self.end_time:
            return "in_progress"
        return "late" if self.allow_late else "ended"

    def is_late(self, moment):
        return moment > self.end_time


class AssignmentProblem(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="items")
    problem = models.ForeignKey("problem.Problem", on_delete=models.PROTECT, related_name="+")
    score = models.PositiveIntegerField("分值", default=100)
    order = models.PositiveIntegerField("顺序", default=0)

    class Meta:
        db_table = "assignment_problem"
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["assignment", "problem"], name="uniq_assignment_problem")]


class ScoreRecord(models.Model):
    """
    成绩记录：学生 × 作业，或学生 × 考试，由该学生在其中的全部提交计算，
    见 classroom.scoring 与 contest.scoring。details 为各题明细，
    作业为 {题目编号: {"score", "accepted", "late"}}，考试见 contest.scoring。
    """

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="score_records")
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, null=True, related_name="score_records")
    exam = models.ForeignKey("contest.Exam", on_delete=models.CASCADE, null=True, related_name="score_records")
    score = models.FloatField("得分", default=0)
    solved_count = models.PositiveIntegerField("通过题数", default=0)
    # ACM 赛制的罚时（秒）：各题通过用时 + 每次错误提交 20 分钟
    penalty = models.PositiveIntegerField("罚时（秒）", default=0)
    is_late = models.BooleanField("含迟交得分", default=False)
    details = models.JSONField("各题明细", default=dict)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "score_record"
        constraints = [
            models.UniqueConstraint(fields=["student", "assignment"], name="uniq_score_record_assignment"),
            models.UniqueConstraint(fields=["student", "exam"], name="uniq_score_record_exam"),
        ]
