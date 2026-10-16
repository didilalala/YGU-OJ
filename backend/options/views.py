from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.exceptions import BusinessError
from utils.permissions import IsAdmin

from . import site


class SiteView(APIView):
    """站点信息：网站参数（公开部分）与已启用的编程语言。访客也可读取。"""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(site.public_payload())


class AdminSettingsView(APIView):
    """网站参数的管理：列出全部参数（含说明与取值范围），批量修改。"""

    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({"items": site.definitions()})

    def patch(self, request):
        if not isinstance(request.data, dict) or not request.data:
            raise BusinessError("请提交要修改的参数")
        errors, current = site.update(request.user, request.data)
        if errors:
            raise BusinessError("部分参数不合法，未保存任何修改：" + "；".join(f"{k}：{v}" for k, v in errors.items()), data=errors)
        return Response({"items": site.definitions()})
