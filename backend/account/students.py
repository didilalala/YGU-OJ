"""在校学生账号规则（设计说明书 4.3）。"""

import re

from django.conf import settings
from django.contrib.auth.hashers import make_password

from .hashers import InitialPasswordHasher


def is_valid_student_no(student_no):
    return bool(re.fullmatch(settings.STUDENT_NO_PATTERN, student_no or ""))


def initial_password(student_no):
    """初始密码为学号后六位，学号不足六位时使用完整学号。"""
    return student_no[-6:]


def set_initial_password(user, student_no):
    """设为初始密码并要求首次登录修改（调用方负责 save）。"""
    user.password = make_password(initial_password(student_no), hasher=InitialPasswordHasher.algorithm)
    user.is_initial_password = True
