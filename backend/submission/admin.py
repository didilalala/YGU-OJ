from django.contrib import admin

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "problem", "language", "result", "time_cost", "memory_cost", "created_at"]
    list_filter = ["result", "language"]
    raw_id_fields = ["user", "problem"]
    readonly_fields = ["case_info", "judged_at"]
