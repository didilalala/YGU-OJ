from django.urls import path

from . import views

urlpatterns = [
    path("settings", views.AdminSettingsView.as_view()),
]
