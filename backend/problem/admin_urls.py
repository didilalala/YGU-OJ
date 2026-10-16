from django.urls import path

from . import views

urlpatterns = [
    path("problems", views.AdminProblemListCreateView.as_view()),
    path("problems/<int:pk>", views.AdminProblemDetailView.as_view()),
    path("problems/test-cases", views.TestCaseUploadView.as_view()),
    path("problems/import-fps", views.FPSImportView.as_view()),
    path("knowledge-points", views.AdminKnowledgePointCreateView.as_view()),
    path("knowledge-points/<int:pk>", views.AdminKnowledgePointDetailView.as_view()),
]
