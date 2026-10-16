"""普通用户注册（设计说明书 4.1、7.2）。"""

import re

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import User

USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,31}$")


def validate_username(username):
    # 与学号格式相同的用户名留给在校学生导入，否则学生无法使用学号导入
    if re.fullmatch(settings.STUDENT_NO_PATTERN, username):
        raise serializers.ValidationError("用户名不能是纯数字学号，学号请在绑定学号时使用")
    if not USERNAME_RE.match(username):
        raise serializers.ValidationError("用户名以字母开头，只能包含字母、数字和下划线，长度 3–32 位")
    if User.objects.filter(username__iexact=username).exists():
        raise serializers.ValidationError("该用户名已被使用")
    return username


def validate_email(email):
    if User.objects.filter(email__iexact=email).exists():
        raise serializers.ValidationError("该邮箱已被注册")
    return email


def create_regular_user(username, email, password):
    user = User(username=username, email=email, role=User.Role.REGULAR, source=User.Source.REGISTER)
    try:
        user.set_password(password)
        with transaction.atomic():
            user.save()
    except IntegrityError:
        # 注册提交时的并发冲突
        raise serializers.ValidationError("用户名或邮箱已被使用")
    return user


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=32)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)

    def validate_username(self, value):
        return validate_username(value)

    def validate_email(self, value):
        return validate_email(value)

    def validate(self, attrs):
        candidate = User(username=attrs["username"], email=attrs["email"])
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs
