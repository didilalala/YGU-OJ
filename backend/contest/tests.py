from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from account.models import StudentProfile, User
from classroom.models import Assignment, ClassGroup, ClassMember, ScoreRecord
from problem.models import Problem
from submission.models import Submission

from .models import Exam, ExamParticipant, ExamProblem
from .scoring import WRONG_SUBMISSION_PENALTY, exam_rank, recalculate_exam, recalculate_exam_score

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def cases(passed, total=4):
    return [{"case": i + 1, "result": "AC" if i < passed else "WA"} for i in range(total)]


@override_settings(CACHES=LOCMEM_CACHE)
class ExamTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.now = timezone.now()
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        self.other_teacher = User.objects.create_user("t2", password="x", role=User.Role.TEACHER)
        self.klass = ClassGroup.objects.create(name="软件 2601", teacher=self.teacher)
        self.alice = self.make_student("20260001", "张三")
        self.bob = self.make_student("20260002", "李四")
        self.carol = self.make_student("20260003", "王五")
        self.outsider = self.make_student("20269999", "外班")
        for student in (self.alice, self.bob, self.carol):
            ClassMember.objects.create(class_group=self.klass, student=student)

        self.p1 = Problem.objects.create(title="A+B", description="d", is_public=True, test_case_id="a" * 32)
        self.p2 = Problem.objects.create(
            title="考试私有题", description="d", is_public=False, created_by=self.teacher, test_case_id="b" * 32
        )
        self.exam = self.make_exam()

    def make_student(self, student_no, name):
        user = User.objects.create_user(student_no, password="x", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=user, student_no=student_no, real_name=name)
        return user

    def make_exam(self, start=-1, end=1, rule_type="OI", scores=(60, 40), **fields):
        exam = Exam.objects.create(
            class_group=fields.pop("class_group", self.klass),
            title=fields.pop("title", "期中考试"),
            rule_type=rule_type,
            start_time=self.now + timedelta(hours=start),
            end_time=self.now + timedelta(hours=end),
            is_published=fields.pop("is_published", True),
            created_by=self.teacher,
            **fields,
        )
        for order, (problem, score) in enumerate(zip((self.p1, self.p2), scores)):
            ExamProblem.objects.create(exam=exam, problem=problem, score=score, order=order)
        return exam

    def submission(self, student, problem, result="AC", passed=4, minutes=10, exam=None):
        exam = exam or self.exam
        submission = Submission.objects.create(
            user=student,
            problem=problem,
            language="c",
            code="x",
            result=result,
            case_info=[] if result in ("CE", "SE") else cases(passed),
            exam=exam,
        )
        Submission.objects.filter(pk=submission.pk).update(created_at=exam.start_time + timedelta(minutes=minutes))
        return submission

    def join(self, student, exam=None):
        return ExamParticipant.objects.create(exam=exam or self.exam, student=student, join_ip="127.0.0.1")

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client


