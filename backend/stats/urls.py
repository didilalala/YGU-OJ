from django.urls import path

from . import views

urlpatterns = [
    path("scores/mine", views.MyScoresView.as_view()),
]
