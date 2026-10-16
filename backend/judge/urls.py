from django.urls import path

from . import views

urlpatterns = [
    # 地址与 deploy/docker-compose.yml 中 judge-server 的 BACKEND_URL 一致
    path("judge-server/heartbeat", views.JudgeServerHeartbeatView.as_view()),
]
