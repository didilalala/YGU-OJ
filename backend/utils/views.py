from django.core.cache import cache
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """健康检查：确认数据库与 Redis 可用，供部署脚本和容器探活使用。"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    cache.set("health", 1, 5)
    return Response({"database": "ok", "redis": "ok" if cache.get("health") else "error"})
