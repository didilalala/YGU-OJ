import hashlib
import hmac
import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ParseError
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.permissions import IsAdmin

from .models import JudgeServer, Language
from .serializers import HeartbeatSerializer, JudgeServerSerializer, LanguageSerializer

logger = logging.getLogger(__name__)


def _token_valid(client_token):
    token = settings.JUDGE_SERVER_TOKEN
    if not token:
        logger.error("JUDGE_SERVER_TOKEN 未配置，拒绝判题服务器心跳")
        return False
    expected = hashlib.sha256(token.encode()).hexdigest()
    return hmac.compare_digest(expected.encode(), client_token.encode())


def _reply(error=None, data=None, status=status.HTTP_200_OK):
    return Response({"error": error, "data": data}, status=status)


class JudgeServerHeartbeatView(APIView):
    """
    判题服务器心跳，由 JudgeServer 容器的健康检查每 5 秒调用一次，首次心跳即自动注册。

    请求头 X-Judge-Server-Token 为 sha256(JUDGE_SERVER_TOKEN)。
    JudgeServer 只认 QDUOJ 的响应格式 {"error": ..., "data": ...}（error 为 null 表示成功），
    因此本接口不使用统一响应格式；返回错误会使 judge-server 容器显示 unhealthy。
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]

    def post(self, request):
        if not _token_valid(request.headers.get("X-Judge-Server-Token", "")):
            return _reply("invalid-token", "令牌错误", status.HTTP_403_FORBIDDEN)

        try:
            serializer = HeartbeatSerializer(data=request.data)
            valid = serializer.is_valid()
        except ParseError as exc:
            return _reply("invalid-data", str(exc.detail), status.HTTP_400_BAD_REQUEST)
        if not valid:
            return _reply("invalid-data", serializer.errors, status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        JudgeServer.objects.update_or_create(
            url=data["service_url"],
            defaults={
                "hostname": data["hostname"],
                "ip": request.META.get("REMOTE_ADDR"),
                "judger_version": data["judger_version"],
                "cpu_core": data["cpu_core"],
                "cpu_usage": data["cpu"],
                "memory_usage": data["memory"],
                "last_heartbeat": timezone.now(),
            },
        )
        return _reply()


class JudgeServerListView(generics.ListAPIView):
    """判题服务器状态（管理员）。服务器数量很少，不分页。"""

    permission_classes = [IsAdmin]
    queryset = JudgeServer.objects.all()
    serializer_class = JudgeServerSerializer
    pagination_class = None


class JudgeServerDetailView(generics.UpdateAPIView, generics.DestroyAPIView):
    """
    启用或停用判题服务器（PATCH is_enabled），或删除已下线的服务器记录。
    删除仍在运行的服务器没有意义，它会在下次心跳时重新注册。
    """

    permission_classes = [IsAdmin]
    queryset = JudgeServer.objects.all()
    serializer_class = JudgeServerSerializer
    http_method_names = ["patch", "delete"]


class LanguageListCreateView(generics.ListCreateAPIView):
    """编程语言列表（含已停用的）与新增语言。"""

    permission_classes = [IsAdmin]
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    pagination_class = None


class LanguageDetailView(generics.UpdateAPIView):
    """修改语言的名称、启用状态、排序、编辑器语言、初始代码与判题配置。语言不提供删除，只能停用。"""

    permission_classes = [IsAdmin]
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    http_method_names = ["patch"]