class ScoringTests(ExamTestBase):
    def test_oi_best_partial_score(self):
        self.submission(self.alice, self.p1, "PAC", passed=1)
        self.submission(self.alice, self.p1, "PAC", passed=3)
        self.submission(self.alice, self.p2, "AC")
        recalculate_exam_score(self.exam, self.alice.id)
        record = ScoreRecord.objects.get(exam=self.exam, student=self.alice)

        self.assertEqual((record.score, record.solved_count), (45 + 40, 1))
        self.assertEqual(record.details[str(self.p1.id)]["attempts"], 2)

    def test_acm_full_score_only_and_penalty(self):
        exam = self.make_exam(rule_type="ACM", title="ACM")
        self.submission(self.alice, self.p1, "WA", passed=3, minutes=5, exam=exam)
        self.submission(self.alice, self.p1, "CE", minutes=6, exam=exam)  # 编译错误不计罚时
        self.submission(self.alice, self.p1, "AC", minutes=12, exam=exam)
        self.submission(self.alice, self.p1, "WA", minutes=20, exam=exam)  # 通过后的错误不计
        self.submission(self.alice, self.p2, "PAC", passed=3, minutes=30, exam=exam)
        recalculate_exam_score(exam, self.alice.id)
        record = ScoreRecord.objects.get(exam=exam, student=self.alice)

        self.assertEqual((record.score, record.solved_count), (60, 1))
        self.assertEqual(record.penalty, 12 * 60 + WRONG_SUBMISSION_PENALTY)
        self.assertEqual(record.details[str(self.p1.id)], {"score": 60, "accepted": True, "attempts": 1, "ac_time": 720})
        self.assertEqual(record.details[str(self.p2.id)]["score"], 0)

    def test_acm_rank_by_solved_then_penalty(self):
        exam = self.make_exam(rule_type="ACM", title="ACM")
        self.submission(self.alice, self.p1, "AC", minutes=50, exam=exam)
        self.submission(self.bob, self.p1, "AC", minutes=10, exam=exam)
        self.submission(self.carol, self.p1, "AC", minutes=60, exam=exam)
        self.submission(self.carol, self.p2, "AC", minutes=70, exam=exam)
        for student in (self.alice, self.bob, self.carol):
            recalculate_exam_score(exam, student.id)

        rank = exam_rank(exam)
        self.assertEqual([(r["real_name"], r["rank"]) for r in rank], [("王五", 1), ("李四", 2), ("张三", 3)])

    def test_oi_rank_ties_share_rank_and_participants_without_score_listed(self):
        self.submission(self.alice, self.p1, "AC")
        self.submission(self.bob, self.p1, "AC")
        self.join(self.carol)
        for student in (self.alice, self.bob):
            recalculate_exam_score(self.exam, student.id)

        rank = exam_rank(self.exam)
        self.assertEqual([(r["real_name"], r["score"], r["rank"]) for r in rank], [("张三", 60, 1), ("李四", 60, 1), ("王五", 0, 3)])

    def test_rank_cache_invalidated_after_new_score(self):
        self.submission(self.alice, self.p1, "PAC", passed=2)
        with self.captureOnCommitCallbacks(execute=True):
            recalculate_exam_score(self.exam, self.alice.id)
        self.assertEqual(exam_rank(self.exam)[0]["score"], 30)

        self.submission(self.alice, self.p1, "AC")
        with self.captureOnCommitCallbacks(execute=True):
            recalculate_exam_score(self.exam, self.alice.id)
        self.assertEqual(exam_rank(self.exam)[0]["score"], 60)

    def test_recalculate_after_switching_rule(self):
        self.submission(self.alice, self.p1, "PAC", passed=2)
        recalculate_exam_score(self.exam, self.alice.id)
        self.exam.rule_type = "ACM"
        self.exam.save()
        recalculate_exam(self.exam)
        self.assertEqual(ScoreRecord.objects.get(exam=self.exam).score, 0)

    def test_oi_exam_submission_uses_partial_result(self):
        self.assertTrue(Submission(exam=self.exam).uses_partial_score)
        acm = self.make_exam(rule_type="ACM", title="ACM")
        self.assertFalse(Submission(exam=acm).uses_partial_score)


