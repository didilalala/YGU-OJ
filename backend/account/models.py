from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class OJUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("source", User.Source.CREATED)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    用户主表。访客不建账号；在校学生的扩展信息见 StudentProfile。

    username 的取值：普通用户自定，在校学生为学号，教师为工号。
    """

    class Role(models.TextChoices):
        REGULAR = "regular", "普通用户"
        STUDENT = "student", "在校学生"
        TEACHER = "teacher", "教师"
        ADMIN = "admin", "管理员"

    class Source(models.TextChoices):
        REGISTER = "register", "注册"
        IMPORT = "import", "导入"
        CREATED = "created", "管理员创建"

    # 导入的学生没有邮箱，用 NULL 而非空串，避免唯一约束冲突
    email = models.EmailField("邮箱", unique=True, null=True, blank=True)
    role = models.CharField("角色", max_length=16, choices=Role.choices, default=Role.REGULAR)
    is_initial_password = models.BooleanField("是否仍为初始密码", default=False)
    source = models.CharField("来源", max_length=16, choices=Source.choices, default=Source.REGISTER)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    objects = OJUserManager()

    class Meta:
        db_table = "user"
        verbose_name = verbose_name_plural = "用户"

    @property
    def display_name(self):
        """优先显示学生或教师的真实姓名，否则显示用户名。"""
        for attr in ("student_profile", "teacher_profile"):
            try:
                return getattr(self, attr).real_name
            except (StudentProfile.DoesNotExist, TeacherProfile.DoesNotExist):
                continue
        return self.username

    @property
    def is_teacher_or_admin(self):
        # 不叫 is_staff：那是 Django 自带的「可登录 django-admin」字段
        return self.role in (self.Role.TEACHER, self.Role.ADMIN)

    def save(self, *args, **kwargs):
        if not self.email:
            self.email = None
        super().save(*args, **kwargs)


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    student_no = models.CharField("学号", max_length=32, unique=True)
    real_name = models.CharField("姓名", max_length=32)
    college = models.CharField("学院", max_length=64, blank=True)
    major = models.CharField("专业", max_length=64, blank=True)
    grade = models.CharField("年级", max_length=16, blank=True)

    class Meta:
        db_table = "student_profile"
        verbose_name = verbose_name_plural = "在校学生信息"

    def __str__(self):
        return f"{self.student_no} {self.real_name}"


class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    staff_no = models.CharField("工号", max_length=32, unique=True)
    real_name = models.CharField("姓名", max_length=32)
    college = models.CharField("学院", max_length=64, blank=True)

    class Meta:
        db_table = "teacher_profile"
        verbose_name = verbose_name_plural = "教师信息"

    def __str__(self):
        return f"{self.staff_no} {self.real_name}"
