"""
路由总表。

每个应用提供两组路由：
- urls.py        前台接口，挂在 /api/ 下
- admin_urls.py  管理接口，挂在 /api/admin/ 下（仅教师与管理员）
具体路径在各应用内定义，例如 problem/urls.py 中的 "problems"。
"""

from django.contrib import admin
from django.urls import include, path

from utils.views import health

APPS = [
    "account",
    "announcement",
    "problem",
    "submission",
    "judge",
    "contest",
    "classroom",
    "stats",
    "options",
]

urlpatterns = [
    path("api/health", health),
    path("django-admin/", admin.site.urls),
]
urlpatterns += [path("api/", include(f"{app}.urls")) for app in APPS]
urlpatterns += [path("api/admin/", include(f"{app}.admin_urls")) for app in APPS]