class AdminExamApiTests(ExamTestBase):
    def payload(self, **overrides):
        payload = {
            "class_group": self.klass.id,
            "title": "期末上机考试",
            "rule_type": "ACM",
            "start_time": (self.now + timedelta(days=1)).isoformat(),
            "end_time": (self.now + timedelta(days=1, hours=2)).isoformat(),
            "allowed_ip_ranges": ["10.1.0.0/16", "202.1.2.3", " "],
            "password": "secret",
            "is_published": True,
            "problems": [{"problem_id": self.p2.id, "score": 50}, {"problem_id": self.p1.id, "score": 50}],
        }
        payload.update(overrides)
        return payload

    def test_create(self):
        response = self.client_for(self.teacher).post("/api/admin/exams", self.payload(), format="json")

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["allowed_ip_ranges"], ["10.1.0.0/16", "202.1.2.3/32"])
        self.assertEqual((data["total_score"], data["status"], data["member_count"]), (100, "not_started", 3))
        self.assertTrue(data["lock_problem_bank"])

    def test_validation(self):
        other_class = ClassGroup.objects.create(name="别人的班", teacher=self.other_teacher)
        cases_ = [
            ({"class_group": other_class.id}, "班级不存在"),
            ({"allowed_ip_ranges": ["10.1.0.0/33"]}, "无效的 IP"),
            ({"end_time": self.now.isoformat()}, "结束时间应晚于开始时间"),
            ({"problems": []}, "请至少选择一道题目"),
            ({"rule_type": "IOI"}, "rule_type"),
        ]
        client = self.client_for(self.teacher)
        for overrides, message in cases_:
            with self.subTest(overrides=list(overrides)):
                response = client.post("/api/admin/exams", self.payload(**overrides), format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, response.json()["message"])

    def test_scoped_to_teacher(self):
        self.assertEqual(self.client_for(self.other_teacher).get(f"/api/admin/exams/{self.exam.id}").status_code, 404)
        self.assertEqual(self.client_for(self.other_teacher).get("/api/admin/exams").json()["data"]["total"], 0)

    def test_delete(self):
        self.submission(self.alice, self.p1)
        response = self.client_for(self.teacher).delete(f"/api/admin/exams/{self.exam.id}")
        self.assertEqual(response.status_code, 400)
        empty = self.make_exam(title="空考试")
        self.assertEqual(self.client_for(self.teacher).delete(f"/api/admin/exams/{empty.id}").status_code, 204)

    def test_class_with_exam_cannot_be_deleted(self):
        response = self.client_for(self.teacher).delete(f"/api/admin/classes/{self.klass.id}")
        self.assertEqual(response.json()["message"], "该班级已布置作业或考试，不能删除")

    def test_monitor(self):
        self.join(self.alice)
        self.join(self.bob).__class__.objects.filter(student=self.bob).update(finished_at=self.now)
        self.submission(self.alice, self.p1, "AC")
        recalculate_exam_score(self.exam, self.alice.id)

        data = self.client_for(self.teacher).get(f"/api/admin/exams/{self.exam.id}/monitor").json()["data"]
        states = {s["real_name"]: (s["state"], s["submission_count"], s["score"]) for s in data["students"]}
        self.assertEqual(states, {"张三": ("in_exam", 1, 60), "李四": ("finished", 0, 0), "王五": ("absent", 0, 0)})
        self.assertEqual(data["summary"], {"member_count": 3, "in_exam": 1, "finished": 1, "absent": 1})
        self.assertEqual(data["rank"][0]["real_name"], "张三")

    def test_reopen(self):
        ExamParticipant.objects.create(exam=self.exam, student=self.alice, finished_at=self.now)
        url = f"/api/admin/exams/{self.exam.id}/participants/{self.alice.id}/reopen"
        self.assertEqual(self.client_for(self.teacher).post(url).status_code, 200)
        self.assertIsNone(ExamParticipant.objects.get().finished_at)
        self.assertEqual(self.client_for(self.teacher).post(url).status_code, 400)

    def test_update_recalculates(self):
        self.submission(self.alice, self.p1, "PAC", passed=2)
        recalculate_exam_score(self.exam, self.alice.id)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.teacher).patch(
                f"/api/admin/exams/{self.exam.id}", {"problems": [{"problem_id": self.p1.id, "score": 10}]}, format="json"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ScoreRecord.objects.get(exam=self.exam).score, 5)


