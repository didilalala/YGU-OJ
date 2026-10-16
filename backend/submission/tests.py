from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from account.models import User
from problem.models import Problem

from .models import Submission

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CPP = "#include <cstdio>\nint main(){int a,b;scanf(\"%d%d\",&a,&b);printf(\"%d\\n\",a+b);}"


@override_settings(CACHES=LOCMEM_CACHE)
class SubmissionApiTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.student = User.objects.create_user("20260001", password="x", role=User.Role.STUDENT)
        self.other = User.objects.create_user("20260002", password="x", role=User.Role.STUDENT)
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        self.problem = Problem.objects.create(title="A+B", description="", is_public=True, test_case_id="a" * 32)

        patcher = mock.patch("judge.tasks.judge_submission.delay")
        self.delay = patcher.start()
        self.addCleanup(patcher.stop)

    def client_for(self, user):
        client = APIClient()
        if user:
            client.force_authenticate(user)
        return client

    def submit(self, user=None, **data):
        payload = {"problem_id": self.problem.id, "language": "cpp", "code": CPP, **data}
        with self.captureOnCommitCallbacks(execute=True):
            return self.client_for(user or self.student).post("/api/submissions", payload, format="json")

    def make_submission(self, user, **fields):
        fields = {"problem": self.problem, "language": "cpp", "code": CPP, **fields}
        return Submission.objects.create(user=user, **fields)


class SubmitTests(SubmissionApiTestBase):
    def test_submit_creates_pending_submission_and_enqueues(self):
        response = self.submit()

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["result"], "PENDING")
        submission = Submission.objects.get(pk=data["id"])
        self.assertEqual((submission.user, submission.problem, submission.code), (self.student, self.problem, CPP))
        self.assertEqual(submission.ip, "127.0.0.1")
        self.delay.assert_called_once_with(submission.id)

    def test_rate_limited_per_user(self):
        self.assertEqual(self.submit().status_code, 201)
        response = self.submit()

        self.assertEqual(response.status_code, 429)
        self.assertIn("提交过于频繁", response.json()["message"])
        self.assertEqual(Submission.objects.count(), 1)
        # 其他用户不受影响
        self.assertEqual(self.submit(user=self.other).status_code, 201)

    def test_invalid_submission_does_not_consume_rate_limit(self):
        self.assertEqual(self.submit(language="pascal").status_code, 400)
        self.assertEqual(self.submit().status_code, 201)

    def test_validation_errors(self):
        cases = [
            ({"language": "pascal"}, "language"),
            ({"code": "   \n"}, "代码不能为空"),
            ({"code": "x" * (64 * 1024 + 1)}, "code"),
            ({"problem_id": "abc"}, "problem_id"),
        ]
        for data, message in cases:
            with self.subTest(data=list(data)):
                response = self.submit(**data)
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, response.json()["message"])
        self.delay.assert_not_called()

    def test_private_problem_only_for_its_creator(self):
        self.problem.is_public = False
        self.problem.created_by = self.teacher
        self.problem.save()
        other_teacher = User.objects.create_user("t2", password="x", role=User.Role.TEACHER)

        response = self.submit()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "题目不存在")
        self.assertEqual(self.submit(problem_id=999999).json()["message"], "题目不存在")
        self.assertEqual(self.submit(user=other_teacher).status_code, 404)
        self.assertEqual(self.submit(user=self.teacher).status_code, 201)

    def test_problem_without_test_cases(self):
        self.problem.test_case_id = ""
        self.problem.save()
        response = self.submit()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "该题目暂无测试数据，无法提交")

    def test_template_problem_requires_supported_language(self):
        self.problem.is_template = True
        self.problem.template_code = {"c": {"prepend": "", "append": ""}}
        self.problem.save()

        self.assertEqual(self.submit(language="cpp").json()["message"], "该模板题不支持所选语言")
        self.assertEqual(self.submit(language="c").status_code, 201)

    def test_anonymous_cannot_submit(self):
        response = self.client_for(None).post("/api/submissions", {}, format="json")
        self.assertEqual(response.status_code, 401)

    @override_settings(TRUST_X_REAL_IP=True)
    def test_records_ip_from_nginx_header(self):
        client = self.client_for(self.student)
        payload = {"problem_id": self.problem.id, "language": "cpp", "code": CPP}
        client.post("/api/submissions", payload, format="json", HTTP_X_REAL_IP="10.1.2.3")
        self.assertEqual(Submission.objects.get().ip, "10.1.2.3")

    def test_ignores_x_real_ip_unless_trusted(self):
        client = self.client_for(self.student)
        payload = {"problem_id": self.problem.id, "language": "cpp", "code": CPP}
        client.post("/api/submissions", payload, format="json", HTTP_X_REAL_IP="10.1.2.3")
        self.assertEqual(Submission.objects.get().ip, "127.0.0.1")


