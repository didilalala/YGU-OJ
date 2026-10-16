from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from contest.access import active_exam, ensure_not_locked
from judge.tasks import enqueue_judge, rejudge
from options import site
from utils.exceptions import BusinessError
from utils.permissions import IsTeacherOrAdmin
from utils.request import get_client_ip

from .models import Submission
from .serializers import SubmissionDetailSerializer, SubmissionListSerializer, SubmitSerializer

# 同一用户两次提交的最短间隔（秒），设计说明书 10.1


def _int_param(request, name):
    value = request.query_params.get(name)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError({name: "必须是整数"})


class SubmissionListCreateView(generics.ListCreateAPIView):
    """
    GET  提交记录列表。学生和普通用户只能看到自己的提交；教师与管理员可看全部，
         并可按 user_id 筛选。其他筛选参数：problem_id、result、language。
    POST 提交代码，返回提交编号；评测异步进行，前端轮询 GET /api/submissions/{id}。
    """

    serializer_class = SubmissionListSerializer

    def get_queryset(self):
        request = self.request
        queryset = Submission.objects.select_related("problem", "user").defer(
            "code", "case_info", "error_info", "problem__description"
        )
        # TODO(M9)：教师只能看到本人班级学生的提交
        if request.user.is_teacher_or_admin:
            user_id = _int_param(request, "user_id")
            if user_id is not None:
                queryset = queryset.filter(user_id=user_id)
        else:
            queryset = queryset.filter(user=request.user)
            # 考试期间只能看到本场考试的提交，不能查看历史代码
            exam = active_exam(request.user)
            if exam is not None:
                queryset = queryset.filter(exam=exam)

        problem_id = _int_param(request, "problem_id")
        if problem_id is not None:
            queryset = queryset.filter(problem_id=problem_id)
        for name in ("result", "language"):
            value = request.query_params.get(name)
            if value:
                queryset = queryset.filter(**{name: value})
        return queryset

    def create(self, request):
        serializer = SubmitSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 校验通过后才计入频率限制；cache.add 在键已存在时返回 False，是原子操作
        interval = site.get("submit_interval_seconds")
        if interval and not cache.add(f"submit-interval:{request.user.id}", 1, timeout=interval):
            raise Throttled(detail=f"提交过于频繁，请 {interval} 秒后再试")

        submission = Submission.objects.create(
            user=request.user,
            problem=data["problem"],
            language=data["language"],
            code=data["code"],
            assignment=data.get("assignment"),
            exam=data.get("exam"),
            ip=get_client_ip(request),
        )
        enqueue_judge(submission)
        return Response({"id": submission.id, "result": submission.result}, status=status.HTTP_201_CREATED)


class SubmissionDetailView(generics.RetrieveAPIView):
    """评测结果与代码。仅提交者本人、教师与管理员可见，其他人一律返回不存在。"""

    serializer_class = SubmissionDetailSerializer
    queryset = Submission.objects.select_related("problem", "user")

    def get_object(self):
        submission = super().get_object()
        user = self.request.user
        # TODO(M9)：教师只能看本人班级学生
        if submission.user_id != user.id and not user.is_teacher_or_admin:
            raise NotFound("提交记录不存在")
        # 考试期间学生不能查看考试以外的历史代码
        ensure_not_locked(user, allowed_exam_id=submission.exam_id)
        return submission


class RejudgeView(APIView):
    """重判（教师与管理员），常用于系统错误或修改测试数据之后。"""

    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, pk):
        submission = Submission.objects.filter(pk=pk).first()
        if submission is None:
            raise NotFound("提交记录不存在")
        if not submission.is_finished:
            raise BusinessError("该提交正在等待或进行评测，无需重判")
        rejudge(submission)
        return Response({"id": submission.id, "result": submission.result})
