from django.conf import settings
from django.db import models
from django.db.models import Q


class KnowledgePoint(models.Model):
    """课程知识点（M12），如「循环」「数组」「指针」，可按 parent 组成树。"""

    name = models.CharField("名称", max_length=64)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children", verbose_name="上级知识点"
    )
    course = models.CharField("课程", max_length=64, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "knowledge_point"
        ordering = ["course", "id"]
        constraints = [models.UniqueConstraint(fields=["course", "name"], name="uniq_knowledge_point_course_name")]
        verbose_name = verbose_name_plural = "知识点"

    def __str__(self):
        return self.name

    @classmethod
    def with_descendants(cls, point_id):
        """该知识点及其全部下级的编号；知识点数量很少，一次取出在内存中遍历。"""
        children = {}
        for pk, parent_id in cls.objects.values_list("id", "parent_id"):
            children.setdefault(parent_id, []).append(pk)
        result, stack = set(), [point_id]
        while stack:
            pk = stack.pop()
            if pk not in result:
                result.add(pk)
                stack.extend(children.get(pk, []))
        return result


class ProblemQuerySet(models.QuerySet):
    def visible_to(self, user):
        """公开题目所有人可见；私有题目仅创建者与管理员可见。"""
        if user and user.is_authenticated:
            if user.role == user.Role.ADMIN:
                return self
            if user.role == user.Role.TEACHER:
                return self.filter(Q(is_public=True) | Q(created_by=user))
        # TODO(M7/M10)：私有题目对布置了该题的作业、考试中的学生可见
        return self.filter(is_public=True)


class Problem(models.Model):
    """
    题目（M3）。测试数据以文件形式存放在 TEST_CASE_DIR/<test_case_id>/，见 problem/test_cases.py。
    """

    class Difficulty(models.TextChoices):
        EASY = "easy", "简单"
        MEDIUM = "medium", "中等"
        HARD = "hard", "困难"

    title = models.CharField("标题", max_length=128)
    # 题面各部分为 Markdown（FPS 导入的题目为 HTML），前端渲染前过滤脚本
    description = models.TextField("题目描述")
    input_desc = models.TextField("输入说明", blank=True)
    output_desc = models.TextField("输出说明", blank=True)
    # [{"input": "...", "output": "..."}]
    samples = models.JSONField("样例", default=list, blank=True)
    hint = models.TextField("提示", blank=True)
    source = models.CharField("来源", max_length=128, blank=True)
    time_limit = models.PositiveIntegerField("时间限制（毫秒）", default=1000)
    memory_limit = models.PositiveIntegerField("内存限制（MB）", default=256)
    difficulty = models.CharField("难度", max_length=16, choices=Difficulty.choices, default=Difficulty.EASY)
    knowledge_points = models.ManyToManyField(
        KnowledgePoint, through="ProblemKnowledge", related_name="problems", blank=True, verbose_name="知识点"
    )
    is_public = models.BooleanField("是否公开", default=False)
    # 模板题（M8）：学生只写函数体，评测时拼接为 prepend + 学生代码 + append。
    # template_code 形如 {"cpp": {"prepend": "...", "template": "...", "append": "..."}}，
    # template 是展示给学生的初始代码，prepend 与 append 不对学生展示。
    is_template = models.BooleanField("是否模板题", default=False)
    template_code = models.JSONField("模板代码", default=dict, blank=True)
    test_case_id = models.CharField("测试数据编号", max_length=32, blank=True)
    # 由判题结果统计，见 judge.judger.update_problem_statistics
    submission_count = models.PositiveIntegerField("提交数", default=0)
    accepted_count = models.PositiveIntegerField("通过数", default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="创建者"
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    objects = ProblemQuerySet.as_manager()

    class Meta:
        db_table = "problem"
        ordering = ["id"]
        verbose_name = verbose_name_plural = "题目"

    def __str__(self):
        return f"{self.id}. {self.title}"

    def is_visible_to(self, user):
        return Problem.objects.visible_to(user).filter(pk=self.pk).exists()

    def can_edit(self, user):
        """管理员可编辑全部题目，教师只能编辑自己创建的题目。"""
        if not (user and user.is_authenticated):
            return False
        if user.role == user.Role.ADMIN:
            return True
        return user.role == user.Role.TEACHER and self.created_by_id == user.id

    @property
    def languages(self):
        """可提交的语言：模板题限于配置了模板的语言。"""
        from judge.models import Language

        keys = list(Language.objects.filter(enabled=True).values_list("key", flat=True))
        if self.is_template:
            keys = [key for key in keys if key in (self.template_code or {})]
        return keys


class ProblemKnowledge(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    knowledge_point = models.ForeignKey(KnowledgePoint, on_delete=models.CASCADE)

    class Meta:
        db_table = "problem_knowledge"
        constraints = [
            models.UniqueConstraint(fields=["problem", "knowledge_point"], name="uniq_problem_knowledge")
        ]
