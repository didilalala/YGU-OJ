from django.urls import path

from . import views

urlpatterns = [
    path("auth/login", views.LoginView.as_view()),
    path("auth/refresh", views.RefreshView.as_view()),
    path("auth/me", views.MeView.as_view()),
    path("auth/change-password", views.ChangePasswordView.as_view()),
    path("auth/register", views.RegisterView.as_view()),
    path("auth/bind-student", views.BindStudentView.as_view()),
    path("profile", views.ProfileView.as_view()),
]
