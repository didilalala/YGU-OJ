from django.contrib import admin

from .models import Exam, ExamParticipant


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "class_group", "rule_type", "start_time", "end_time", "is_published"]
    list_filter = ["rule_type", "is_published"]
    raw_id_fields = ["class_group", "created_by"]


@admin.register(ExamParticipant)
class ExamParticipantAdmin(admin.ModelAdmin):
    list_display = ["id", "exam", "student", "joined_at", "join_ip", "finished_at"]
    raw_id_fields = ["exam", "student"]
