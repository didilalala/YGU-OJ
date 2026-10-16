import io
from datetime import timedelta

import openpyxl
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from account.models import StudentProfile, User
from classroom.models import Assignment, AssignmentProblem, ClassGroup, ClassMember
from classroom.scoring import recalculate_score
from contest.models import Exam, ExamProblem
from contest.scoring import recalculate_exam_score
from problem.models import Problem
from submission.models import Submission

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def cases(passed, total=4):
    return [{"case": i + 1, "result": "AC" if i < passed else "WA"} for i in range(total)]


@override_settings(CACHES=LOCMEM_CACHE)
class StatsTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.now = timezone.now()
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        self.other_teacher = User.objects.create_user("t2", password="x", role=User.Role.TEACHER)
        self.klass = ClassGroup.objects.create(name="软件 2601", teacher=self.teacher)
        self.students = [self.make_student(f"2026000{i}", name) for i, name in enumerate(["张三", "李四", "王五", "赵六"], start=1)]
        for student in self.students:
            ClassMember.objects.create(class_group=self.klass, student=student)
        self.removed = self.make_student("20260009", "已移出")
        ClassMember.objects.create(class_group=self.klass, student=self.removed, is_removed=True)

        self.p1 = Problem.objects.create(title="A+B", description="d", is_public=True, test_case_id="a" * 32)
        self.p2 = Problem.objects.create(title="循环", description="d", is_public=True, test_case_id="b" * 32)
        self.assignment = Assignment.objects.create(
            class_group=self.klass, title="第一次作业", is_published=True,
            start_time=self.now - timedelta(days=7), end_time=self.now - timedelta(days=1),
        )
        AssignmentProblem.objects.create(assignment=self.assignment, problem=self.p1, score=60, order=0)
        AssignmentProblem.objects.create(assignment=self.assignment, problem=self.p2, score=40, order=1)

    def make_student(self, student_no, name):
        user = User.objects.create_user(student_no, password="x", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=user, student_no=student_no, real_name=name)
        return user

    def submit(self, student, problem, result, passed=4, assignment=None, exam=None):
        work = exam or assignment or self.assignment
        submission = Submission.objects.create(
            user=student, problem=problem, language="c", code="x", result=result,
            case_info=[] if result == "CE" else cases(passed),
            assignment=None if exam else work, exam=exam,
        )
        Submission.objects.filter(pk=submission.pk).update(created_at=work.start_time + timedelta(minutes=5))
        return submission

    def score_all(self, work=None):
        work = work or self.assignment
        for student in self.students + [self.removed]:
            if isinstance(work, Exam):
                recalculate_exam_score(work, student.id)
            else:
                recalculate_score(work, student.id)

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client


class AssignmentStatsTests(StatsTestBase):
    def setUp(self):
        super().setUp()
        zhang, li, wang, _zhao = self.students
        self.submit(zhang, self.p1, "AC")
        self.submit(zhang, self.p2, "AC")  # 100
        self.submit(li, self.p1, "WA", passed=2)
        self.submit(li, self.p1, "AC")
        self.submit(li, self.p2, "TLE", passed=0)  # 60
        self.submit(wang, self.p1, "CE")
        self.submit(wang, self.p2, "RE", passed=0)  # 0
        self.submit(self.removed, self.p1, "AC")  # 已移出，不计入
        self.score_all()

    def stats(self):
        response = self.client_for(self.teacher).get(f"/api/admin/stats/assignments/{self.assignment.id}")
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]

    def test_summary(self):
        summary = self.stats()["summary"]
        self.assertEqual(summary["member_count"], 4)
        self.assertEqual(summary["submitted_count"], 3)
        self.assertEqual(summary["submission_rate"], 75.0)
        self.assertEqual(summary["average_score"], 40)  # (100 + 60 + 0 + 0) / 4
        self.assertEqual(summary["average_submitted"], 53.33)
        self.assertEqual((summary["max_score"], summary["min_score"], summary["median_submitted"]), (100, 0, 60))
        self.assertEqual(summary["full_score_count"], 1)
        self.assertEqual(summary["pass_rate"], 50.0)  # 100 与 60 及格

    def test_distribution_and_not_submitted(self):
        data = self.stats()
        self.assertEqual([b["count"] for b in data["distribution"]], [1, 1, 0, 0, 1])
        self.assertEqual(data["distribution"][0]["label"], "不及格")
        self.assertEqual([s["real_name"] for s in data["not_submitted"]], ["赵六"])

    def test_problem_stats_and_errors(self):
        data = self.stats()
        a, b = data["problems"]
        self.assertEqual((a["attempted_count"], a["accepted_count"], a["accepted_rate"]), (3, 2, 50.0))
        self.assertEqual((a["submission_count"], a["ac_submission_count"]), (4, 2))
        self.assertEqual(a["errors"], {"WA": 1, "CE": 1, "TLE": 0, "MLE": 0, "RE": 0, "PAC": 0})
        self.assertEqual(b["average_score"], 10)  # 只有张三 40 分，按 4 人平均
        self.assertEqual(data["errors"]["TLE"], 1)
        self.assertEqual(data["errors"]["RE"], 1)

    def test_cached_until_scores_change(self):
        first = self.stats()
        # 直接改库不会使缓存失效
        Submission.objects.filter(user=self.students[3]).delete()
        Submission.objects.create(user=self.students[3], problem=self.p1, language="c", code="x", result="AC", assignment=self.assignment)
        self.assertEqual(self.stats(), first)
        # 成绩重算后失效
        with self.captureOnCommitCallbacks(execute=True):
            recalculate_score(self.assignment, self.students[3].id)
        self.assertEqual(self.stats()["summary"]["submitted_count"], 4)

    def test_permissions(self):
        url = f"/api/admin/stats/assignments/{self.assignment.id}"
        self.assertEqual(self.client_for(self.other_teacher).get(url).status_code, 404)
        self.assertEqual(self.client_for(self.students[0]).get(url).status_code, 403)


