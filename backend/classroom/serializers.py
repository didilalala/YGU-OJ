from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import serializers

from account.students import is_valid_student_no
from problem.models import Problem

from .models import Assignment, AssignmentProblem, ClassGroup, ClassMember
from stats.cache import bump_class

from .scoring import recalculate_assignment


class ClassGroupSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.display_name", read_only=True)
    # 由查询集 annotate，见 classroom.views
    member_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ClassGroup
        fields = ["id", "name", "course", "semester", "teacher", "teacher_name", "member_count", "invite_code", "created_at"]
        read_only_fields = ["teacher", "invite_code", "created_at"]


class MyClassSerializer(serializers.ModelSerializer):
    """学生端：我所在的班级。"""

    teacher_name = serializers.CharField(source="teacher.display_name", read_only=True)

    class Meta:
        model = ClassGroup
        fields = ["id", "name", "course", "semester", "teacher_name"]


class ClassMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="student.id", read_only=True)
    username = serializers.CharField(source="student.username", read_only=True)
    student_no = serializers.CharField(source="student.student_profile.student_no", read_only=True, default="")
    real_name = serializers.CharField(source="student.student_profile.real_name", read_only=True, default="")
    college = serializers.CharField(source="student.student_profile.college", read_only=True, default="")
    major = serializers.CharField(source="student.student_profile.major", read_only=True, default="")
    grade = serializers.CharField(source="student.student_profile.grade", read_only=True, default="")
    # 仍为初始密码，即还没有登录并修改过密码
    is_initial_password = serializers.BooleanField(source="student.is_initial_password", read_only=True)
    last_login = serializers.DateTimeField(source="student.last_login", read_only=True)

    class Meta:
        model = ClassMember
        fields = [
            "id",
            "user_id",
            "username",
            "student_no",
            "real_name",
            "college",
            "major",
            "grade",
            "is_initial_password",
            "last_login",
            "joined_at",
            "is_removed",
            "removed_at",
        ]


class AddStudentSerializer(serializers.Serializer):
    """手动添加单个学生，规则与名单导入相同。"""

    student_no = serializers.CharField(max_length=32)
    real_name = serializers.CharField(max_length=32)
    college = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    major = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    grade = serializers.CharField(max_length=16, required=False, allow_blank=True, default="")

    def validate_student_no(self, value):
        if not is_valid_student_no(value):
            raise serializers.ValidationError("学号格式不正确")
        return value


class UserIdsSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False, max_length=1000)


# ---------------------------------------------------------------- 作业

MAX_ASSIGNMENT_PROBLEMS = 50
SCORE_RANGE = (1, 1000)


class AssignmentItemWriteSerializer(serializers.Serializer):
    problem_id = serializers.IntegerField()
    score = serializers.IntegerField(min_value=SCORE_RANGE[0], max_value=SCORE_RANGE[1])


class AssignmentItemSerializer(serializers.ModelSerializer):
    problem_id = serializers.IntegerField(source="problem.id")
    title = serializers.CharField(source="problem.title")
    difficulty = serializers.CharField(source="problem.difficulty")

    class Meta:
        model = AssignmentProblem
        fields = ["problem_id", "title", "difficulty", "score"]


