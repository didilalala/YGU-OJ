from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import User


class UsernameOrEmailBackend(ModelBackend):
    """支持用户名（学号、工号）或邮箱登录。"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if not username or password is None:
            return None
        user = User.objects.filter(Q(username=username) | Q(email__iexact=username)).first()
        if user is None:
            # 与存在用户时耗时一致，避免通过响应时间探测账号是否存在
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
