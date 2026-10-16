import ipaddress

from django.conf import settings


def get_client_ip(request):
    """
    客户端真实 IP（考试 IP 段限制、提交记录使用）。

    部署时 Nginx 用 X-Real-IP 覆盖客户端自带的同名请求头，因此只有在
    TRUST_X_REAL_IP 开启（即后端只能经由 Nginx 访问）时才采信该请求头。
    """
    if settings.TRUST_X_REAL_IP:
        real_ip = request.META.get("HTTP_X_REAL_IP", "").strip()
        try:
            return str(ipaddress.ip_address(real_ip))
        except ValueError:
            pass
    return request.META.get("REMOTE_ADDR")
