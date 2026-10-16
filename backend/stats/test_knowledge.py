from datetime import timedelta

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from account.models import StudentProfile, User
from classroom.models import Assignment, AssignmentProblem, ClassGroup, ClassMember
from contest.models import Exam, ExamProblem
from problem.models import KnowledgePoint, Problem
from submission.models import Submission

from .knowledge import class_knowledge

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def cases(passed, total=4):
    return [{"case": i + 1, "result": "AC" if i < passed else "WA"} for i in range(total)]


@override_settings(CACHES=LOCMEM_CACHE)
class KnowledgeTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        now = timezone.now()
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        self.klass = ClassGroup.objects.create(name="软件 2601", teacher=self.teacher)
        self.alice = self.make_student("20260001", "张三")
        self.bob = self.make_student("20260002", "李四")
        for student in (self.alice, self.bob):
            ClassMember.objects.create(class_group=self.klass, student=student)

        # 循环 ─┬─ for 循环
        #       └─ while 循环        数组（独立）
        self.loop = KnowledgePoint.objects.create(name="循环", course="C")
        self.for_loop = KnowledgePoint.objects.create(name="for 循环", parent=self.loop, course="C")
        self.while_loop = KnowledgePoint.objects.create(name="while 循环", parent=self.loop, course="C")
        self.array = KnowledgePoint.objects.create(name="数组", course="C")
        self.unused = KnowledgePoint.objects.create(name="指针", course="C")

        self.p_for = self.problem("求和", [self.for_loop])
        self.p_while = self.problem("猜数", [self.while_loop])
        self.p_array = self.problem("逆序", [self.array, self.for_loop])
        self.p_untagged = self.problem("无标签", [])
        self.p_outside = self.problem("作业外的题", [self.array])

        self.assignment = Assignment.objects.create(
            class_group=self.klass, title="作业", is_published=True,
            start_time=now - timedelta(days=2), end_time=now - timedelta(days=1),
        )
        for problem in (self.p_for, self.p_while, self.p_untagged):
            AssignmentProblem.objects.create(assignment=self.assignment, problem=problem, score=10)
        self.exam = Exam.objects.create(
            class_group=self.klass, title="考试", is_published=True,
            start_time=now - timedelta(hours=3), end_time=now - timedelta(hours=1),
        )
        ExamProblem.objects.create(exam=self.exam, problem=self.p_array, score=10)

    def make_student(self, student_no, name):
        user = User.objects.create_user(student_no, password="x", role=User.Role.STUDENT)
        StudentProfile.objects.create(user=user, student_no=student_no, real_name=name)
        return user

    def problem(self, title, points):
        problem = Problem.objects.create(title=title, description="d", is_public=True, test_case_id="a" * 32)
        problem.knowledge_points.set(points)
        return problem

    def submit(self, student, problem, result="AC", passed=4, **fields):
        return Submission.objects.create(
            user=student, problem=problem, language="c", code="x", result=result,
            case_info=[] if result == "CE" else cases(passed), **fields,
        )

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client