class StudentExamApiTests(ExamTestBase):
    def submit(self, user, problem=None, exam=None, **extra):
        cache.delete(f"submit-interval:{user.id}")
        payload = {"problem_id": (problem or self.p1).id, "language": "c", "code": "int main(){}", **extra}
        if exam is not False:
            payload["exam_id"] = (exam or self.exam).id
        with mock.patch("judge.tasks.judge_submission.delay"):
            return self.client_for(user).post("/api/submissions", payload, format="json")

    def test_list_and_detail(self):
        upcoming = self.make_exam(start=2, end=3, title="下周考试", password="abc")
        self.make_exam(title="未发布", is_published=False)
        data = self.client_for(self.alice).get("/api/exams").json()["data"]
        self.assertEqual([e["title"] for e in data], ["期中考试", "下周考试"])
        self.assertEqual((data[1]["status"], data[1]["need_password"]), ("not_started", True))
        self.assertNotIn("password", data[1])

        detail = self.client_for(self.alice).get(f"/api/exams/{self.exam.id}").json()["data"]
        self.assertEqual((detail["joined"], detail["problems"], detail["ip"]), (False, [], "127.0.0.1"))
        self.assertIn("server_time", detail)
        self.assertEqual(self.client_for(self.outsider).get(f"/api/exams/{upcoming.id}").status_code, 404)

    def test_join_rules(self):
        locked = self.make_exam(title="有口令", password="abc123")
        not_started = self.make_exam(start=1, end=2, title="未开始")
        ip_limited = self.make_exam(title="限机房", allowed_ip_ranges=["10.1.0.0/16"])
        client = self.client_for(self.alice)

        self.assertIn("考试尚未开始", client.post(f"/api/exams/{not_started.id}/join").json()["message"])
        response = client.post(f"/api/exams/{ip_limited.id}/join")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 40302)
        self.assertIn("127.0.0.1", response.json()["message"])
        self.assertIn("口令不正确", client.post(f"/api/exams/{locked.id}/join", {"password": "x"}, format="json").json()["message"])
        self.assertEqual(client.post(f"/api/exams/{locked.id}/join", {"password": "abc123"}, format="json").status_code, 200)
        # 重复进入无需再输口令
        self.assertEqual(client.post(f"/api/exams/{locked.id}/join").status_code, 200)
        self.assertEqual(ExamParticipant.objects.filter(exam=locked).count(), 1)
        self.assertEqual(self.client_for(self.outsider).post(f"/api/exams/{self.exam.id}/join").status_code, 404)

    @override_settings(TRUST_X_REAL_IP=True)
    def test_ip_range_uses_real_client_ip(self):
        exam = self.make_exam(title="限机房", allowed_ip_ranges=["10.1.0.0/16"])
        response = self.client_for(self.alice).post(f"/api/exams/{exam.id}/join", HTTP_X_REAL_IP="10.1.2.3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ExamParticipant.objects.get(exam=exam).join_ip, "10.1.2.3")

    def test_problems_visible_after_join(self):
        client = self.client_for(self.alice)
        url = f"/api/problems/{self.p2.id}?exam_id={self.exam.id}"
        self.assertIn("请先进入考试", client.get(url).json()["message"])
        client.post(f"/api/exams/{self.exam.id}/join")

        self.assertEqual(client.get(url).json()["data"]["title"], "考试私有题")
        detail = client.get(f"/api/exams/{self.exam.id}").json()["data"]
        self.assertEqual([p["title"] for p in detail["problems"]], ["A+B", "考试私有题"])
        self.assertIsNone(detail["problems"][0]["my_score"])  # 公布成绩前不显示得分

    def test_submit_in_exam(self):
        self.assertIn("请先进入考试", self.submit(self.alice).json()["message"])
        self.join(self.alice)
        response = self.submit(self.alice, self.p2)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Submission.objects.get().exam, self.exam)

    def test_cannot_submit_after_finish_or_end(self):
        self.join(self.alice)
        client = self.client_for(self.alice)
        self.assertEqual(client.post(f"/api/exams/{self.exam.id}/finish").status_code, 200)
        self.assertIn("你已交卷", self.submit(self.alice).json()["message"])
        self.assertIn("已经交卷", client.post(f"/api/exams/{self.exam.id}/finish").json()["message"])

        ended = self.make_exam(start=-3, end=-2, title="已结束")
        self.join(self.alice, ended)
        self.assertIn("考试已结束", self.submit(self.alice, exam=ended).json()["message"])

    def test_problem_bank_locked_during_exam(self):
        client = self.client_for(self.alice)
        practice = Submission.objects.create(user=self.alice, problem=self.p1, language="c", code="old", result="AC")
        assignment = Assignment.objects.create(class_group=self.klass, title="作业", start_time=self.now, end_time=self.now + timedelta(days=1), is_published=True)

        for url in ("/api/problems", f"/api/problems/{self.p1.id}", "/api/assignments", f"/api/assignments/{assignment.id}",
                    f"/api/problems/{self.p1.id}?assignment_id={assignment.id}", f"/api/submissions/{practice.id}"):
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(response.status_code, 403)
                body = response.json()
                self.assertEqual(body["code"], 40301)
                self.assertEqual(body["data"]["exam_id"], self.exam.id)

        response = self.submit(self.alice, exam=False)
        self.assertEqual(response.json()["code"], 40301)
        # 提交记录列表只显示本场考试的提交
        self.join(self.alice)
        self.submit(self.alice)
        ids = [s["id"] for s in client.get("/api/submissions").json()["data"]["results"]]
        self.assertEqual(ids, [Submission.objects.get(exam=self.exam).id])
        self.assertEqual(client.get("/api/exams/active").json()["data"]["id"], self.exam.id)

    def test_lock_does_not_affect_others(self):
        self.make_exam(title="另一个", lock_problem_bank=False)
        self.assertEqual(self.client_for(self.outsider).get("/api/problems").status_code, 200)
        self.assertEqual(self.client_for(self.teacher).get("/api/problems").status_code, 200)
        self.assertIsNone(self.client_for(self.outsider).get("/api/exams/active").json()["data"])

        self.exam.lock_problem_bank = False
        self.exam.save()
        self.assertEqual(self.client_for(self.alice).get("/api/problems").status_code, 200)

    def test_lock_ends_with_exam(self):
        self.exam.start_time = self.now - timedelta(hours=3)
        self.exam.end_time = self.now - timedelta(hours=2)
        self.exam.save()
        self.assertEqual(self.client_for(self.alice).get("/api/problems").status_code, 200)

    def test_rank_visibility(self):
        client = self.client_for(self.alice)
        self.assertIn("排名暂不公开", client.get(f"/api/exams/{self.exam.id}/rank").json()["message"])
        self.exam.show_rank = True
        self.exam.save()
        self.assertEqual(client.get(f"/api/exams/{self.exam.id}/rank").status_code, 200)

    def test_scores_after_publish(self):
        self.join(self.alice)
        self.submission(self.alice, self.p1, "AC")
        recalculate_exam_score(self.exam, self.alice.id)
        self.exam.start_time = self.now - timedelta(hours=3)
        self.exam.end_time = self.now - timedelta(hours=2)
        self.exam.save()
        client = self.client_for(self.alice)

        detail = client.get(f"/api/exams/{self.exam.id}").json()["data"]
        self.assertEqual((detail["my_score"], detail["problems"]), (None, []))
        self.assertIn("公布成绩后可查看题目", client.get(f"/api/problems/{self.p2.id}?exam_id={self.exam.id}").json()["message"])

        self.exam.is_score_published = True
        self.exam.save()
        detail = client.get(f"/api/exams/{self.exam.id}").json()["data"]
        self.assertEqual(detail["my_score"], 60)
        self.assertEqual([p["my_score"] for p in detail["problems"]], [60, 0])
        self.assertEqual(client.get(f"/api/problems/{self.p2.id}?exam_id={self.exam.id}").status_code, 200)
        self.assertEqual(client.get(f"/api/exams/{self.exam.id}/rank").json()["data"]["rank"][0]["score"], 60)