class SubmissionQueryTests(SubmissionApiTestBase):
    def test_owner_sees_code_and_case_info(self):
        submission = self.make_submission(
            self.student, result="WA", case_info=[{"case": 1, "result": "WA"}], time_cost=3, memory_cost=1024
        )
        response = self.client_for(self.student).get(f"/api/submissions/{submission.id}")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["code"], CPP)
        self.assertEqual(data["result"], "WA")
        self.assertTrue(data["is_finished"])
        self.assertEqual(data["problem_title"], "A+B")
        self.assertEqual(data["case_info"], [{"case": 1, "result": "WA"}])

    def test_other_students_cannot_see_submission(self):
        submission = self.make_submission(self.other)
        response = self.client_for(self.student).get(f"/api/submissions/{submission.id}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client_for(self.teacher).get(f"/api/submissions/{submission.id}").status_code, 200)

    def test_error_info_visibility(self):
        ce = self.make_submission(self.student, result="CE", error_info="main.cpp:1: error")
        se = self.make_submission(self.student, result="SE", error_info="JudgeServerError: http://judge-server:8080")
        student = self.client_for(self.student)

        self.assertEqual(student.get(f"/api/submissions/{ce.id}").json()["data"]["error_info"], "main.cpp:1: error")
        self.assertEqual(student.get(f"/api/submissions/{se.id}").json()["data"]["error_info"], "")
        teacher_view = self.client_for(self.teacher).get(f"/api/submissions/{se.id}").json()["data"]
        self.assertIn("JudgeServerError", teacher_view["error_info"])

    def test_list_shows_only_own_submissions_for_students(self):
        mine = self.make_submission(self.student)
        self.make_submission(self.other)
        response = self.client_for(self.student).get("/api/submissions")

        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["results"][0]["id"], mine.id)
        self.assertNotIn("code", data["results"][0])
        # 学生传 user_id 也不能看别人的
        other_id = self.other.id
        self.assertEqual(self.client_for(self.student).get(f"/api/submissions?user_id={other_id}").json()["data"]["total"], 1)

    def test_teacher_lists_and_filters(self):
        other_problem = Problem.objects.create(title="B", description="", is_public=True, test_case_id="b" * 32)
        self.make_submission(self.student, result="AC")
        self.make_submission(self.student, result="WA", language="python")
        self.make_submission(self.other, problem=other_problem, result="AC")
        teacher = self.client_for(self.teacher)

        def total(query):
            return teacher.get(f"/api/submissions?{query}").json()["data"]["total"]

        self.assertEqual(total(""), 3)
        self.assertEqual(total(f"user_id={self.student.id}"), 2)
        self.assertEqual(total(f"problem_id={other_problem.id}"), 1)
        self.assertEqual(total("result=AC"), 2)
        self.assertEqual(total("language=python"), 1)
        self.assertEqual(teacher.get("/api/submissions?problem_id=x").status_code, 400)

    def test_list_is_newest_first_and_paginated(self):
        ids = [self.make_submission(self.student).id for _ in range(3)]
        data = self.client_for(self.student).get("/api/submissions?page_size=2").json()["data"]
        self.assertEqual(data["total"], 3)
        self.assertEqual([item["id"] for item in data["results"]], ids[::-1][:2])


class RejudgeTests(SubmissionApiTestBase):
    def rejudge(self, user, submission_id):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client_for(user).post(f"/api/admin/submissions/{submission_id}/rejudge")

    def test_teacher_rejudges_finished_submission(self):
        submission = self.make_submission(self.student, result="SE", error_info="boom")
        response = self.rejudge(self.teacher, submission.id)

        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual((submission.result, submission.error_info), ("PENDING", ""))
        self.delay.assert_called_once_with(submission.id)

    def test_cannot_rejudge_pending_submission(self):
        submission = self.make_submission(self.student)
        response = self.rejudge(self.teacher, submission.id)

        self.assertEqual(response.status_code, 400)
        self.delay.assert_not_called()

    def test_students_cannot_rejudge(self):
        submission = self.make_submission(self.student, result="SE")
        self.assertEqual(self.rejudge(self.student, submission.id).status_code, 403)

    def test_missing_submission(self):
        self.assertEqual(self.rejudge(self.teacher, 999999).status_code, 404)
