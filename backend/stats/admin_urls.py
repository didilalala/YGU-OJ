from django.urls import path

from . import views

urlpatterns = [
    path("stats/overview", views.OverviewView.as_view()),
    path("stats/classes/<int:pk>", views.ClassStatsView.as_view()),
    path("stats/classes/<int:pk>/export", views.ClassExportView.as_view()),
    path("stats/classes/<int:pk>/knowledge", views.ClassKnowledgeView.as_view()),
    path("stats/assignments/<int:pk>", views.AssignmentStatsView.as_view()),
    path("stats/exams/<int:pk>", views.ExamStatsView.as_view()),
]
