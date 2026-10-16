from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from account.models import StudentProfile, User
from problem.models import Problem
from submission.models import Submission

from .models import Assignment, AssignmentProblem, ClassGroup, ClassMember, ScoreRecord
from .scoring import recalculate_assignment, recalculate_score

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def cases(passed, total=4):
    return [{"case": i + 1, "result": "AC" if i < passed else "WA"} for i in range(total)]


class AssignmentTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.now = timezone.now()
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        self.other_teacher = User.objects.create_user("t2", password="x", role=User.Role.TEACHER)
        self.klass = ClassGroup.objects.create(name="软件 2601", teacher=self.teacher)
        self.student = self.make_student("20260001", "张三")
        self.classmate = self.make_student("20260002", "李四")
        self.outsider = self.make_student("20269999", "外班")
        for student in (self.student, self.classmate):
            ClassMember.objects.create(class_group=self.klass, student=student)

        self.p1 = Problem.objects.create(title="A+B", description="d", is_public=True, test_case_id="a" * 32)
        self.p2 = Problem.objects.create(
            title="私有题", description="d", is_public=False, created_by=self.teacher, test_case_id="b" * 32
        )
        self.assignment = self.make_assignment()

    def make_student(self, student_no, name):
        user = User.objects.create_user(student_no, password="x", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=user, student_no=student_no, real_name=name)
        return user

    def make_assignment(self, start=-1, end=1, scores=(60, 40), **fields):
        assignment = Assignment.objects.create(
            class_group=fields.pop("class_group", self.klass),
            title=fields.pop("title", "第一次作业"),
            start_time=self.now + timedelta(hours=start),
            end_time=self.now + timedelta(hours=end),
            is_published=fields.pop("is_published", True),
            **fields,
        )
        for order, (problem, score) in enumerate(zip((self.p1, self.p2), scores)):
            AssignmentProblem.objects.create(assignment=assignment, problem=problem, score=score, order=order)
        return assignment

    def submission(self, problem, result="AC", passed=4, late=False, student=None, assignment=None):
        assignment = assignment or self.assignment
        submission = Submission.objects.create(
            user=student or self.student,
            problem=problem,
            language="c",
            code="x",
            result=result,
            case_info=[] if result in ("CE", "SE") else cases(passed),
            assignment=assignment,
        )
        moment = assignment.end_time + (timedelta(minutes=5) if late else -timedelta(minutes=5))
        Submission.objects.filter(pk=submission.pk).update(created_at=moment)
        return submission

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client


class ScoringTests(AssignmentTestBase):
    def score(self, assignment=None, student=None):
        return recalculate_score(assignment or self.assignment, (student or self.student).id)

    def test_best_score_per_problem(self):
        self.submission(self.p1, "PAC", passed=1)
        self.submission(self.p1, "PAC", passed=3)
        self.submission(self.p1, "WA", passed=0)
        self.submission(self.p2, "AC")
        record = self.score()

        self.assertEqual(record.score, 60 * 0.75 + 40)
        self.assertEqual(record.solved_count, 1)
        self.assertEqual(record.details[str(self.p1.id)], {"score": 45, "late": False, "accepted": False})
        self.assertFalse(record.is_late)

    def test_late_penalty(self):
        self.assignment.allow_late = True
        self.assignment.late_penalty = 0.3
        self.assignment.save()
        self.submission(self.p1, "AC", late=True)
        record = self.score()

        self.assertEqual(record.score, 42)
        self.assertTrue(record.is_late)
        self.assertEqual(record.solved_count, 1)

    def test_on_time_partial_beats_late_full_and_accepted_is_kept(self):
        self.assignment.late_penalty = 0.5
        self.assignment.save()
        self.submission(self.p1, "AC", late=True)  # 30 分
        self.submission(self.p1, "PAC", passed=3)  # 45 分
        record = self.score()

        self.assertEqual(record.details[str(self.p1.id)], {"score": 45, "late": False, "accepted": True})
        self.assertFalse(record.is_late)
        self.assertEqual(record.solved_count, 1)

    def test_equal_score_prefers_on_time(self):
        self.submission(self.p1, "AC", late=True)  # 无扣分时迟交也是 60
        self.submission(self.p1, "AC")
        self.assertFalse(self.score().details[str(self.p1.id)]["late"])

    def test_ce_counts_as_submitted_zero_and_se_is_ignored(self):
        self.submission(self.p1, "CE")
        self.submission(self.p2, "SE")
        record = self.score()
        self.assertEqual((record.score, list(record.details)), (0, [str(self.p1.id)]))

    def test_no_scored_submission_means_no_record(self):
        self.submission(self.p1, "SE")
        self.assertIsNone(self.score())
        self.assertFalse(ScoreRecord.objects.exists())

    def test_recalculate_after_changing_scores_and_problems(self):
        self.submission(self.p1, "AC")
        self.submission(self.p2, "AC")
        self.score()
        self.assignment.items.filter(problem=self.p1).update(score=100)
        self.assignment.items.filter(problem=self.p2).delete()
        recalculate_assignment(self.assignment)

        record = ScoreRecord.objects.get()
        self.assertEqual((record.score, record.solved_count), (100, 1))

    def test_practice_submissions_do_not_count(self):
        Submission.objects.create(user=self.student, problem=self.p1, language="c", code="x", result="AC")
        self.assertIsNone(self.score())


