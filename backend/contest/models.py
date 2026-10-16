import ipaddress

from django.conf import settings
from django.db import models


class Exam(models.Model):
    """
    考试与竞赛（M7）。
    - 课堂考试：限定班级、IP 段限制、考试期间锁定题库、自动计分；
    - 公开竞赛：class_group 为空，所有登录用户都能参加（可设口令），访客可浏览与看排名，不锁定题库。
    """

    class Rule(models.TextChoices):
        ACM = "ACM", "ACM 赛制"
        OI = "OI", "OI 赛制"

    class_group = models.ForeignKey(
        "classroom.ClassGroup",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="exams",
        db_column="class_id",
        verbose_name="班级",
    )
    title = models.CharField("标题", max_length=128)
    description = models.TextField("说明", blank=True)
    rule_type = models.CharField("赛制", max_length=8, choices=Rule.choices, default=Rule.OI)
    start_time = models.DateTimeField("开始时间")
    end_time = models.DateTimeField("结束时间")
    # 允许的 IP 段，如 ["10.1.0.0/16", "202.1.2.3"]；为空表示不限制
    allowed_ip_ranges = models.JSONField("允许的 IP 段", default=list, blank=True)
    # 进入考试时需输入的口令（如监考老师在机房公布）；为空表示不需要
    password = models.CharField("考试口令", max_length=32, blank=True)
    is_published = models.BooleanField("已发布", default=False)
    show_rank = models.BooleanField("考试中学生可看排名", default=False)
    lock_problem_bank = models.BooleanField("考试期间锁定题库", default=True)
    is_score_published = models.BooleanField("已公布成绩", default=False)
    problems = models.ManyToManyField(
        "problem.Problem", through="ExamProblem", related_name="exams", verbose_name="题目"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="创建者"
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "exam"
        ordering = ["-start_time", "-id"]
        verbose_name = verbose_name_plural = "考试"

    def __str__(self):
        return self.title

    @property
    def is_public(self):
        return self.class_group_id is None

    def status_at(self, now):
        """not_started 未开始、in_progress 进行中、ended 已结束。"""
        if now < self.start_time:
            return "not_started"
        if now <= self.end_time:
            return "in_progress"
        return "ended"

    def ip_allowed(self, ip):
        if not self.allowed_ip_ranges:
            return True
        try:
            address = ipaddress.ip_address(ip or "")
        except ValueError:
            return False
        return any(address in ipaddress.ip_network(cidr, strict=False) for cidr in self.allowed_ip_ranges)


class ExamProblem(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="items")
    problem = models.ForeignKey("problem.Problem", on_delete=models.PROTECT, related_name="+")
    score = models.PositiveIntegerField("分值", default=100)
    order = models.PositiveIntegerField("顺序", default=0)

    class Meta:
        db_table = "exam_problem"
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["exam", "problem"], name="uniq_exam_problem")]


class ExamParticipant(models.Model):
    """进入考试的记录：进入时间与 IP（便于监考核对）、交卷时间。"""

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="participants")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exam_participations")
    joined_at = models.DateTimeField("进入时间", auto_now_add=True)
    join_ip = models.GenericIPAddressField("进入 IP", null=True, blank=True)
    finished_at = models.DateTimeField("交卷时间", null=True, blank=True)

    class Meta:
        db_table = "exam_participant"
        constraints = [models.UniqueConstraint(fields=["exam", "student"], name="uniq_exam_participant")]
