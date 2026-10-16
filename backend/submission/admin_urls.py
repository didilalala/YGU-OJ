from django.urls import path

from . import views

urlpatterns = [
    path("submissions/<int:pk>/rejudge", views.RejudgeView.as_view()),
]
