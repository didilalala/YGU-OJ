from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from account.models import StudentProfile, User
from classroom.models import ClassGroup, ClassMember
from problem.models import Problem
from submission.models import Submission

from .models import Exam, ExamParticipant, ExamProblem
from .scoring import recalculate_exam_score

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=LOCMEM_CACHE)
class PublicContestTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.now = timezone.now()
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        self.other_teacher = User.objects.create_user("t2", password="x", role=User.Role.TEACHER)
        self.admin = User.objects.create_user("admin1", password="x", role=User.Role.ADMIN)
        self.regular = User.objects.create_user("coder", password="x", role=User.Role.REGULAR)
        self.student = User.objects.create_user("20260001", password="x", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=self.student, student_no="20260001", real_name="张三")

        self.p1 = Problem.objects.create(title="A+B", description="d", is_public=True, test_case_id="a" * 32)
        self.p2 = Problem.objects.create(
            title="竞赛私有题", description="d", is_public=False, created_by=self.teacher, test_case_id="b" * 32
        )
        self.contest = self.make_contest()

    def make_contest(self, start=-1, end=1, **fields):
        contest = Exam.objects.create(
            class_group=fields.pop("class_group", None),
            title=fields.pop("title", "秋季新生赛"),
            rule_type=fields.pop("rule_type", "ACM"),
            start_time=self.now + timedelta(hours=start),
            end_time=self.now + timedelta(hours=end),
            is_published=fields.pop("is_published", True),
            show_rank=fields.pop("show_rank", True),
            lock_problem_bank=False,
            created_by=self.teacher,
            **fields,
        )
        for order, problem in enumerate((self.p1, self.p2)):
            ExamProblem.objects.create(exam=contest, problem=problem, score=100, order=order)
        return contest

    def client_for(self, user=None):
        client = APIClient()
        if user:
            client.force_authenticate(user)
        return client

    def submit(self, user, problem, contest=None):
        cache.delete(f"submit-interval:{user.id}")
        with mock.patch("judge.tasks.judge_submission.delay"):
            return self.client_for(user).post(
                "/api/submissions",
                {"problem_id": problem.id, "language": "c", "code": "int main(){}", "exam_id": (contest or self.contest).id},
                format="json",
            )


class AdminPublicContestTests(PublicContestTestBase):
    def payload(self, **overrides):
        payload = {
            "title": "程序设计校赛",
            "rule_type": "ACM",
            "start_time": (self.now + timedelta(days=1)).isoformat(),
            "end_time": (self.now + timedelta(days=1, hours=3)).isoformat(),
            "lock_problem_bank": True,
            "show_rank": True,
            "is_published": True,
            "problems": [{"problem_id": self.p1.id, "score": 100}],
        }
        payload.update(overrides)
        return payload

    def test_create_public_contest_without_class(self):
        response = self.client_for(self.teacher).post("/api/admin/exams", self.payload(), format="json")

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertIsNone(data["class_group"])
        self.assertIsNone(data["class_name"])
        self.assertFalse(data["lock_problem_bank"])  # 公开竞赛不锁定题库
        self.assertEqual(Exam.objects.get(pk=data["id"]).created_by, self.teacher)

    def test_teacher_manages_only_own_public_contests(self):
        own = self.client_for(self.teacher).get("/api/admin/exams?scope=public").json()["data"]
        self.assertEqual([e["title"] for e in own["results"]], ["秋季新生赛"])
        self.assertEqual(self.client_for(self.other_teacher).get("/api/admin/exams").json()["data"]["total"], 0)
        self.assertEqual(self.client_for(self.other_teacher).get(f"/api/admin/exams/{self.contest.id}").status_code, 404)
        self.assertEqual(self.client_for(self.admin).get(f"/api/admin/exams/{self.contest.id}").status_code, 200)

    def test_scope_public_excludes_class_exams(self):
        klass = ClassGroup.objects.create(name="班", teacher=self.teacher)
        self.make_contest(class_group=klass, title="课堂考试")
        titles = [e["title"] for e in self.client_for(self.teacher).get("/api/admin/exams?scope=public").json()["data"]["results"]]
        self.assertEqual(titles, ["秋季新生赛"])

    def test_monitor_lists_participants(self):
        ExamParticipant.objects.create(exam=self.contest, student=self.regular, join_ip="1.2.3.4")
        data = self.client_for(self.teacher).get(f"/api/admin/exams/{self.contest.id}/monitor").json()["data"]
        self.assertEqual([(s["student_no"], s["state"]) for s in data["students"]], [("coder", "in_exam")])
        self.assertEqual(data["summary"]["absent"], 0)

    def test_stats_for_public_contest(self):
        ExamParticipant.objects.create(exam=self.contest, student=self.regular)
        Submission.objects.create(user=self.regular, problem=self.p1, language="c", code="x", result="AC", exam=self.contest)
        recalculate_exam_score(self.contest, self.regular.id)
        data = self.client_for(self.teacher).get(f"/api/admin/stats/exams/{self.contest.id}").json()["data"]
        self.assertEqual(data["class_name"], "公开竞赛")
        self.assertEqual((data["summary"]["member_count"], data["summary"]["submitted_count"]), (1, 1))


