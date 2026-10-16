from io import BytesIO
from urllib.parse import quote

from django.db.models import Count, OuterRef, ProtectedError, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from contest.access import ensure_not_locked
from stats.cache import bump_class
from utils.exceptions import BusinessError
from utils.permissions import IsTeacherOrAdmin

from . import importing
from .models import Assignment, ClassGroup, ClassMember, ScoreRecord
from .serializers import (
    AddStudentSerializer,
    AdminAssignmentSerializer,
    AssignmentItemSerializer,
    ClassGroupSerializer,
    ClassMemberSerializer,
    MyClassSerializer,
    StudentAssignmentDetailSerializer,
    StudentAssignmentSerializer,
    UserIdsSerializer,
)


def managed_classes(user):
    """管理员看全部班级，教师只看自己的班级；附带在班人数。"""
    queryset = ClassGroup.objects.select_related("teacher__teacher_profile").annotate(
        member_count=Count("members", filter=Q(members__is_removed=False))
    )
    if user.role != user.Role.ADMIN:
        queryset = queryset.filter(teacher=user)
    return queryset


def get_managed_class(request, pk):
    class_group = ClassGroup.objects.filter(pk=pk).first()
    if class_group is None:
        raise NotFound("班级不存在")
    if not class_group.can_manage(request.user):
        # 教师看不到别人的班级，与不存在一样处理
        raise NotFound("班级不存在")
    return class_group


# ---------------------------------------------------------------- 学生端


class MyClassListView(generics.ListAPIView):
    """学生查看自己所在的班级（已移出的不显示）。"""

    serializer_class = MyClassSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            ClassGroup.objects.filter(members__student=self.request.user, members__is_removed=False)
            .select_related("teacher__teacher_profile")
            .order_by("-id")
        )


# ---------------------------------------------------------------- 管理端


class ClassListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = ClassGroupSerializer

    def get_queryset(self):
        queryset = managed_classes(self.request.user)
        keyword = self.request.query_params.get("keyword", "").strip()
        if keyword:
            queryset = queryset.filter(Q(name__icontains=keyword) | Q(course__icontains=keyword))
        semester = self.request.query_params.get("semester")
        if semester:
            queryset = queryset.filter(semester=semester)
        return queryset

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data["member_count"] = 0
        return response


class ClassDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    删除班级只删除班级与成员关系，学生账号保留；已布置作业或考试的班级不能删除。
    """

    permission_classes = [IsTeacherOrAdmin]
    serializer_class = ClassGroupSerializer

    def get_object(self):
        class_group = managed_classes(self.request.user).filter(pk=self.kwargs["pk"]).first()
        if class_group is None:
            raise NotFound("班级不存在")
        return class_group

    def perform_destroy(self, class_group):
        try:
            class_group.delete()
        except ProtectedError:
            raise BusinessError("该班级已布置作业或考试，不能删除")


class ClassStudentListView(generics.ListCreateAPIView):
    """
    GET  班级学生，可按 keyword（学号或姓名）筛选；include_removed=1 时包含已移出的学生。
    POST 手动添加单个学生，规则与名单导入相同，返回导入报告。
    """

    permission_classes = [IsTeacherOrAdmin]
    serializer_class = ClassMemberSerializer

    def get_queryset(self):
        class_group = get_managed_class(self.request, self.kwargs["pk"])
        queryset = ClassMember.objects.filter(class_group=class_group).select_related("student__student_profile")
        if self.request.query_params.get("include_removed") != "1":
            queryset = queryset.filter(is_removed=False)
        keyword = self.request.query_params.get("keyword", "").strip()
        if keyword:
            queryset = queryset.filter(
                Q(student__student_profile__student_no__icontains=keyword)
                | Q(student__student_profile__real_name__icontains=keyword)
            )
        return queryset.order_by("is_removed", "student__student_profile__student_no")

    def create(self, request, pk):
        class_group = get_managed_class(request, pk)
        serializer = AddStudentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = importing.StudentRow(row=None, **serializer.validated_data)
        report = importing.import_students(class_group, [row])
        if report.failed:
            raise BusinessError(report.failed[0]["reason"])
        if report.already_in_class:
            raise BusinessError("该学生已在班级中")
        return Response(report.as_dict(), status=status.HTTP_201_CREATED)


class ClassImportView(APIView):
    """Excel 批量导入学生（.xlsx），返回导入报告。"""

    permission_classes = [IsTeacherOrAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request, pk):
        class_group = get_managed_class(request, pk)
        file = request.FILES.get("file")
        if file is None:
            raise ValidationError({"file": "请选择学生名单文件"})
        if file.size > importing.MAX_FILE_SIZE:
            raise BusinessError("名单文件不能超过 5MB")
        try:
            rows = importing.read_rows(file)
        except importing.StudentImportError as exc:
            raise BusinessError(str(exc))
        report = importing.import_students(class_group, rows)
        return Response(report.as_dict())


class ImportTemplateView(APIView):
    """下载学生名单 Excel 模板。返回文件本身，不经统一响应格式。"""

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        buffer = BytesIO()
        importing.build_template().save(buffer)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = quote("学生名单导入模板.xlsx")
        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{filename}"
        return response


class RemoveStudentsView(APIView):
    """移出学生：历史成绩保留，不再出现在本班后续统计中。"""

    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, pk):
        class_group = get_managed_class(request, pk)
        serializer = UserIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        count = importing.remove_members(class_group, serializer.validated_data["user_ids"])
        return Response({"count": count})


class ResetPasswordView(APIView):
    """把本班学生的密码重置为初始密码（学号后六位），登录后须重新修改。"""

    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, pk):
        class_group = get_managed_class(request, pk)
        serializer = UserIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        count = importing.reset_passwords(class_group, serializer.validated_data["user_ids"])
        return Response({"count": count})


# ---------------------------------------------------------------- 作业


def _member_count_subquery():
    return Subquery(
        ClassMember.objects.filter(class_group=OuterRef("class_group"), is_removed=False)
        .values("class_group")
        .annotate(count=Count("id"))
        .values("count")[:1]
    )


def managed_assignments(user):
    queryset = (
        Assignment.objects.select_related("class_group")
        .prefetch_related("items__problem")
        .annotate(
            submitted_count=Count("score_records", distinct=True),
            member_count=Coalesce(_member_count_subquery(), 0),
        )
    )
    if user.role != user.Role.ADMIN:
        queryset = queryset.filter(class_group__teacher=user)
    return queryset


class AdminAssignmentListCreateView(generics.ListCreateAPIView):
    """作业列表（可按 class_id 筛选）与布置作业。"""

    permission_classes = [IsTeacherOrAdmin]
    serializer_class = AdminAssignmentSerializer

    def get_queryset(self):
        queryset = managed_assignments(self.request.user)
        class_id = self.request.query_params.get("class_id")
        if class_id:
            if not class_id.isdigit():
                raise ValidationError({"class_id": "必须是整数"})
            queryset = queryset.filter(class_group_id=int(class_id))
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        return Response(
            AdminAssignmentSerializer(managed_assignments(request.user).get(pk=assignment.pk)).data,
            status=status.HTTP_201_CREATED,
        )


class AdminAssignmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = AdminAssignmentSerializer

    def get_object(self):
        assignment = managed_assignments(self.request.user).filter(pk=self.kwargs["pk"]).first()
        if assignment is None:
            raise NotFound("作业不存在")
        return assignment

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(AdminAssignmentSerializer(self.get_object()).data)

    def perform_destroy(self, assignment):
        bump_class(assignment.class_group_id)
        try:
            assignment.delete()
        except ProtectedError:
            raise BusinessError("已有学生提交，不能删除；如需隐藏请取消发布")


class AssignmentResultView(APIView):
    """
    作业成绩表：在班学生 × 各题最高得分。未提交的学生也列出（submitted 为 false）。
    成绩分布、通过率等统计见 M11。
    """

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, pk):
        assignment = managed_assignments(request.user).filter(pk=pk).first()
        if assignment is None:
            raise NotFound("作业不存在")
        items = list(assignment.items.all())
        records = {r.student_id: r for r in ScoreRecord.objects.filter(assignment=assignment)}
        members = (
            ClassMember.objects.active()
            .filter(class_group=assignment.class_group)
            .select_related("student__student_profile")
            .order_by("student__student_profile__student_no")
        )

        rows = []
        for member in members:
            student = member.student
            profile = getattr(student, "student_profile", None)
            record = records.get(student.id)
            details = record.details if record else {}
            rows.append(
                {
                    "user_id": student.id,
                    "student_no": profile.student_no if profile else student.username,
                    "real_name": profile.real_name if profile else "",
                    "submitted": record is not None,
                    "score": record.score if record else 0,
                    "solved_count": record.solved_count if record else 0,
                    "is_late": bool(record and record.is_late),
                    "problems": {str(item.problem_id): details.get(str(item.problem_id)) for item in items},
                }
            )

        total_score = sum(item.score for item in items)
        submitted = [row for row in rows if row["submitted"]]
        return Response(
            {
                "assignment": AdminAssignmentSerializer(assignment).data,
                "problems": AssignmentItemSerializer(items, many=True).data,
                "rows": rows,
                "summary": {
                    "member_count": len(rows),
                    "submitted_count": len(submitted),
                    # 平均分按全班计算，未提交按 0 分
                    "average_score": round(sum(r["score"] for r in rows) / len(rows), 2) if rows else 0,
                    "full_score_count": sum(1 for r in rows if total_score and r["score"] >= total_score),
                },
            }
        )


def _my_records(user, assignments):
    ids = [a.id for a in assignments]
    return {r.assignment_id: r for r in ScoreRecord.objects.filter(student=user, assignment_id__in=ids)}


def _student_assignments(user):
    return (
        Assignment.objects.filter(
            is_published=True,
            class_group__members__student=user,
            class_group__members__is_removed=False,
        )
        .select_related("class_group")
        .prefetch_related("items__problem")
        .distinct()
    )


class MyAssignmentListView(generics.ListAPIView):
    """
    我的作业：所在班级已发布的作业。status 筛选：
      todo 待完成（进行中或可迟交）、not_started 未开始、ended 已结束（截止且不可迟交）。
    """

    serializer_class = StudentAssignmentSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = _student_assignments(self.request.user)
        now = timezone.now()
        status_filter = self.request.query_params.get("status")
        if status_filter == "todo":
            queryset = queryset.filter(start_time__lte=now).filter(Q(end_time__gte=now) | Q(allow_late=True))
            return queryset.order_by("end_time")
        if status_filter == "not_started":
            return queryset.filter(start_time__gt=now).order_by("start_time")
        if status_filter == "ended":
            return queryset.filter(end_time__lt=now, allow_late=False).order_by("-end_time")
        return queryset.order_by("-end_time")

    def list(self, request):
        ensure_not_locked(request.user)
        assignments = list(self.get_queryset())
        context = {**self.get_serializer_context(), "records": _my_records(request.user, assignments)}
        return Response(StudentAssignmentSerializer(assignments, many=True, context=context).data)


class MyAssignmentDetailView(APIView):
    def get(self, request, pk):
        ensure_not_locked(request.user)
        assignment = _student_assignments(request.user).filter(pk=pk).first()
        if assignment is None:
            raise NotFound("作业不存在")
        context = {"request": request, "records": _my_records(request.user, [assignment])}
        return Response(StudentAssignmentDetailSerializer(assignment, context=context).data)
