import ipaddress

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import serializers

from classroom.serializers import MAX_ASSIGNMENT_PROBLEMS, AssignmentItemWriteSerializer
from problem.models import Problem

from .models import Exam, ExamProblem
from stats.cache import bump_class

from .scoring import recalculate_exam

MAX_IP_RANGES = 50


class ExamItemSerializer(serializers.ModelSerializer):
    problem_id = serializers.IntegerField(source="problem.id")
    title = serializers.CharField(source="problem.title")
    difficulty = serializers.CharField(source="problem.difficulty")

    class Meta:
        model = ExamProblem
        fields = ["problem_id", "title", "difficulty", "score"]


class AdminExamSerializer(serializers.ModelSerializer):
    """
    管理端考试。problems 为写入用的 [{"problem_id", "score"}]（按顺序），items 为读取用的题目明细。
    班级创建后不可更改。
    """

    class_name = serializers.CharField(source="class_group.name", read_only=True, default=None)
    problems = AssignmentItemWriteSerializer(many=True, write_only=True)
    items = ExamItemSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()
    total_score = serializers.SerializerMethodField()
    # 由查询集 annotate，见 contest.views
    participant_count = serializers.IntegerField(read_only=True, default=0)
    member_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Exam
        fields = [
            "id",
            "class_group",
            "class_name",
            "title",
            "description",
            "rule_type",
            "start_time",
            "end_time",
            "allowed_ip_ranges",
            "password",
            "is_published",
            "show_rank",
            "lock_problem_bank",
            "is_score_published",
            "problems",
            "items",
            "status",
            "total_score",
            "participant_count",
            "member_count",
            "created_at",
            "updated_at",
        ]
        # 班级为空表示公开竞赛
        extra_kwargs = {"class_group": {"required": False, "allow_null": True}}

    def get_status(self, exam):
        return exam.status_at(timezone.now())

    def get_total_score(self, exam):
        return sum(item.score for item in exam.items.all())

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None and not isinstance(self.instance, (list, QuerySet)):
            fields["class_group"].read_only = True
        return fields

    def validate_class_group(self, class_group):
        if class_group is not None and not class_group.can_manage(self.context["request"].user):
            raise serializers.ValidationError("班级不存在")
        return class_group

    def validate_allowed_ip_ranges(self, ranges):
        if not isinstance(ranges, list) or len(ranges) > MAX_IP_RANGES:
            raise serializers.ValidationError(f"IP 段应为列表，且不超过 {MAX_IP_RANGES} 条")
        normalized = []
        for value in ranges:
            text = str(value).strip()
            if not text:
                continue
            try:
                normalized.append(str(ipaddress.ip_network(text, strict=False)))
            except ValueError:
                raise serializers.ValidationError(f"无效的 IP 或 IP 段：{text}")
        return normalized

    def validate_problems(self, items):
        if not items:
            raise serializers.ValidationError("请至少选择一道题目")
        if len(items) > MAX_ASSIGNMENT_PROBLEMS:
            raise serializers.ValidationError(f"一场考试最多 {MAX_ASSIGNMENT_PROBLEMS} 道题目")
        ids = [item["problem_id"] for item in items]
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("题目重复")
        visible = set(
            Problem.objects.visible_to(self.context["request"].user).filter(pk__in=ids).values_list("id", flat=True)
        )
        missing = [pid for pid in ids if pid not in visible]
        if missing:
            raise serializers.ValidationError(f"题目不存在或无权使用：{', '.join(map(str, missing))}")
        return items

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start:
            raise serializers.ValidationError("结束时间应晚于开始时间")
        # 公开竞赛的参加者不限于某个班级，不锁定题库
        is_public = attrs.get("class_group", getattr(self.instance, "class_group", None)) is None
        if is_public:
            attrs["lock_problem_bank"] = False
        return attrs

    def _save_items(self, exam, items):
        exam.items.all().delete()
        ExamProblem.objects.bulk_create(
            ExamProblem(exam=exam, problem_id=item["problem_id"], score=item["score"], order=index)
            for index, item in enumerate(items)
        )

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("problems")
        exam = Exam.objects.create(created_by=self.context["request"].user, **validated_data)
        self._save_items(exam, items)
        bump_class(exam.class_group_id)
        return exam

    @transaction.atomic
    def update(self, exam, validated_data):
        items = validated_data.pop("problems", None)
        for key, value in validated_data.items():
            setattr(exam, key, value)
        exam.save()
        if items is not None:
            self._save_items(exam, items)
        bump_class(exam.class_group_id)
        # 赛制、题目或分值可能改变，重算已有成绩
        transaction.on_commit(lambda: recalculate_exam(exam))
        return exam


class StudentExamSerializer(serializers.ModelSerializer):
    """学生端考试列表；详情另加题目、说明与本人进度，见 contest.views。"""

    class_name = serializers.CharField(source="class_group.name", read_only=True, default=None)
    is_public = serializers.BooleanField(read_only=True)
    # 由查询集 annotate（公开竞赛列表）
    participant_count = serializers.IntegerField(read_only=True, default=None)
    status = serializers.SerializerMethodField()
    problem_count = serializers.SerializerMethodField()
    total_score = serializers.SerializerMethodField()
    need_password = serializers.SerializerMethodField()
    joined = serializers.SerializerMethodField()
    finished = serializers.SerializerMethodField()
    my_score = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            "id",
            "title",
            "class_name",
            "is_public",
            "participant_count",
            "rule_type",
            "start_time",
            "end_time",
            "status",
            "problem_count",
            "total_score",
            "need_password",
            "show_rank",
            "is_score_published",
            "joined",
            "finished",
            "my_score",
        ]

    def _participant(self, exam):
        return self.context.get("participants", {}).get(exam.id)

    def get_status(self, exam):
        return exam.status_at(timezone.now())

    def get_problem_count(self, exam):
        return len(exam.items.all())

    def get_total_score(self, exam):
        return sum(item.score for item in exam.items.all())

    def get_need_password(self, exam):
        return bool(exam.password)

    def get_joined(self, exam):
        return self._participant(exam) is not None

    def get_finished(self, exam):
        participant = self._participant(exam)
        return bool(participant and participant.finished_at)

    def get_my_score(self, exam):
        """成绩公布后才显示总分。"""
        if not exam.is_score_published:
            return None
        record = self.context.get("records", {}).get(exam.id)
        return record.score if record else 0
