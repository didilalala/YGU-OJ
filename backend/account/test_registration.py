from datetime import timedelta

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from account.models import StudentProfile, User
from classroom.models import Assignment, AssignmentProblem, ClassGroup, ClassMember, ScoreRecord
from contest.models import Exam, ExamParticipant, ExamProblem
from problem.models import Problem
from submission.models import Submission

from . import throttle
from .students import set_initial_password

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PASSWORD = "Coder-2026!"


@override_settings(CACHES=LOCMEM_CACHE)
class AccountTestBase(APITestCase):
    def setUp(self):
        cache.clear()

    def register(self, **overrides):
        payload = {"username": "coder_li", "email": "li@example.edu", "password": PASSWORD, **overrides}
        return self.client.post("/api/auth/register", payload, format="json")

    def login(self, username, password):
        return self.client.post("/api/auth/login", {"username": username, "password": password}, format="json")

    def auth(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def make_imported_student(self, student_no, name="张三"):
        """教师导入名单时创建的学号账号：初始密码为学号后六位。"""
        user = User(username=student_no, role=User.Role.STUDENT, source=User.Source.IMPORT)
        set_initial_password(user, student_no)
        user.save()
        StudentProfile.objects.create(user=user, student_no=student_no, real_name=name)
        return user


class RegisterTests(AccountTestBase):
    def test_register_logs_in_immediately(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertTrue(data["access"] and data["refresh"])
        self.assertEqual(data["user"]["role"], "regular")
        self.assertFalse(data["must_change_password"])
        user = User.objects.get(username="coder_li")
        self.assertEqual((user.role, user.source, user.email), ("regular", "register", "li@example.edu"))
        self.assertTrue(user.check_password(PASSWORD))

    def test_can_login_with_username_or_email(self):
        self.register()
        self.assertEqual(self.login("coder_li", PASSWORD).status_code, 200)
        self.assertEqual(self.login("LI@example.edu", PASSWORD).status_code, 200)

    def test_duplicate_username_and_email(self):
        self.register()
        response = self.register(username="CODER_LI", email="other@example.edu")
        self.assertEqual(response.status_code, 400)
        self.assertIn("该用户名已被使用", response.json()["message"])

        response = self.register(username="another", email="LI@EXAMPLE.EDU")
        self.assertIn("该邮箱已被注册", response.json()["message"])

    def test_username_rules(self):
        cases = [
            ("ab", "3–32"),
            ("1abc", "字母开头"),
            ("有中文", "字母开头"),
        ]
        for username, message in cases:
            with self.subTest(username=username):
                response = self.register(username=username)
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, str(response.json()["message"]))

    def test_too_long_username_is_rejected(self):
        self.assertEqual(self.register(username="x" * 33).status_code, 400)

    def test_student_number_cannot_be_registered_as_username(self):
        response = self.register(username="20260001")
        self.assertEqual(response.status_code, 400)
        self.assertIn("纯数字学号", str(response.json()["message"]))

    def test_password_validation(self):
        response = self.register(password="123")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()["data"]["password"])
        self.assertFalse(User.objects.filter(username="coder_li").exists())

    def test_invalid_email(self):
        self.assertEqual(self.register(email="not-an-email").status_code, 400)


class LoginLockoutTests(AccountTestBase):
    def setUp(self):
        super().setUp()
        self.register()

    def test_locks_after_five_failures(self):
        for _ in range(5):
            self.assertEqual(self.login("coder_li", "wrong-pass").status_code, 401)

        # 锁定期间即使密码正确也拒绝
        response = self.login("coder_li", PASSWORD)
        self.assertEqual(response.status_code, 400)
        self.assertIn("临时锁定", response.json()["message"])

    def test_success_resets_counter(self):
        for _ in range(4):
            self.login("coder_li", "wrong-pass")
        self.assertEqual(self.login("coder_li", PASSWORD).status_code, 200)
        for _ in range(4):
            self.login("coder_li", "wrong-pass")
        self.assertEqual(self.login("coder_li", PASSWORD).status_code, 200)

    def test_unknown_user_counts_too(self):
        for _ in range(5):
            self.login("nobody", "x")
        self.assertIn("临时锁定", self.login("nobody", "x").json()["message"])

    def test_lock_expires(self):
        for _ in range(5):
            self.login("coder_li", "wrong-pass")
        cache.clear()  # 模拟锁定时间已过
        self.assertEqual(self.login("coder_li", PASSWORD).status_code, 200)

    def test_throttle_scope_is_case_insensitive(self):
        throttle.record_failure("login", "Coder_Li")
        throttle.record_failure("login", "coder_li")
        self.assertEqual(cache.get("auth-fail:login:coder_li"), 2)


