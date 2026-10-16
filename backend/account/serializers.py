from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
# 凭据错误由 simplejwt 抛出的是 DRF 的 AuthenticationFailed
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from . import throttle
from .models import User


class UserSerializer(serializers.ModelSerializer):
    real_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "real_name", "is_initial_password", "created_at"]

    def get_real_name(self, user):
        for attr in ("student_profile", "teacher_profile"):
            profile = getattr(user, attr, None)
            if profile is not None:
                return profile.real_name
        return None


class LoginSerializer(TokenObtainPairSerializer):
    """登录：返回令牌、用户信息，以及是否需要强制修改初始密码。"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        username = attrs.get(User.USERNAME_FIELD, "")
        throttle.ensure_not_locked("login", username)
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            throttle.record_failure("login", username)
            raise
        throttle.clear("login", username)
        data["must_change_password"] = self.user.is_initial_password
        data["user"] = UserSerializer(self.user).data
        return data


def token_payload(user):
    """注册成功后直接登录：返回与登录接口相同的令牌结构。"""
    refresh = LoginSerializer.get_token(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "must_change_password": user.is_initial_password,
        "user": UserSerializer(user).data,
    }


class BindStudentSerializer(serializers.Serializer):
    student_no = serializers.CharField(max_length=32)
    initial_password = serializers.CharField(max_length=32, trim_whitespace=False)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("原密码不正确")
        return value

    def validate(self, attrs):
        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError("新密码不能与原密码相同")
        validate_password(attrs["new_password"], self.context["request"].user)
        return attrs
