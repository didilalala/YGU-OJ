from django.contrib import admin

from .models import ClassGroup, ClassMember


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "course", "semester", "teacher", "invite_code"]
    list_filter = ["semester"]
    search_fields = ["name", "course"]
    raw_id_fields = ["teacher"]


@admin.register(ClassMember)
class ClassMemberAdmin(admin.ModelAdmin):
    list_display = ["id", "class_group", "student", "joined_at", "is_removed"]
    list_filter = ["is_removed"]
    raw_id_fields = ["class_group", "student"]