class AdminAssignmentApiTests(AssignmentTestBase):
    def payload(self, **overrides):
        payload = {
            "class_group": self.klass.id,
            "title": "第二次作业",
            "description": "完成循环练习",
            "start_time": (self.now + timedelta(days=1)).isoformat(),
            "end_time": (self.now + timedelta(days=8)).isoformat(),
            "allow_late": True,
            "late_penalty": 0.2,
            "is_published": False,
            "problems": [{"problem_id": self.p2.id, "score": 30}, {"problem_id": self.p1.id, "score": 70}],
        }
        payload.update(overrides)
        return payload

    def test_create(self):
        response = self.client_for(self.teacher).post("/api/admin/assignments", self.payload(), format="json")

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual([(i["problem_id"], i["score"]) for i in data["items"]], [(self.p2.id, 30), (self.p1.id, 70)])
        self.assertEqual((data["total_score"], data["status"], data["member_count"]), (100, "not_started", 2))
        self.assertEqual(data["class_name"], "软件 2601")

    def test_validation(self):
        other_class = ClassGroup.objects.create(name="别人的班", teacher=self.other_teacher)
        others_private = Problem.objects.create(title="别人的私有题", description="d", created_by=self.other_teacher)
        cases_ = [
            ({"class_group": other_class.id}, "班级不存在"),
            ({"end_time": self.now.isoformat()}, "截止时间应晚于开始时间"),
            ({"late_penalty": 1.5}, "0–100%"),
            ({"problems": []}, "请至少选择一道题目"),
            ({"problems": [{"problem_id": self.p1.id, "score": 10}] * 2}, "题目重复"),
            ({"problems": [{"problem_id": others_private.id, "score": 10}]}, "无权使用"),
            ({"problems": [{"problem_id": self.p1.id, "score": 0}]}, "problems"),
        ]
        client = self.client_for(self.teacher)
        for overrides, message in cases_:
            with self.subTest(overrides=list(overrides)):
                response = client.post("/api/admin/assignments", self.payload(**overrides), format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, response.json()["message"])

    def test_update_replaces_problems_and_recalculates(self):
        self.submission(self.p1, "AC")
        recalculate_score(self.assignment, self.student.id)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.teacher).patch(
                f"/api/admin/assignments/{self.assignment.id}",
                {"problems": [{"problem_id": self.p1.id, "score": 10}], "class_group": 999},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual([i["score"] for i in data["items"]], [10])
        self.assertEqual(data["class_group"], self.klass.id)  # 班级不可修改
        self.assertEqual(ScoreRecord.objects.get().score, 10)

    def test_list_scoped_to_teacher_and_filtered_by_class(self):
        other_class = ClassGroup.objects.create(name="别人的班", teacher=self.other_teacher)
        self.make_assignment(class_group=other_class, title="别人的作业")
        second_class = ClassGroup.objects.create(name="软件 2602", teacher=self.teacher)
        self.make_assignment(class_group=second_class, title="2602 作业")
        client = self.client_for(self.teacher)

        titles = [a["title"] for a in client.get("/api/admin/assignments").json()["data"]["results"]]
        self.assertEqual(sorted(titles), ["2602 作业", "第一次作业"])
        data = client.get(f"/api/admin/assignments?class_id={self.klass.id}").json()["data"]
        self.assertEqual([a["title"] for a in data["results"]], ["第一次作业"])
        self.assertEqual(data["results"][0]["member_count"], 2)
        self.assertEqual(self.client_for(self.other_teacher).get(f"/api/admin/assignments/{self.assignment.id}").status_code, 404)

    def test_delete(self):
        empty = self.make_assignment(title="空作业")
        client = self.client_for(self.teacher)
        self.assertEqual(client.delete(f"/api/admin/assignments/{empty.id}").status_code, 204)

        self.submission(self.p1)
        response = client.delete(f"/api/admin/assignments/{self.assignment.id}")
        self.assertEqual(response.status_code, 400)
        self.assertIn("已有学生提交", response.json()["message"])

    def test_class_with_assignments_cannot_be_deleted(self):
        response = self.client_for(self.teacher).delete(f"/api/admin/classes/{self.klass.id}")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "该班级已布置作业或考试，不能删除")

    def test_results(self):
        self.submission(self.p1, "AC")
        self.submission(self.p2, "PAC", passed=2)
        recalculate_score(self.assignment, self.student.id)
        data = self.client_for(self.teacher).get(f"/api/admin/assignments/{self.assignment.id}/results").json()["data"]

        self.assertEqual([p["problem_id"] for p in data["problems"]], [self.p1.id, self.p2.id])
        first, second = data["rows"]
        self.assertEqual((first["student_no"], first["score"], first["solved_count"]), ("20260001", 80, 1))
        self.assertEqual(first["problems"][str(self.p2.id)]["score"], 20)
        self.assertEqual((second["real_name"], second["submitted"], second["problems"][str(self.p1.id)]), ("李四", False, None))
        self.assertEqual(data["summary"], {"member_count": 2, "submitted_count": 1, "average_score": 40, "full_score_count": 0})


