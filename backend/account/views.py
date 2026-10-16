from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.exceptions import BusinessError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from options import site

from . import binding, profile, registration
from .serializers import (
    BindStudentSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    UserSerializer,
    token_payload,
)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.is_initial_password = False
        user.save(update_fields=["password", "is_initial_password"])
        return Response(None)


class RegisterView(APIView):
    """普通用户注册，成功后直接登录。"""

    permission_classes = [AllowAny]

    def post(self, request):
        if not site.get("allow_registration"):
            raise BusinessError("注册已关闭，如需账号请联系任课教师")
        serializer = registration.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = registration.create_regular_user(data["username"], data["email"], data["password"])
        return Response(token_payload(user), status=status.HTTP_201_CREATED)


class BindStudentView(APIView):
    """普通用户用「学号 + 初始密码」绑定为在校学生；账号数据保留。"""

    def post(self, request):
        serializer = BindStudentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = binding.bind_student(
            request.user,
            serializer.validated_data["student_no"].strip(),
            serializer.validated_data["initial_password"],
        )
        return Response(UserSerializer(user).data)


class ProfileView(APIView):
    """个人主页：个人信息与做题统计。"""

    def get(self, request):
        return Response(profile.profile(request.user))

