from rest_framework import serializers

from judge.models import Language

from . import test_cases
from .models import KnowledgePoint, Problem

MAX_SAMPLES = 10
TIME_LIMIT_RANGE = (100, 10000)  # 毫秒
MEMORY_LIMIT_RANGE = (16, 1024)  # MB
TEMPLATE_PARTS = ("prepend", "template", "append")


class KnowledgePointSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgePoint
        fields = ["id", "name", "parent", "course"]
        # 自动生成的唯一性校验提示为「字段 course, name 必须能构成唯一集合」，改为在 validate 中给出可读提示
        validators = []

    def validate(self, attrs):
        name = attrs.get("name", self.instance.name if self.instance else "")
        course = attrs.get("course", self.instance.course if self.instance else "")
        duplicates = KnowledgePoint.objects.filter(name=name, course=course)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(f"课程「{course or '未分类'}」下已有同名知识点「{name}」")
        return attrs

    def validate_parent(self, parent):
        # 不能把知识点挂到自己或自己的下级下面，否则形成环
        if parent and self.instance and parent.id in KnowledgePoint.with_descendants(self.instance.id):
            raise serializers.ValidationError("不能选择自身或下级知识点作为上级")
        return parent


class KnowledgePointBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgePoint
        fields = ["id", "name"]


# ---------------------------------------------------------------- 前台


class ProblemListSerializer(serializers.ModelSerializer):
    knowledge_points = KnowledgePointBriefSerializer(many=True, read_only=True)
    # 当前用户的做题状态：AC（已通过）、TRIED（尝试过）、null（未提交或未登录）
    my_status = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = [
            "id",
            "title",
            "difficulty",
            "knowledge_points",
            "is_template",
            "submission_count",
            "accepted_count",
            "my_status",
        ]

    def get_my_status(self, problem):
        return self.context.get("my_status", {}).get(problem.id)


class ProblemDetailSerializer(ProblemListSerializer):
    template = serializers.SerializerMethodField()
    languages = serializers.ListField(read_only=True)

    class Meta(ProblemListSerializer.Meta):
        fields = ProblemListSerializer.Meta.fields + [
            "description",
            "input_desc",
            "output_desc",
            "samples",
            "hint",
            "source",
            "time_limit",
            "memory_limit",
            "languages",
            "template",
        ]

    def get_template(self, problem):
        """只给学生看初始代码，不给出评测时拼接的前后代码。"""
        if not problem.is_template:
            return {}
        return {lang: parts.get("template", "") for lang, parts in problem.template_code.items()}


# ---------------------------------------------------------------- 管理


class AdminProblemListSerializer(serializers.ModelSerializer):
    knowledge_points = KnowledgePointBriefSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    can_edit = serializers.SerializerMethodField()
    has_test_cases = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = [
            "id",
            "title",
            "difficulty",
            "knowledge_points",
            "is_public",
            "is_template",
            "has_test_cases",
            "submission_count",
            "accepted_count",
            "created_by",
            "created_by_name",
            "can_edit",
            "created_at",
            "updated_at",
        ]

    def get_can_edit(self, problem):
        return problem.can_edit(self.context["request"].user)

    def get_has_test_cases(self, problem):
        return bool(problem.test_case_id)


class AdminProblemSerializer(AdminProblemListSerializer):
    """管理端创建、编辑与查看题目。"""

    knowledge_point_ids = serializers.PrimaryKeyRelatedField(
        many=True, source="knowledge_points", queryset=KnowledgePoint.objects.all(), write_only=True, required=False
    )
    test_cases = serializers.SerializerMethodField()

    class Meta(AdminProblemListSerializer.Meta):
        fields = AdminProblemListSerializer.Meta.fields + [
            "knowledge_point_ids",
            "description",
            "input_desc",
            "output_desc",
            "samples",
            "hint",
            "source",
            "time_limit",
            "memory_limit",
            "template_code",
            "test_case_id",
            "test_cases",
        ]
        read_only_fields = ["submission_count", "accepted_count", "created_by", "created_at", "updated_at"]

    def get_test_cases(self, problem):
        """测试点概况，便于教师核对上传结果。"""
        if not problem.test_case_id:
            return []
        try:
            info = test_cases.load_info(problem.test_case_id)
        except (ValueError, OSError):
            return []
        return [
            {"index": int(index), "input_size": item["input_size"], "output_size": item["output_size"]}
            for index, item in sorted(info["test_cases"].items(), key=lambda pair: int(pair[0]))
        ]

    def validate_time_limit(self, value):
        low, high = TIME_LIMIT_RANGE
        if not low <= value <= high:
            raise serializers.ValidationError(f"时间限制应在 {low}–{high} 毫秒之间")
        return value

    def validate_memory_limit(self, value):
        low, high = MEMORY_LIMIT_RANGE
        if not low <= value <= high:
            raise serializers.ValidationError(f"内存限制应在 {low}–{high} MB 之间")
        return value

    def validate_samples(self, samples):
        if not isinstance(samples, list) or len(samples) > MAX_SAMPLES:
            raise serializers.ValidationError(f"样例应为列表，且不超过 {MAX_SAMPLES} 组")
        for sample in samples:
            if not (
                isinstance(sample, dict)
                and set(sample) == {"input", "output"}
                and all(isinstance(sample[key], str) for key in sample)
            ):
                raise serializers.ValidationError('每组样例应为 {"input": "...", "output": "..."}')
        return samples

    def validate_template_code(self, template_code):
        if not isinstance(template_code, dict):
            raise serializers.ValidationError("模板代码格式错误")
        for language, parts in template_code.items():
            if not Language.objects.filter(key=language).exists():
                raise serializers.ValidationError(f"不支持的语言：{language}")
            if not (
                isinstance(parts, dict)
                and set(parts) <= set(TEMPLATE_PARTS)
                and all(isinstance(value, str) for value in parts.values())
            ):
                raise serializers.ValidationError(f"{language} 的模板应包含 prepend、template、append 文本")
        return template_code

    def validate_test_case_id(self, value):
        if not value:
            return ""
        try:
            test_cases.load_info(value)
        except (ValueError, OSError):
            raise serializers.ValidationError("测试数据不存在，请重新上传")
        # 每题独占一份测试数据：修改或删除题目时会清理旧数据
        others = Problem.objects.filter(test_case_id=value)
        if self.instance:
            others = others.exclude(pk=self.instance.pk)
        if others.exists():
            raise serializers.ValidationError("该测试数据已被其他题目使用，请重新上传")
        return value

    def validate(self, attrs):
        is_template = attrs.get("is_template", self.instance.is_template if self.instance else False)
        template_code = attrs.get("template_code", self.instance.template_code if self.instance else {})
        if is_template and not template_code:
            raise serializers.ValidationError("模板题至少需要配置一种语言的模板")
        return attrs
