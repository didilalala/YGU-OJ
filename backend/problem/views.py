import shutil

from django.db import transaction
from django.db.models import Count, ProtectedError, Q
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import SAFE_METHODS, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from classroom.access import assignment_problem
from contest.access import ensure_not_locked, exam_problem
from submission.models import Submission
from utils.exceptions import BusinessError
from utils.permissions import IsTeacherOrAdmin

from . import fps, test_cases
from .models import KnowledgePoint, Problem
from .serializers import (
    AdminProblemListSerializer,
    AdminProblemSerializer,
    KnowledgePointSerializer,
    ProblemDetailSerializer,
    ProblemListSerializer,
)


def _int_param(request, name):
    value = request.query_params.get(name)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError({name: "必须是整数"})


def filter_problems(queryset, request):
    """
    通用筛选参数：
      difficulty       难度
      knowledge_point  知识点编号，包含其下级知识点
      keyword          标题关键字或题号
    """
    difficulty = request.query_params.get("difficulty")
    if difficulty:
        queryset = queryset.filter(difficulty=difficulty)

    point_id = _int_param(request, "knowledge_point")
    if point_id is not None:
        point_ids = KnowledgePoint.with_descendants(point_id)
        queryset = queryset.filter(knowledge_points__in=point_ids).distinct()

    keyword = request.query_params.get("keyword", "").strip()
    if keyword:
        condition = Q(title__icontains=keyword)
        if keyword.isdigit():
            condition |= Q(pk=int(keyword))
        queryset = queryset.filter(condition)
    return queryset


def my_status(user, problem_ids):
    """当前用户在这些题目上的做题状态：{题目编号: "AC" | "TRIED"}。"""
    if not user.is_authenticated or not problem_ids:
        return {}
    rows = (
        Submission.objects.filter(user=user, problem_id__in=problem_ids)
        .values("problem_id")
        .annotate(accepted=Count("id", filter=Q(result=Submission.Result.AC)))
    )
    return {row["problem_id"]: "AC" if row["accepted"] else "TRIED" for row in rows}


def discard_test_cases_later(test_case_id):
    """事务提交后删除不再被任何题目引用的测试数据。"""
    if not test_case_id:
        return

    def discard():
        if not Problem.objects.filter(test_case_id=test_case_id).exists():
            shutil.rmtree(test_cases.test_case_dir(test_case_id), ignore_errors=True)

    transaction.on_commit(discard)


# ---------------------------------------------------------------- 前台


class ProblemListView(generics.ListAPIView):
    """题目列表，访客也可浏览公开题目。"""

    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Problem.objects.visible_to(self.request.user).prefetch_related("knowledge_points")
        return filter_problems(queryset, self.request)

    def list(self, request):
        ensure_not_locked(request.user)
        page = self.paginate_queryset(self.get_queryset())
        context = {**self.get_serializer_context(), "my_status": my_status(request.user, [p.id for p in page])}
        return self.get_paginated_response(ProblemListSerializer(page, many=True, context=context).data)


class ProblemDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Problem.objects.visible_to(self.request.user).prefetch_related("knowledge_points")

    def retrieve(self, request, pk):
        exam_id = _int_param(request, "exam_id")
        assignment_id = _int_param(request, "assignment_id")
        if exam_id is not None:
            # 考试中的题目对参加考试的学生可见（含私有题目）
            exam_problem(request, exam_id, pk)
            problem = Problem.objects.prefetch_related("knowledge_points").filter(pk=pk).first()
        elif assignment_id is not None:
            ensure_not_locked(request.user)
            # 作业中的题目对班级学生可见（含私有题目）
            assignment_problem(request.user, assignment_id, pk)
            problem = Problem.objects.prefetch_related("knowledge_points").filter(pk=pk).first()
        else:
            ensure_not_locked(request.user)
            problem = self.get_queryset().filter(pk=pk).first()
        if problem is None:
            raise NotFound("题目不存在")
        context = {**self.get_serializer_context(), "my_status": my_status(request.user, [problem.id])}
        return Response(ProblemDetailSerializer(problem, context=context).data)


class KnowledgePointListView(generics.ListAPIView):
    """知识点（平铺列表，前端按 parent 组装成树），可按 course 筛选。"""

    permission_classes = [AllowAny]
    serializer_class = KnowledgePointSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = KnowledgePoint.objects.all()
        course = self.request.query_params.get("course")
        return queryset.filter(course=course) if course else queryset


# ---------------------------------------------------------------- 管理