class ClassStatsTests(StatsTestBase):
    def setUp(self):
        super().setUp()
        zhang, li, wang, _ = self.students
        self.exam = Exam.objects.create(
            class_group=self.klass, title="期中考试", rule_type="OI", is_published=True,
            start_time=self.now - timedelta(hours=3), end_time=self.now - timedelta(hours=1),
        )
        ExamProblem.objects.create(exam=self.exam, problem=self.p1, score=100)
        Assignment.objects.create(  # 未发布、未开始的不计入
            class_group=self.klass, title="未发布", start_time=self.now - timedelta(days=1), end_time=self.now + timedelta(days=1),
        )
        self.submit(zhang, self.p1, "AC")
        self.submit(zhang, self.p2, "AC")
        self.submit(li, self.p1, "AC")
        self.submit(zhang, self.p1, "PAC", passed=2, exam=self.exam)
        self.submit(wang, self.p1, "AC", exam=self.exam)
        self.score_all()
        self.score_all(self.exam)

    def test_overview(self):
        data = self.client_for(self.teacher).get(f"/api/admin/stats/classes/{self.klass.id}").json()["data"]

        self.assertEqual([(w["kind"], w["title"]) for w in data["works"]], [("assignment", "第一次作业"), ("exam", "期中考试")])
        self.assertEqual(data["works"][0]["average_rate"], 40.0)  # (100 + 60) / 4 / 100
        self.assertEqual(data["works"][1]["submission_rate"], 50.0)
        ranking = [(s["real_name"], s["total_score"], s["rate"], s["rank"]) for s in data["students"]]
        self.assertEqual(ranking, [("张三", 150, 75.0, 1), ("王五", 100, 50.0, 2), ("李四", 60, 30.0, 3), ("赵六", 0, 0.0, 4)])
        self.assertIsNone(data["students"][3]["scores"][f"assignment:{self.assignment.id}"])
        self.assertEqual(data["summary"], {"member_count": 4, "assignment_count": 1, "exam_count": 1, "average_rate": 38.8})

    def test_export(self):
        response = self.client_for(self.teacher).get(f"/api/admin/stats/classes/{self.klass.id}/export")

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        workbook = openpyxl.load_workbook(io.BytesIO(response.content))
        self.assertEqual(workbook.sheetnames, ["成绩总表", "作业-第一次作业", "考试-期中考试"])
        summary = list(workbook["成绩总表"].values)
        self.assertEqual(summary[0][:4], ("学号", "姓名", "作业：第一次作业（100）", "考试：期中考试（100）"))
        self.assertEqual(summary[1], ("20260001", "张三", 100, 50, 150, 200, 75, 1))
        self.assertEqual(summary[4][2], "未提交")
        detail = list(workbook["作业-第一次作业"].values)
        self.assertEqual(detail[2][:5], ("20260002", "李四", 60, None, 60))

    def test_sheet_names_are_sanitised_and_unique(self):
        from stats.export import _sheet_title

        used = set()
        self.assertEqual(_sheet_title("作业-第 1/2 周:循环*", used), "作业-第 1_2 周_循环_")
        self.assertEqual(_sheet_title("作业-第 1/2 周:循环*", used), "作业-第 1_2 周_循环_(2)")
        self.assertEqual(len(_sheet_title("长" * 40, used)), 31)

    def test_other_teacher_cannot_export(self):
        response = self.client_for(self.other_teacher).get(f"/api/admin/stats/classes/{self.klass.id}/export")
        self.assertEqual(response.status_code, 404)


