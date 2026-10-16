from rest_framework.permissions import BasePermission

from account.models import User


class HasRole(BasePermission):
    """按角色放行；子类只需声明 roles。"""

    roles = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.roles)


class IsStudent(HasRole):
    roles = (User.Role.STUDENT,)


class IsTeacherOrAdmin(HasRole):
    """管理接口（/api/admin/）的默认权限。"""

    roles = (User.Role.TEACHER, User.Role.ADMIN)


class IsAdmin(HasRole):
    roles = (User.Role.ADMIN,)


class IsOwnerOrAdmin(BasePermission):
    """
    对象级权限：管理员可操作全部数据，教师只能操作自己创建的数据。

    视图可通过 owner_field 指定归属字段，默认 "created_by"，
    班级等以 "teacher" 记录归属的模型需改为 owner_field = "teacher"。
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Role.ADMIN:
            return True
        owner_field = getattr(view, "owner_field", "created_by")
        return getattr(obj, f"{owner_field}_id", None) == request.user.id
