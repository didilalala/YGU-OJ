from django.urls import path

from . import views

urlpatterns = [
    path("exams", views.AdminExamListCreateView.as_view()),
    path("exams/<int:pk>", views.AdminExamDetailView.as_view()),
    path("exams/<int:pk>/monitor", views.ExamMonitorView.as_view()),
    path("exams/<int:pk>/participants/<int:user_id>/reopen", views.ReopenParticipantView.as_view()),
]