class BindStudentTests(AccountTestBase):
    def setUp(self):
        super().setUp()
        self.regular = User.objects.create_user("coder_li", password=PASSWORD, email="li@example.edu")
        self.placeholder = self.make_imported_student("20260001", "李四")
        self.klass = ClassGroup.objects.create(
            name="软件 2601", teacher=User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        )
        self.problem = Problem.objects.create(title="A+B", description="d", is_public=True, test_case_id="a" * 32)

    def bind(self, user=None, student_no="20260001", password="260001"):
        return self.auth(user or self.regular).post(
            "/api/auth/bind-student", {"student_no": student_no, "initial_password": password}, format="json"
        )

    def test_bind_upgrades_account_and_keeps_history(self):
        now = timezone.now()
        assignment = Assignment.objects.create(
            class_group=self.klass, title="作业", is_published=True, start_time=now - timedelta(days=1), end_time=now + timedelta(days=1)
        )
        AssignmentProblem.objects.create(assignment=assignment, problem=self.problem, score=100)
        # 绑定前的练习提交与班级成员关系（绑定后应归到本账号）
        practice = Submission.objects.create(user=self.regular, problem=self.problem, language="c", code="x", result="AC")
        ClassMember.objects.create(class_group=self.klass, student=self.placeholder)
        Submission.objects.create(
            user=self.placeholder, problem=self.problem, language="c", code="x", result="AC", assignment=assignment
        )
        ScoreRecord.objects.create(student=self.placeholder, assignment=assignment, score=100, solved_count=1)

        response = self.bind()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["role"], "student")
        self.assertEqual(response.json()["data"]["real_name"], "李四")
        self.regular.refresh_from_db()
        self.assertEqual(self.regular.role, "student")
        self.assertEqual(self.regular.username, "coder_li")  # 登录名不变
        self.assertFalse(User.objects.filter(username="20260001").exists())
        self.assertEqual(self.regular.student_profile.student_no, "20260001")
        self.assertEqual(self.regular.student_profile.real_name, "李四")
        self.assertEqual(Submission.objects.filter(user=self.regular).count(), 2)
        self.assertTrue(Submission.objects.get(pk=practice.pk).user_id == self.regular.id)
        self.assertTrue(ClassMember.objects.filter(student=self.regular, class_group=self.klass).exists())
        # 成绩按转过来的提交重算
        self.assertEqual(ScoreRecord.objects.get(student=self.regular, assignment=assignment).score, 100)

    def test_bound_student_logs_in_with_registered_credentials(self):
        self.bind()
        self.assertEqual(self.login("coder_li", PASSWORD).json()["data"]["user"]["role"], "student")
        self.assertEqual(self.login("20260001", "260001").status_code, 401)

    def test_wrong_initial_password_is_rejected_and_counted(self):
        response = self.bind(password="000000")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "学号或初始密码不正确")
        self.assertEqual(cache.get("auth-fail:bind:%s" % self.regular.id), 1)
        self.regular.refresh_from_db()
        self.assertEqual(self.regular.role, "regular")

    def test_unknown_student_number_gives_same_message(self):
        response = self.bind(student_no="20269999", password="269999")
        self.assertEqual(response.json()["message"], "学号或初始密码不正确")

    def test_bind_locks_after_five_failures(self):
        for _ in range(5):
            self.bind(password="000000")
        response = self.bind()
        self.assertIn("临时锁定", response.json()["message"])

    def test_activated_placeholder_cannot_be_claimed(self):
        self.placeholder.set_password("Changed-2026!")
        self.placeholder.is_initial_password = False
        self.placeholder.save()
        response = self.bind()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "学号或初始密码不正确")

    def test_already_student_cannot_bind(self):
        self.regular.role = User.Role.STUDENT
        self.regular.save()
        response = self.bind()
        self.assertIn("无需绑定", response.json()["message"])

    def test_teacher_cannot_bind(self):
        teacher = User.objects.create_user("t2", password="x", role=User.Role.TEACHER)
        self.assertIn("无需绑定", self.bind(user=teacher).json()["message"])

    def test_requires_login(self):
        response = APIClient().post(
            "/api/auth/bind-student", {"student_no": "20260001", "initial_password": "260001"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_exam_participation_conflict_keeps_one(self):
        now = timezone.now()
        exam = Exam.objects.create(
            title="公开赛", is_published=True, start_time=now - timedelta(hours=1), end_time=now + timedelta(hours=1)
        )
        ExamProblem.objects.create(exam=exam, problem=self.problem, score=100)
        ExamParticipant.objects.create(exam=exam, student=self.regular)
        ExamParticipant.objects.create(exam=exam, student=self.placeholder)

        self.assertEqual(self.bind().status_code, 200)

        self.assertEqual(ExamParticipant.objects.filter(exam=exam, student=self.regular).count(), 1)

    def test_bind_does_not_touch_other_students(self):
        other = self.make_imported_student("20260002", "王五")
        self.bind()
        other.refresh_from_db()
        self.assertEqual(other.role, "student")
        self.assertTrue(User.objects.filter(username="20260002").exists())