class AdminAssignmentSerializer(serializers.ModelSerializer):
    """
    管理端作业。problems 为写入用的 [{"problem_id", "score"}]（按顺序），items 为读取用的题目明细。
    班级创建后不可更改。
    """

    class_name = serializers.CharField(source="class_group.name", read_only=True)
    problems = AssignmentItemWriteSerializer(many=True, write_only=True)
    items = AssignmentItemSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()
    total_score = serializers.SerializerMethodField()
    # 由查询集 annotate，见 classroom.views
    submitted_count = serializers.IntegerField(read_only=True, default=0)
    member_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Assignment
        fields = [
            "id",
            "class_group",
            "class_name",
            "title",
            "description",
            "start_time",
            "end_time",
            "allow_late",
            "late_penalty",
            "is_published",
            "problems",
            "items",
            "status",
            "total_score",
            "submitted_count",
            "member_count",
            "created_at",
            "updated_at",
        ]

    def get_status(self, assignment):
        return assignment.status_at(timezone.now())

    def get_total_score(self, assignment):
        return sum(item.score for item in assignment.items.all())

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None and not isinstance(self.instance, (list, QuerySet)):
            fields["class_group"].read_only = True
        return fields

    def validate_class_group(self, class_group):
        if not class_group.can_manage(self.context["request"].user):
            raise serializers.ValidationError("班级不存在")
        return class_group

    def validate_late_penalty(self, value):
        if not 0 <= value <= 1:
            raise serializers.ValidationError("迟交扣分比例应在 0–100% 之间")
        return value

    def validate_problems(self, items):
        if not items:
            raise serializers.ValidationError("请至少选择一道题目")
        if len(items) > MAX_ASSIGNMENT_PROBLEMS:
            raise serializers.ValidationError(f"一份作业最多 {MAX_ASSIGNMENT_PROBLEMS} 道题目")
        ids = [item["problem_id"] for item in items]
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("题目重复")
        visible = set(Problem.objects.visible_to(self.context["request"].user).filter(pk__in=ids).values_list("id", flat=True))
        missing = [pid for pid in ids if pid not in visible]
        if missing:
            raise serializers.ValidationError(f"题目不存在或无权使用：{', '.join(map(str, missing))}")
        return items

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start:
            raise serializers.ValidationError("截止时间应晚于开始时间")
        return attrs

    def _save_items(self, assignment, items):
        assignment.items.all().delete()
        AssignmentProblem.objects.bulk_create(
            AssignmentProblem(assignment=assignment, problem_id=item["problem_id"], score=item["score"], order=index)
            for index, item in enumerate(items)
        )

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("problems")
        assignment = Assignment.objects.create(**validated_data)
        self._save_items(assignment, items)
        bump_class(assignment.class_group_id)
        return assignment

    @transaction.atomic
    def update(self, assignment, validated_data):
        items = validated_data.pop("problems", None)
        for key, value in validated_data.items():
            setattr(assignment, key, value)
        assignment.save()
        if items is not None:
            self._save_items(assignment, items)
        bump_class(assignment.class_group_id)
        # 题目、分值、截止时间或迟交规则可能改变，重算已有成绩
        transaction.on_commit(lambda: recalculate_assignment(assignment))
        return assignment


class StudentAssignmentSerializer(serializers.ModelSerializer):
    """学生端作业列表与详情（详情另加 description 与 problems）。"""

    class_name = serializers.CharField(source="class_group.name", read_only=True)
    status = serializers.SerializerMethodField()
    problem_count = serializers.SerializerMethodField()
    total_score = serializers.SerializerMethodField()
    my_score = serializers.SerializerMethodField()
    my_solved = serializers.SerializerMethodField()
    my_late = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            "id",
            "title",
            "class_name",
            "start_time",
            "end_time",
            "allow_late",
            "late_penalty",
            "status",
            "problem_count",
            "total_score",
            "my_score",
            "my_solved",
            "my_late",
        ]

    def _record(self, assignment):
        return self.context.get("records", {}).get(assignment.id)

    def get_status(self, assignment):
        return assignment.status_at(timezone.now())

    def get_problem_count(self, assignment):
        return len(assignment.items.all())

    def get_total_score(self, assignment):
        return sum(item.score for item in assignment.items.all())

    def get_my_score(self, assignment):
        record = self._record(assignment)
        return record.score if record else None

    def get_my_solved(self, assignment):
        record = self._record(assignment)
        return record.solved_count if record else 0

    def get_my_late(self, assignment):
        record = self._record(assignment)
        return bool(record and record.is_late)


class StudentAssignmentDetailSerializer(StudentAssignmentSerializer):
    problems = serializers.SerializerMethodField()

    class Meta(StudentAssignmentSerializer.Meta):
        fields = StudentAssignmentSerializer.Meta.fields + ["description", "problems"]

    def get_problems(self, assignment):
        # 开始前不公布题目
        if assignment.status_at(timezone.now()) == "not_started":
            return []
        record = self._record(assignment)
        details = record.details if record else {}
        problems = []
        for item in assignment.items.all():
            mine = details.get(str(item.problem_id))
            problems.append(
                {
                    "problem_id": item.problem_id,
                    "title": item.problem.title,
                    "difficulty": item.problem.difficulty,
                    "score": item.score,
                    "my_score": mine["score"] if mine else None,
                    "accepted": bool(mine and mine["accepted"]),
                    "late": bool(mine and mine["late"]),
                }
            )
        return problems