@override_settings(CACHES=LOCMEM_CACHE)
class StudentAssignmentApiTests(AssignmentTestBase):
    def test_list_only_published_assignments_of_my_classes(self):
        self.make_assignment(title="未发布", is_published=False)
        other_class = ClassGroup.objects.create(name="外班", teacher=self.teacher)
        self.make_assignment(class_group=other_class, title="外班作业")
        removed_class = ClassGroup.objects.create(name="已移出的班", teacher=self.teacher)
        ClassMember.objects.create(class_group=removed_class, student=self.student, is_removed=True)
        self.make_assignment(class_group=removed_class, title="已移出班级的作业")

        titles = [a["title"] for a in self.client_for(self.student).get("/api/assignments").json()["data"]]
        self.assertEqual(titles, ["第一次作业"])

    def test_status_filters(self):
        self.make_assignment(start=1, end=2, title="未开始")
        self.make_assignment(start=-3, end=-2, title="已截止")
        self.make_assignment(start=-3, end=-2, title="可迟交", allow_late=True)
        client = self.client_for(self.student)

        def titles(status):
            return [a["title"] for a in client.get(f"/api/assignments?status={status}").json()["data"]]

        self.assertEqual(sorted(titles("todo")), ["可迟交", "第一次作业"])
        self.assertEqual(titles("not_started"), ["未开始"])
        self.assertEqual(titles("ended"), ["已截止"])

    def test_my_progress_in_list_and_detail(self):
        self.submission(self.p1, "AC")
        recalculate_score(self.assignment, self.student.id)
        client = self.client_for(self.student)

        item = client.get("/api/assignments").json()["data"][0]
        self.assertEqual((item["my_score"], item["my_solved"], item["problem_count"], item["total_score"]), (60, 1, 2, 100))
        detail = client.get(f"/api/assignments/{self.assignment.id}").json()["data"]
        self.assertEqual(
            [(p["title"], p["score"], p["my_score"], p["accepted"]) for p in detail["problems"]],
            [("A+B", 60, 60, True), ("私有题", 40, None, False)],
        )
        # 同班同学看到的是自己的进度
        self.assertIsNone(self.client_for(self.classmate).get("/api/assignments").json()["data"][0]["my_score"])

    def test_problems_hidden_before_start(self):
        upcoming = self.make_assignment(start=1, end=2)
        detail = self.client_for(self.student).get(f"/api/assignments/{upcoming.id}").json()["data"]
        self.assertEqual((detail["status"], detail["problems"]), ("not_started", []))

    def test_outsiders_cannot_see_assignment(self):
        response = self.client_for(self.outsider).get(f"/api/assignments/{self.assignment.id}")
        self.assertEqual(response.status_code, 404)

    def test_private_problem_visible_through_assignment(self):
        url = f"/api/problems/{self.p2.id}"
        self.assertEqual(self.client_for(self.student).get(url).status_code, 404)
        response = self.client_for(self.student).get(f"{url}?assignment_id={self.assignment.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["title"], "私有题")
        self.assertEqual(self.client_for(self.outsider).get(f"{url}?assignment_id={self.assignment.id}").status_code, 404)

    def submit(self, user=None, assignment=None, problem=None):
        with mock.patch("judge.tasks.judge_submission.delay"):
            return self.client_for(user or self.student).post(
                "/api/submissions",
                {
                    "problem_id": (problem or self.p2).id,
                    "language": "c",
                    "code": "int main(){}",
                    "assignment_id": (assignment or self.assignment).id,
                },
                format="json",
            )

    def test_submit_in_assignment(self):
        response = self.submit()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Submission.objects.get().assignment, self.assignment)

    def test_submit_rules(self):
        not_started = self.make_assignment(start=1, end=2)
        closed = self.make_assignment(start=-3, end=-2)
        late_ok = self.make_assignment(start=-3, end=-2, allow_late=True, late_penalty=0.1)
        third = Problem.objects.create(title="不在作业中", description="d", is_public=True, test_case_id="c" * 32)

        cases_ = [
            ({"user": self.outsider}, 404, "作业不存在"),
            ({"assignment": not_started}, 400, "作业尚未开始"),
            ({"assignment": closed}, 400, "作业已截止"),
            ({"problem": third}, 404, "该题目不在此作业中"),
        ]
        for kwargs, code, message in cases_:
            with self.subTest(message=message):
                cache.clear()
                response = self.submit(**kwargs)
                self.assertEqual(response.status_code, code)
                self.assertIn(message, response.json()["message"])
        cache.clear()
        self.assertEqual(self.submit(assignment=late_ok).status_code, 201)


class JudgedSubmissionUpdatesScoreTests(AssignmentTestBase, TestCase):
    def test_on_judged_hook(self):
        from judge.judger import on_judged

        submission = self.submission(self.p1, "AC")
        on_judged(submission)
        self.assertEqual(ScoreRecord.objects.get(student=self.student).score, 60)
