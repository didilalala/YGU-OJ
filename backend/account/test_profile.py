from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from account.models import StudentProfile, TeacherProfile, User
from classroom.models import ClassGroup, ClassMember
from problem.models import Problem
from submission.models import Submission


class ProfileTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user("20260001", password="x", role=User.Role.STUDENT)
        StudentProfile.objects.create(
            user=self.student, student_no="20260001", real_name="张三", college="计算机学院", major="软件工程", grade="2026"
        )
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        TeacherProfile.objects.create(user=self.teacher, staff_no="T0001", real_name="赵老师", college="计算机学院")
        self.regular = User.objects.create_user("coder", password="x", role=User.Role.REGULAR, email="c@example.edu")

        self.easy = self.problem("A+B", "easy", public=True)
        self.medium = self.problem("循环", "medium", public=True)
        self.hard = self.problem("私有难题", "hard", public=False, created_by=self.teacher)
        self.other_private = self.problem("别人的私有题", "easy", public=False, created_by=self.other())

    def other(self):
        return User.objects.create_user("t2", password="x", role=User.Role.TEACHER)

    def problem(self, title, difficulty, public, created_by=None):
        return Problem.objects.create(
            title=title, description="d", difficulty=difficulty, is_public=public, created_by=created_by, test_case_id="a" * 32
        )

    def submit(self, user, problem, result, days_ago=0, **fields):
        submission = Submission.objects.create(user=user, problem=problem, language="c", code="x", result=result, **fields)
        Submission.objects.filter(pk=submission.pk).update(created_at=timezone.now() - timedelta(days=days_ago, minutes=1))
        return submission

    def get(self, user):
        client = APIClient()
        client.force_authenticate(user)
        response = client.get("/api/profile")
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]

    def test_student_profile_fields(self):
        profile = self.get(self.student)["profile"]
        self.assertEqual(
            {k: profile[k] for k in ("student_no", "real_name", "college", "major", "grade", "role")},
            {"student_no": "20260001", "real_name": "张三", "college": "计算机学院", "major": "软件工程", "grade": "2026", "role": "student"},
        )
        self.assertEqual(profile["class_count"], 0)

    def test_teacher_and_regular_profiles(self):
        teacher = self.get(self.teacher)["profile"]
        self.assertEqual((teacher["staff_no"], teacher["real_name"]), ("T0001", "赵老师"))
        self.assertNotIn("student_no", teacher)

        regular = self.get(self.regular)["profile"]
        self.assertEqual((regular["email"], regular["real_name"]), ("c@example.edu", ""))
        self.assertNotIn("student_no", regular)

    def test_class_count_counts_active_memberships_only(self):
        klass = ClassGroup.objects.create(name="班", teacher=self.teacher)
        ClassMember.objects.create(class_group=klass, student=self.student)
        removed = ClassGroup.objects.create(name="旧班", teacher=self.teacher)
        ClassMember.objects.create(class_group=removed, student=self.student, is_removed=True)
        self.assertEqual(self.get(self.student)["profile"]["class_count"], 1)

    def test_counts_solved_and_attempted(self):
        self.submit(self.regular, self.easy, "WA")
        self.submit(self.regular, self.easy, "AC")
        self.submit(self.regular, self.easy, "AC")  # 同一题多次通过只算一题
        self.submit(self.regular, self.medium, "TLE")
        stats = self.get(self.regular)["stats"]

        self.assertEqual((stats["submitted"], stats["accepted"]), (4, 2))
        self.assertEqual(stats["accept_rate"], 50.0)
        self.assertEqual((stats["attempted_problems"], stats["solved_problems"]), (2, 1))

    def test_distribution_excludes_pending_judging_and_system_errors(self):
        self.submit(self.regular, self.easy, "AC")
        self.submit(self.regular, self.easy, "CE")
        self.submit(self.regular, self.easy, "PENDING")
        self.submit(self.regular, self.easy, "SE")
        distribution = {row["result"]: row["count"] for row in self.get(self.regular)["stats"]["distribution"]}

        self.assertEqual(distribution["AC"], 1)
        self.assertEqual(distribution["CE"], 1)
        self.assertNotIn("PENDING", distribution)
        self.assertNotIn("SE", distribution)
        self.assertEqual(self.get(self.regular)["stats"]["submitted"], 2)

    def test_difficulty_totals_follow_visibility(self):
        self.submit(self.regular, self.easy, "AC")
        levels = {row["difficulty"]: row for row in self.get(self.regular)["stats"]["by_difficulty"]}
        self.assertEqual((levels["easy"]["total"], levels["easy"]["solved"]), (1, 1))
        self.assertEqual(levels["hard"]["total"], 0)
        self.assertEqual(levels["easy"]["percent"], 100.0)

        # 教师可以看到自己的私有题，但看不到别人的
        teacher_levels = {row["difficulty"]: row for row in self.get(self.teacher)["stats"]["by_difficulty"]}
        self.assertEqual(teacher_levels["hard"]["total"], 1)
        self.assertEqual(teacher_levels["easy"]["total"], 1)  # 别人的私有题不计入

    def test_visible_problem_count(self):
        self.assertEqual(self.get(self.regular)["stats"]["visible_problems"], 2)
        self.assertEqual(self.get(self.teacher)["stats"]["visible_problems"], 3)

    def test_activity_buckets_each_day(self):
        self.submit(self.regular, self.easy, "AC")
        self.submit(self.regular, self.easy, "WA")
        self.submit(self.regular, self.medium, "AC", days_ago=3)
        activity = self.get(self.regular)["stats"]["activity"]

        self.assertEqual(len(activity), 30)
        self.assertEqual(activity[-1]["count"], 2)
        self.assertEqual(activity[-4]["count"], 1)
        self.assertEqual(sum(day["count"] for day in activity), 3)
        # 超过 30 天的提交不计入
        self.submit(self.regular, self.easy, "AC", days_ago=40)
        self.assertEqual(sum(day["count"] for day in self.get(self.regular)["stats"]["activity"]), 3)

    def test_recent_submissions_newest_first(self):
        first = self.submit(self.regular, self.easy, "WA")
        second = self.submit(self.regular, self.medium, "AC")
        recent = self.get(self.regular)["stats"]["recent"]

        self.assertEqual([r["id"] for r in recent], [second.id, first.id])
        self.assertEqual(recent[0]["problem_title"], "循环")

    def test_empty_account(self):
        stats = self.get(self.regular)["stats"]
        self.assertEqual((stats["submitted"], stats["accept_rate"], stats["recent"]), (0, 0.0, []))

    def test_requires_login(self):
        self.assertEqual(APIClient().get("/api/profile").status_code, 401)