class AdminProblemListCreateView(generics.ListCreateAPIView):
    """
    GET  题库：管理员看全部，教师看公开题目与自己的私有题目，can_edit 表示能否编辑。
         额外筛选参数：mine=1 只看自己创建的、is_public=0/1。
    POST 创建题目，test_case_id 来自测试数据上传接口。
    """

    permission_classes = [IsTeacherOrAdmin]

    def get_serializer_class(self):
        return AdminProblemSerializer if self.request.method == "POST" else AdminProblemListSerializer

    def get_queryset(self):
        request = self.request
        queryset = (
            Problem.objects.visible_to(request.user)
            .select_related("created_by")
            .prefetch_related("knowledge_points")
            .defer("description", "input_desc", "output_desc", "hint", "samples", "template_code")
        )
        if request.query_params.get("mine") == "1":
            queryset = queryset.filter(created_by=request.user)
        is_public = request.query_params.get("is_public")
        if is_public in ("0", "1"):
            queryset = queryset.filter(is_public=is_public == "1")
        return filter_problems(queryset, request)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AdminProblemDetailView(generics.RetrieveUpdateDestroyAPIView):
    """查看、编辑、删除题目。只能编辑和删除自己创建的题目（管理员不限）。"""

    permission_classes = [IsTeacherOrAdmin]
    serializer_class = AdminProblemSerializer

    def get_object(self):
        problem = (
            Problem.objects.visible_to(self.request.user)
            .select_related("created_by")
            .filter(pk=self.kwargs["pk"])
            .first()
        )
        if problem is None:
            raise NotFound("题目不存在")
        if self.request.method not in SAFE_METHODS and not problem.can_edit(self.request.user):
            raise PermissionDenied("只能修改自己创建的题目")
        return problem

    def perform_update(self, serializer):
        old_test_case_id = serializer.instance.test_case_id
        problem = serializer.save()
        if problem.test_case_id != old_test_case_id:
            discard_test_cases_later(old_test_case_id)

    def perform_destroy(self, problem):
        if problem.submissions.exists():
            raise BusinessError("该题目已有提交记录，不能删除；如需下架请设为私有")
        test_case_id = problem.test_case_id
        problem.delete()
        discard_test_cases_later(test_case_id)


class TestCaseUploadView(APIView):
    """
    上传测试数据 zip，返回 test_case_id，创建或编辑题目时引用该编号。

    压缩包中每组数据为同名的 .in 与 .out（如 1.in / 1.out），可放在子目录中，
    按名称自然排序（1, 2, 10）后重新编号；忽略其他文件。
    未被任何题目引用的测试数据由 cleanup_test_cases 命令定期清理。
    """

    permission_classes = [IsTeacherOrAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("file")
        if file is None:
            raise ValidationError({"file": "请选择测试数据压缩包"})
        if file.size > test_cases.MAX_ZIP_SIZE:
            raise BusinessError(f"压缩包不能超过 {test_cases.MAX_ZIP_SIZE // 1024 // 1024}MB")

        try:
            test_case_id, names = test_cases.save_test_cases_from_zip(file)
        except test_cases.TestCaseError as exc:
            raise BusinessError(str(exc))

        info = test_cases.load_info(test_case_id)
        cases = [
            {
                "index": index,
                "name": name,
                "input_size": info["test_cases"][str(index)]["input_size"],
                "output_size": info["test_cases"][str(index)]["output_size"],
            }
            for index, name in enumerate(names, start=1)
        ]
        return Response({"test_case_id": test_case_id, "test_cases": cases}, status=status.HTTP_201_CREATED)


class FPSImportView(APIView):
    """
    导入 FPS 文件（HUSTOJ 等系统导出的题目 XML）。
    导入的题目为私有、创建者为当前用户；特判题跳过。全部成功或全部不导入。
    """

    permission_classes = [IsTeacherOrAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("file")
        if file is None:
            raise ValidationError({"file": "请选择 FPS 文件"})
        if file.size > fps.MAX_FPS_SIZE:
            raise BusinessError(f"FPS 文件不能超过 {fps.MAX_FPS_SIZE // 1024 // 1024}MB")
        try:
            items = fps.parse_fps(file)
        except fps.FPSError as exc:
            raise BusinessError(str(exc))

        created, skipped, saved_test_case_ids = [], [], []
        try:
            with transaction.atomic():
                for item in items:
                    if item.skip_reason:
                        skipped.append({"title": item.title, "reason": item.skip_reason})
                        continue
                    test_case_id = test_cases.save_test_cases(item.test_cases) if item.test_cases else ""
                    if test_case_id:
                        saved_test_case_ids.append(test_case_id)
                    problem = Problem.objects.create(
                        title=item.title,
                        description=item.description,
                        input_desc=item.input_desc,
                        output_desc=item.output_desc,
                        samples=item.samples,
                        hint=item.hint,
                        source=item.source,
                        time_limit=item.time_limit,
                        memory_limit=item.memory_limit,
                        test_case_id=test_case_id,
                        is_public=False,
                        created_by=request.user,
                    )
                    created.append(
                        {
                            "id": problem.id,
                            "title": problem.title,
                            "test_case_count": len(item.test_cases),
                            "warnings": item.warnings,
                        }
                    )
        except BaseException:
            for test_case_id in saved_test_case_ids:
                shutil.rmtree(test_cases.test_case_dir(test_case_id), ignore_errors=True)
            raise
        return Response({"created": created, "skipped": skipped}, status=status.HTTP_201_CREATED)


class AdminKnowledgePointCreateView(generics.CreateAPIView):
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = KnowledgePointSerializer


class AdminKnowledgePointDetailView(generics.UpdateAPIView, generics.DestroyAPIView):
    """修改或删除知识点；有下级知识点时不能删除，删除后题目上的该标签一并移除。"""

    permission_classes = [IsTeacherOrAdmin]
    serializer_class = KnowledgePointSerializer
    queryset = KnowledgePoint.objects.all()
    http_method_names = ["patch", "delete"]

    def perform_destroy(self, point):
        try:
            point.delete()
        except ProtectedError:
            raise BusinessError("请先删除或移动该知识点的下级知识点")
