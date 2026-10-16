from django.urls import path

from . import views

urlpatterns = [
    path("classes/mine", views.MyClassListView.as_view()),
    path("assignments", views.MyAssignmentListView.as_view()),
    path("assignments/<int:pk>", views.MyAssignmentDetailView.as_view()),
]
