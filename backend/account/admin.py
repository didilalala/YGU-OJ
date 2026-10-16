from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import StudentProfile, TeacherProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "role", "source", "is_initial_password", "is_active"]
    list_filter = ["role", "source", "is_active"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("OJ", {"fields": ["role", "source", "is_initial_password"]}),
    )


admin.site.register(StudentProfile)
admin.site.register(TeacherProfile)
