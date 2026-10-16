from django.contrib import admin

from .models import KnowledgePoint, Problem


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "difficulty", "is_public", "submission_count", "accepted_count"]
    list_filter = ["difficulty", "is_public", "is_template"]
    search_fields = ["title"]
    readonly_fields = ["submission_count", "accepted_count"]


@admin.register(KnowledgePoint)
class KnowledgePointAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "parent", "course"]
    list_filter = ["course"]