class ParticipantTests(PublicContestTestBase):
    def test_visitors_browse_list_and_detail(self):
        self.make_contest(title="未发布", is_published=False)
        klass = ClassGroup.objects.create(name="班", teacher=self.teacher)
        class_exam = self.make_contest(class_group=klass, title="课堂考试")

        data = self.client_for().get("/api/contests").json()["data"]
        self.assertEqual([c["title"] for c in data], ["秋季新生赛"])
        self.assertTrue(data[0]["is_public"])
        self.assertEqual(data[0]["participant_count"], 0)

        detail = self.client_for().get(f"/api/exams/{self.contest.id}").json()["data"]
        self.assertEqual((detail["joined"], detail["problems"]), (False, []))
        self.assertEqual(self.client_for().get(f"/api/exams/{class_exam.id}").status_code, 404)
        self.assertEqual(self.client_for().post(f"/api/exams/{self.contest.id}/join").status_code, 401)

    def test_regular_user_joins_with_password_and_submits(self):
        locked = self.make_contest(title="有口令", password="go2026")
        client = self.client_for(self.regular)
        self.assertIn("口令不正确", client.post(f"/api/exams/{locked.id}/join", {"password": "x"}, format="json").json()["message"])
        self.assertEqual(client.post(f"/api/exams/{locked.id}/join", {"password": "go2026"}, format="json").status_code, 200)

        # 私有题通过竞赛可见
        response = client.get(f"/api/problems/{self.p2.id}?exam_id={locked.id}")
        self.assertEqual(response.json()["data"]["title"], "竞赛私有题")
        self.assertEqual(self.submit(self.regular, self.p2, locked).status_code, 201)
        self.assertEqual(Submission.objects.get().exam, locked)

        contests = {c["title"]: c for c in client.get("/api/contests").json()["data"]}
        self.assertTrue(contests["有口令"]["joined"])
        self.assertTrue(contests["有口令"]["need_password"])

    def test_must_join_before_submitting(self):
        self.assertIn("请先进入考试", self.submit(self.regular, self.p1).json()["message"])

    def test_public_contest_does_not_lock_problem_bank(self):
        ExamParticipant.objects.create(exam=self.contest, student=self.student)
        client = self.client_for(self.student)
        self.assertEqual(client.get("/api/problems").status_code, 200)
        self.assertIsNone(client.get("/api/exams/active").json()["data"])

    def test_not_in_my_class_exams(self):
        self.assertEqual(self.client_for(self.student).get("/api/exams").json()["data"], [])


class PublicRankTests(PublicContestTestBase):
    def setUp(self):
        super().setUp()
        for user in (self.student, self.regular):
            ExamParticipant.objects.create(exam=self.contest, student=user)
        Submission.objects.create(user=self.student, problem=self.p1, language="c", code="x", result="AC", exam=self.contest)
        recalculate_exam_score(self.contest, self.student.id)

    def test_visitors_see_masked_rank(self):
        data = self.client_for().get(f"/api/exams/{self.contest.id}/rank").json()["data"]
        self.assertTrue(data["is_public"])
        self.assertEqual([(r["student_no"], r["real_name"]) for r in data["rank"]], [("2026**01", ""), ("coder", "")])

    def test_teacher_monitor_sees_full_names(self):
        data = self.client_for(self.teacher).get(f"/api/admin/exams/{self.contest.id}/monitor").json()["data"]
        self.assertEqual(data["rank"][0]["real_name"], "张三")
        self.assertEqual(data["rank"][0]["student_no"], "20260001")

    def test_rank_hidden_when_disabled(self):
        self.contest.show_rank = False
        self.contest.save()
        self.assertIn("排名暂不公开", self.client_for().get(f"/api/exams/{self.contest.id}/rank").json()["message"])
