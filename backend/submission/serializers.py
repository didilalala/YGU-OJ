from rest_framework import serializers
from rest_framework.exceptions import NotFound

from classroom.access import assignment_problem
from contest.access import ensure_not_locked, exam_problem
from judge.models import Language
from options import site
from problem.models import Problem

from .models import Submission


class SubmitSerializer(serializers.Serializer):
    problem_id = serializers.IntegerField()
    language = serializers.CharField(max_length=32)
    # 代码长度上限由网站参数 max_code_kb 决定，见 validate_code
    code = serializers.CharField(trim_whitespace=False)
    # 在作业中提交时传入，提交计入作业成绩
    assignment_id = serializers.IntegerField(required=False, allow_null=True)
    # 在考试中提交时传入，校验考试时间、IP 段与是否已交卷
    exam_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_language(self, value):
        if not Language.objects.filter(key=value, enabled=True).exists():
            raise serializers.ValidationError("该语言暂不支持提交")
        return value

    def validate_code(self, value):
        if not value.strip():
            raise serializers.ValidationError("代码不能为空")
        limit = site.get("max_code_kb") * 1024
        if len(value.encode("utf-8")) > limit:
            raise serializers.ValidationError(f"代码不能超过 {site.get('max_code_kb')} KB")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        problem = Problem.objects.filter(pk=attrs["problem_id"]).first()
        if problem is None:
            raise NotFound("题目不存在")
        if attrs.get("exam_id") and attrs.get("assignment_id"):
            raise serializers.ValidationError("不能同时指定作业与考试")

        if attrs.get("exam_id"):
            # 考试题目对参加考试的学生可见（含私有题目），并检查考试时间、IP 段与是否交卷
            attrs["exam"] = exam_problem(request, attrs["exam_id"], problem.id, for_submit=True)
        else:
            # 考试期间只能提交本场考试的题目
            ensure_not_locked(user)
            if attrs.get("assignment_id"):
                # 作业中的题目对班级学生可见（含私有题目），并检查作业时间
                attrs["assignment"] = assignment_problem(user, attrs["assignment_id"], problem.id, for_submit=True)
            elif not problem.is_visible_to(user):
                # 无权查看的题目与不存在的题目返回相同结果，不暴露私有题目
                raise NotFound("题目不存在")
        if not problem.test_case_id:
            raise serializers.ValidationError("该题目暂无测试数据，无法提交")
        if problem.is_template and attrs["language"] not in (problem.template_code or {}):
            raise serializers.ValidationError("该模板题不支持所选语言")
        attrs["problem"] = problem
        return attrs


class SubmissionListSerializer(serializers.ModelSerializer):
    problem_title = serializers.CharField(source="problem.title", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "problem",
            "problem_title",
            "user",
            "username",
            "language",
            "result",
            "time_cost",
            "memory_cost",
            "is_finished",
            "created_at",
        ]


class SubmissionDetailSerializer(SubmissionListSerializer):
    class Meta(SubmissionListSerializer.Meta):
        fields = SubmissionListSerializer.Meta.fields + ["code", "case_info", "error_info", "judged_at"]

    def to_representation(self, submission):
        data = super().to_representation(submission)
        viewer = self.context["request"].user
        # 系统错误的原因（服务器地址、异常信息）只给教师与管理员看；编译错误信息照常展示
        if submission.result == Submission.Result.SE and not viewer.is_teacher_or_admin:
            data["error_info"] = ""
        return data
