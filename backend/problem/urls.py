from django.urls import path

from . import views

urlpatterns = [
    path("problems", views.ProblemListView.as_view()),
    path("problems/<int:pk>", views.ProblemDetailView.as_view()),
    path("knowledge-points", views.KnowledgePointListView.as_view()),
]
