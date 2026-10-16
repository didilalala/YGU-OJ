from django.urls import path

from . import views

urlpatterns = [
    path("judge-servers", views.JudgeServerListView.as_view()),
    path("judge-servers/<int:pk>", views.JudgeServerDetailView.as_view()),
    path("languages", views.LanguageListCreateView.as_view()),
    path("languages/<int:pk>", views.LanguageDetailView.as_view()),
]
