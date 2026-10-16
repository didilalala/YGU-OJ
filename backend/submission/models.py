from django.conf import settings
from django.db import models


class Submission(models.Model):
    """提交记录（M4）。评测由 judge.tasks.judge_submission 异步完成。"""

    class Result(models.TextChoices):
        PENDING = "PENDING", "等待评测"
        JUDGING = "JUDGING", "评测中"
        AC = "AC", "通过"
        WA = "WA", "答案错误"
        TLE = "TLE", "超出时间限制"
        MLE = "MLE", "超出内存限制"
        RE = "RE", "运行错误"
        CE = "CE", "编译错误"
        PAC = "PAC", "部分正确"
        SE = "SE", "系统错误"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submissions", verbose_name="用户"
    )
    problem = models.ForeignKey(
        "problem.Problem", on_delete=models.PROTECT, related_name="submissions", verbose_name="题目"
    )
    # 语言标识，取值见 judge.Language（可在后台增删）
    language = models.CharField("语言", max_length=32)
    code = models.TextField("代码")
    result = models.CharField("评测结果", max_length=8, choices=Result.choices, default=Result.PENDING)
    # 各测试点的最大值
    time_cost = models.PositiveIntegerField("耗时（毫秒）", null=True, blank=True)
    memory_cost = models.PositiveIntegerField("内存（KB）", null=True, blank=True)
    # [{"case": 1, "result": "AC", "time": 12, "memory": 1024, "exit_code": 0, "signal": 0}, ...]
    case_info = models.JSONField("测试点详情", default=list, blank=True)
    # 编译错误信息（展示给学生），或系统错误原因（仅管理员可见）
    error_info = models.TextField("错误信息", blank=True)
    # 作业中的提交计入成绩；有提交的作业不能删除
    assignment = models.ForeignKey(
        "classroom.Assignment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="submissions",
        verbose_name="作业",
    )
    # 考试中的提交计入考试成绩与排名；有提交的考试不能删除
    exam = models.ForeignKey(
        "contest.Exam",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="submissions",
        verbose_name="考试",
    )
    ip = models.GenericIPAddressField("提交 IP", null=True, blank=True)
    created_at = models.DateTimeField("提交时间", auto_now_add=True)
    judged_at = models.DateTimeField("评测完成时间", null=True, blank=True)

    class Meta:
        db_table = "submission"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["problem", "result"]),
            models.Index(fields=["user", "problem"]),
        ]
        verbose_name = verbose_name_plural = "提交记录"

    def __str__(self):
        return f"#{self.id} {self.user_id} → {self.problem_id} {self.result}"

    @property
    def is_finished(self):
        return self.result not in (self.Result.PENDING, self.Result.JUDGING)

    @property
    def uses_partial_score(self):
        """
        部分正确（PAC）按通过测试点的比例得分，只用于按得分计成绩的场景：
        作业与 OI 赛制考试按比例给分；ACM 赛制考试和日常练习只区分通过与否。
        """
        if self.assignment_id is not None:
            return True
        return self.exam_id is not None and self.exam.rule_type == "OI"

    @property
    def passed_ratio(self):
        if not self.case_info:
            return 0.0
        passed = sum(1 for case in self.case_info if case["result"] == self.Result.AC)
        return passed / len(self.case_info)