class ClassKnowledgeTests(KnowledgeTestBase):
    def setUp(self):
        super().setUp()
        self.submit(self.alice, self.p_for, "AC", assignment=self.assignment)
        self.submit(self.alice, self.p_while, "PAC", passed=2, assignment=self.assignment)
        self.submit(self.alice, self.p_while, "WA", passed=1, assignment=self.assignment)  # 取最佳 0.5
        self.submit(self.alice, self.p_array, "AC", exam=self.exam)
        self.submit(self.bob, self.p_for, "CE", assignment=self.assignment)
        self.submit(self.bob, self.p_while, "AC")  # 平时练习也计入
        self.submit(self.bob, self.p_outside, "AC")  # 不在班级作业考试中的题不计入

    def data(self):
        response = self.client_for(self.teacher).get(f"/api/admin/stats/classes/{self.klass.id}/knowledge")
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]

    def test_points_cover_descendants_and_skip_unused(self):
        points = {p["name"]: p for p in self.data()["points"]}

        self.assertEqual(set(points), {"循环", "for 循环", "while 循环", "数组"})
        self.assertEqual(points["循环"]["problem_count"], 3)  # 求和、猜数、逆序（逆序也属于 for 循环）
        self.assertEqual(points["for 循环"]["problem_count"], 2)
        self.assertEqual((points["循环"]["depth"], points["for 循环"]["depth"]), (0, 1))
        # 树形顺序：上级后面紧跟下级
        self.assertEqual([p["name"] for p in self.data()["points"]], ["循环", "for 循环", "while 循环", "数组"])
        self.assertEqual([p["title"] for p in points["数组"]["problems"]], ["逆序"])

    def test_mastery(self):
        data = self.data()
        alice = next(s for s in data["students"] if s["real_name"] == "张三")
        bob = next(s for s in data["students"] if s["real_name"] == "李四")
        ids = {p["name"]: str(p["id"]) for p in data["points"]}

        # 张三：求和 1、猜数 0.5、逆序 1
        self.assertEqual(alice["mastery"][ids["循环"]], 83.3)
        self.assertEqual(alice["mastery"][ids["while 循环"]], 50.0)
        self.assertEqual(alice["accepted"][ids["循环"]], 2)
        # 李四：求和编译错误 0、猜数练习通过 1、逆序没做 0
        self.assertEqual(bob["mastery"][ids["循环"]], 33.3)
        self.assertEqual(bob["mastery"][ids["数组"]], 0.0)

        points = {p["name"]: p for p in data["points"]}
        self.assertEqual(points["while 循环"]["average_mastery"], 75.0)
        self.assertEqual(points["循环"]["average_pass_rate"], 50.0)  # (2 + 1) / (2 × 3)

    def test_weakest_and_untagged(self):
        data = self.data()
        names = {p["id"]: p["name"] for p in data["points"]}
        # 数组与 for 循环平均都是 50%，并列最低
        self.assertEqual({names[pid] for pid in data["weakest"][:2]}, {"数组", "for 循环"})
        self.assertEqual(data["untagged_problem_count"], 1)
        self.assertEqual(data["problem_count"], 4)

    def test_practice_submission_refreshes_cache(self):
        from judge.judger import on_judged

        before = self.data()
        bob_id = str(self.array.id)
        self.assertEqual(next(s for s in before["students"] if s["real_name"] == "李四")["mastery"][bob_id], 0.0)
        submission = self.submit(self.bob, self.p_array, "AC")
        with self.captureOnCommitCallbacks(execute=True):
            on_judged(submission)
        after = self.data()
        self.assertEqual(next(s for s in after["students"] if s["real_name"] == "李四")["mastery"][bob_id], 100.0)

    def test_permissions(self):
        other = User.objects.create_user("t2", password="x", role=User.Role.TEACHER)
        url = f"/api/admin/stats/classes/{self.klass.id}/knowledge"
        self.assertEqual(self.client_for(other).get(url).status_code, 404)
        self.assertEqual(self.client_for(self.alice).get(url).status_code, 403)

    def test_student_view_in_my_scores(self):
        data = self.client_for(self.alice).get("/api/scores/mine").json()["data"]["classes"][0]
        knowledge = {k["name"]: k for k in data["knowledge"]}
        self.assertEqual(knowledge["循环"]["mastery"], 83.3)
        self.assertEqual(knowledge["循环"]["class_average"], 58.3)  # (83.3 + 33.3) / 2
        self.assertEqual(knowledge["循环"]["accepted_count"], 2)

    def test_removed_students_and_unpublished_work_excluded(self):
        ClassMember.objects.filter(student=self.bob).update(is_removed=True)
        Assignment.objects.create(
            class_group=self.klass, title="未发布", start_time=self.exam.start_time, end_time=self.exam.end_time,
        ).items.create(problem=self.p_outside, score=10)
        cache.clear()
        data = class_knowledge(self.klass)
        self.assertEqual([s["real_name"] for s in data["students"]], ["张三"])
        self.assertEqual({p["name"] for p in data["points"]}, {"循环", "for 循环", "while 循环", "数组"})
        self.assertEqual(next(p for p in data["points"] if p["name"] == "数组")["problem_count"], 1)


class EmptyClassTests(KnowledgeTestBase):
    def test_class_without_tagged_problems(self):
        empty = ClassGroup.objects.create(name="空班", teacher=self.teacher)
        data = class_knowledge(empty)
        self.assertEqual((data["points"], data["students"], data["weakest"]), ([], [], []))