class MyScoresTests(StatsTestBase):
    def test_learning_curve(self):
        zhang, li = self.students[:2]
        exam = Exam.objects.create(
            class_group=self.klass, title="期中考试", is_published=True,
            start_time=self.now - timedelta(hours=3), end_time=self.now - timedelta(hours=1),
        )
        ExamProblem.objects.create(exam=exam, problem=self.p1, score=100)
        upcoming = Assignment.objects.create(
            class_group=self.klass, title="进行中", is_published=True,
            start_time=self.now - timedelta(hours=1), end_time=self.now + timedelta(days=1),
        )
        AssignmentProblem.objects.create(assignment=upcoming, problem=self.p1, score=100)
        self.submit(zhang, self.p1, "AC")
        self.submit(li, self.p1, "AC")
        self.submit(zhang, self.p1, "AC", exam=exam)
        self.score_all()
        self.score_all(exam)
        client = self.client_for(zhang)

        data = client.get("/api/scores/mine").json()["data"]["classes"][0]
        # 进行中且未提交的作业不计入；考试未公布成绩时不计入
        self.assertEqual([(p["title"], p["rate"], p["class_average_rate"]) for p in data["points"]], [("第一次作业", 60.0, 30.0)])

        exam.is_score_published = True
        exam.save()
        data = client.get("/api/scores/mine").json()["data"]["classes"][0]
        self.assertEqual([p["title"] for p in data["points"]], ["第一次作业", "期中考试"])
        self.assertEqual(data["points"][1]["rate"], 100.0)
        self.assertEqual(data["rate"], 80.0)

    def test_student_without_class(self):
        lonely = self.make_student("20269999", "无班级")
        self.assertEqual(self.client_for(lonely).get("/api/scores/mine").json()["data"], {"classes": []})


class OverviewTests(StatsTestBase):
    def get(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client.get("/api/admin/stats/overview").json()["data"]

    def test_summary_and_trend(self):
        # 进行中的作业：4 名学生中 1 人已提交
        current = Assignment.objects.create(
            class_group=self.klass, title="本周作业", is_published=True,
            start_time=self.now - timedelta(days=1), end_time=self.now + timedelta(days=1),
        )
        AssignmentProblem.objects.create(assignment=current, problem=self.p1, score=100, order=0)
        self.submit(self.students[0], self.p1, "AC", assignment=current)
        Submission.objects.create(user=self.students[0], problem=self.p1, language="c", code="x", result="AC", case_info=cases(4))

        data = self.get(self.teacher)
        self.assertEqual(data["summary"]["class_count"], 1)
        # 已移出的学生不计入
        self.assertEqual(data["summary"]["student_count"], 4)
        self.assertEqual(data["summary"]["active_assignments"], 1)
        self.assertEqual(data["summary"]["today_submissions"], 1)
        self.assertEqual(len(data["trend"]), 14)
        self.assertEqual(data["trend"][-1]["count"], 1)
        self.assertEqual(data["trend"][-1]["accepted"], 1)

    def test_attention_lists_low_submission_assignments(self):
        current = Assignment.objects.create(
            class_group=self.klass, title="快截止了", is_published=True,
            start_time=self.now - timedelta(days=2), end_time=self.now + timedelta(hours=10),
        )
        AssignmentProblem.objects.create(assignment=current, problem=self.p1, score=100, order=0)
        data = self.get(self.teacher)
        titles = [row["title"] for row in data["attention"]]
        self.assertIn("快截止了", titles)
        row = next(row for row in data["attention"] if row["title"] == "快截止了")
        self.assertEqual((row["submitted"], row["member_count"], row["rate"]), (0, 4, 0.0))

    def test_other_teacher_sees_nothing_of_this_class(self):
        data = self.get(self.other_teacher)
        self.assertEqual(data["summary"]["class_count"], 0)
        self.assertEqual(data["summary"]["student_count"], 0)
        self.assertEqual(data["attention"], [])

    def test_students_cannot_access(self):
        client = APIClient()
        client.force_authenticate(self.students[0])
        self.assertEqual(client.get("/api/admin/stats/overview").status_code, 403)
