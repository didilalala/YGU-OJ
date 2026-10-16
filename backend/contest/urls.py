from django.urls import path

from . import views

urlpatterns = [
    path("exams", views.MyExamListView.as_view()),
    path("exams/active", views.ActiveExamView.as_view()),
    path("exams/<int:pk>", views.MyExamDetailView.as_view()),
    path("exams/<int:pk>/join", views.JoinExamView.as_view()),
    path("exams/<int:pk>/finish", views.FinishExamView.as_view()),
    path("exams/<int:pk>/rank", views.ExamRankView.as_view()),
    path("contests", views.ContestListView.as_view()),
]
