from django.urls import path

from . import views

urlpatterns = [
    path("classes", views.ClassListCreateView.as_view()),
    path("classes/import-template", views.ImportTemplateView.as_view()),
    path("classes/<int:pk>", views.ClassDetailView.as_view()),
    path("classes/<int:pk>/students", views.ClassStudentListView.as_view()),
    path("classes/<int:pk>/import", views.ClassImportView.as_view()),
    path("classes/<int:pk>/remove-students", views.RemoveStudentsView.as_view()),
    path("classes/<int:pk>/reset-password", views.ResetPasswordView.as_view()),
    path("assignments", views.AdminAssignmentListCreateView.as_view()),
    path("assignments/<int:pk>", views.AdminAssignmentDetailView.as_view()),
    path("assignments/<int:pk>/results", views.AssignmentResultView.as_view()),
]
