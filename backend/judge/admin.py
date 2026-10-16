from django.contrib import admin

from .models import JudgeServer


@admin.register(JudgeServer)
class JudgeServerAdmin(admin.ModelAdmin):
    list_display = ["hostname", "url", "task_count", "cpu_core", "last_heartbeat", "is_enabled"]
    list_filter = ["is_enabled"]
