from rest_framework.test import APIClient, APITestCase

from account.models import User
from submission.models import Submission

from . import test_cases
from .models import KnowledgePoint, Problem
from .tests import TempTestCaseDirMixin


class ProblemApiTestBase(TempTestCaseDirMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user("admin1", password="x", role=User.Role.ADMIN)
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        self.other_teacher = User.objects.create_user("t2", password="x", role=User.Role.TEACHER)
        self.student = User.objects.create_user("20260001", password="x", role=User.Role.STUDENT)

        self.loop = KnowledgePoint.objects.create(name="循环", course="C 语言")
        self.for_loop = KnowledgePoint.objects.create(name="for 循环", parent=self.loop, course="C 语言")
        self.array = KnowledgePoint.objects.create(name="数组", course="C 语言")

        self.public = self.make_problem("A+B", is_public=True, difficulty="easy", points=[self.for_loop])
        self.public_hard = self.make_problem("最短路", is_public=True, difficulty="hard", points=[self.array])
        self.private = self.make_problem("私有题", created_by=self.teacher)
        self.others_private = self.make_problem("别人的题", created_by=self.other_teacher)

    def make_problem(self, title, points=(), **fields):
        fields = {"description": "desc", "created_by": self.admin, **fields}
        problem = Problem.objects.create(title=title, **fields)
        problem.knowledge_points.set(points)
        return problem

    def client_for(self, user=None):
        client = APIClient()
        if user:
            client.force_authenticate(user)
        return client

    @staticmethod
    def ids(response):
        return [item["id"] for item in response.json()["data"]["results"]]


class PublicProblemApiTests(ProblemApiTestBase):
    def test_visitors_see_public_problems(self):
        response = self.client_for().get("/api/problems")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ids(response), [self.public.id, self.public_hard.id])
        item = response.json()["data"]["results"][0]
        self.assertEqual(item["knowledge_points"], [{"id": self.for_loop.id, "name": "for 循环"}])
        self.assertIsNone(item["my_status"])
        self.assertNotIn("test_case_id", item)

    def test_visibility_by_role(self):
        self.assertEqual(len(self.ids(self.client_for(self.student).get("/api/problems"))), 2)
        teacher_ids = self.ids(self.client_for(self.teacher).get("/api/problems"))
        self.assertIn(self.private.id, teacher_ids)
        self.assertNotIn(self.others_private.id, teacher_ids)
        self.assertEqual(len(self.ids(self.client_for(self.admin).get("/api/problems"))), 4)

    def test_filters(self):
        client = self.client_for()

        def ids(query):
            return self.ids(client.get(f"/api/problems?{query}"))

        self.assertEqual(ids("difficulty=hard"), [self.public_hard.id])
        # 按上级知识点筛选也包含下级知识点的题目
        self.assertEqual(ids(f"knowledge_point={self.loop.id}"), [self.public.id])
        self.assertEqual(ids(f"knowledge_point={self.array.id}"), [self.public_hard.id])
        self.assertEqual(ids("keyword=最短"), [self.public_hard.id])
        self.assertEqual(ids(f"keyword={self.public.id}"), [self.public.id])
        self.assertEqual(client.get("/api/problems?knowledge_point=x").status_code, 400)

    def test_my_status(self):
        Submission.objects.create(user=self.student, problem=self.public, language="c", code="x", result="WA")
        Submission.objects.create(user=self.student, problem=self.public, language="c", code="x", result="AC")
        Submission.objects.create(user=self.student, problem=self.public_hard, language="c", code="x", result="WA")
        results = self.client_for(self.student).get("/api/problems").json()["data"]["results"]

        self.assertEqual({item["id"]: item["my_status"] for item in results}, {self.public.id: "AC", self.public_hard.id: "TRIED"})

    def test_detail_hides_judging_internals(self):
        self.public.is_template = True
        self.public.template_code = {"c": {"prepend": "#include <stdio.h>", "template": "int add(int a, int b) {\n}", "append": "int main(){}"}}
        self.public.test_case_id = "a" * 32
        self.public.save()
        data = self.client_for(self.student).get(f"/api/problems/{self.public.id}").json()["data"]

        self.assertEqual(data["template"], {"c": "int add(int a, int b) {\n}"})
        self.assertEqual(data["languages"], ["c"])
        self.assertNotIn("template_code", data)
        self.assertNotIn("test_case_id", data)

    def test_detail_of_hidden_problem_is_not_found(self):
        response = self.client_for(self.student).get(f"/api/problems/{self.private.id}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "题目不存在")
        self.assertEqual(self.client_for(self.teacher).get(f"/api/problems/{self.private.id}").status_code, 200)

    def test_knowledge_points(self):
        data = self.client_for().get("/api/knowledge-points").json()["data"]
        self.assertEqual(len(data), 3)
        self.assertIn({"id": self.for_loop.id, "name": "for 循环", "parent": self.loop.id, "course": "C 语言"}, data)
        self.assertEqual(self.client_for().get("/api/knowledge-points?course=Java").json()["data"], [])


class AdminProblemApiTests(ProblemApiTestBase):
    def payload(self, **overrides):
        payload = {
            "title": "新题",
            "description": "求 $a+b$",
            "input_desc": "两个整数",
            "output_desc": "和",
            "samples": [{"input": "1 2", "output": "3"}],
            "time_limit": 2000,
            "memory_limit": 128,
            "difficulty": "medium",
            "knowledge_point_ids": [self.loop.id, self.array.id],
            "is_public": False,
        }
        payload.update(overrides)
        return payload

    def test_teacher_creates_problem_with_test_cases(self):
        test_case_id = test_cases.save_test_cases([("1 2\n", "3\n"), ("3 4\n", "7\n")])
        response = self.client_for(self.teacher).post(
            "/api/admin/problems", self.payload(test_case_id=test_case_id), format="json"
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        problem = Problem.objects.get(pk=data["id"])
        self.assertEqual(problem.created_by, self.teacher)
        self.assertEqual(set(problem.knowledge_points.all()), {self.loop, self.array})
        self.assertEqual(data["test_cases"], [
            {"index": 1, "input_size": 4, "output_size": 2},
            {"index": 2, "input_size": 4, "output_size": 2},
        ])
        self.assertTrue(data["can_edit"])

    def test_validation(self):
        test_case_id = test_cases.save_test_cases([("1", "1")])
        self.public.test_case_id = test_case_id
        self.public.save()
        cases = [
            ({"time_limit": 50}, "时间限制应在"),
            ({"memory_limit": 4096}, "内存限制应在"),
            ({"samples": [{"input": "1"}]}, "每组样例"),
            ({"samples": [{"input": "1", "output": "1"}] * 11}, "不超过 10 组"),
            ({"test_case_id": "f" * 32}, "测试数据不存在"),
            ({"test_case_id": "../../etc"}, "测试数据不存在"),
            ({"test_case_id": test_case_id}, "已被其他题目使用"),
            ({"is_template": True}, "至少需要配置一种语言"),
            ({"is_template": True, "template_code": {"pascal": {}}}, "不支持的语言"),
            ({"is_template": True, "template_code": {"c": {"main": "x"}}}, "prepend、template、append"),
            ({"knowledge_point_ids": [999999]}, "knowledge_point_ids"),
            ({"title": ""}, "title"),
        ]
        client = self.client_for(self.teacher)
        for overrides, message in cases:
            with self.subTest(overrides=list(overrides)):
                response = client.post("/api/admin/problems", self.payload(**overrides), format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, response.json()["message"])

    def test_admin_list_scope_and_can_edit(self):
        response = self.client_for(self.teacher).get("/api/admin/problems")
        results = {item["id"]: item for item in response.json()["data"]["results"]}

        self.assertEqual(set(results), {self.public.id, self.public_hard.id, self.private.id})
        self.assertTrue(results[self.private.id]["can_edit"])
        self.assertFalse(results[self.public.id]["can_edit"])
        self.assertEqual(results[self.public.id]["created_by_name"], "admin1")
        self.assertNotIn("description", results[self.public.id])

        mine = self.ids(self.client_for(self.teacher).get("/api/admin/problems?mine=1"))
        self.assertEqual(mine, [self.private.id])
        self.assertEqual(self.ids(self.client_for(self.admin).get("/api/admin/problems?is_public=0")),
                         [self.private.id, self.others_private.id])

    def test_students_cannot_use_admin_api(self):
        self.assertEqual(self.client_for(self.student).get("/api/admin/problems").status_code, 403)
        self.assertEqual(self.client_for(self.student).post("/api/admin/problems", self.payload(), format="json").status_code, 403)

    def test_teacher_edits_only_own_problems(self):
        client = self.client_for(self.teacher)
        response = client.patch(f"/api/admin/problems/{self.private.id}", {"title": "改名", "is_public": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.private.refresh_from_db()
        self.assertEqual((self.private.title, self.private.is_public), ("改名", True))

        # 可以查看别人的公开题目，但不能修改；别人的私有题目看不到
        self.assertEqual(client.get(f"/api/admin/problems/{self.public.id}").status_code, 200)
        response = client.patch(f"/api/admin/problems/{self.public.id}", {"title": "x"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["message"], "只能修改自己创建的题目")
        self.assertEqual(client.get(f"/api/admin/problems/{self.others_private.id}").status_code, 404)
        # 管理员不受限制
        response = self.client_for(self.admin).patch(f"/api/admin/problems/{self.others_private.id}", {"title": "y"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_replacing_test_cases_removes_old_data(self):
        old = test_cases.save_test_cases([("1", "1")])
        new = test_cases.save_test_cases([("2", "2")])
        self.private.test_case_id = old
        self.private.save()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.teacher).patch(
                f"/api/admin/problems/{self.private.id}", {"test_case_id": new}, format="json"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.stored_ids(), [new])

    def test_delete(self):
        test_case_id = test_cases.save_test_cases([("1", "1")])
        self.private.test_case_id = test_case_id
        self.private.save()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.teacher).delete(f"/api/admin/problems/{self.private.id}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Problem.objects.filter(pk=self.private.id).exists())
        self.assertEqual(self.stored_ids(), [])

    def test_cannot_delete_problem_with_submissions(self):
        Submission.objects.create(user=self.student, problem=self.private, language="c", code="x")
        response = self.client_for(self.teacher).delete(f"/api/admin/problems/{self.private.id}")

        self.assertEqual(response.status_code, 400)
        self.assertIn("已有提交记录", response.json()["message"])
        self.assertTrue(Problem.objects.filter(pk=self.private.id).exists())


class AdminKnowledgePointApiTests(ProblemApiTestBase):
    def test_create_update_delete(self):
        client = self.client_for(self.teacher)
        response = client.post("/api/admin/knowledge-points", {"name": "while 循环", "parent": self.loop.id, "course": "C 语言"}, format="json")
        self.assertEqual(response.status_code, 201)
        point_id = response.json()["data"]["id"]

        self.assertEqual(client.patch(f"/api/admin/knowledge-points/{point_id}", {"name": "do-while"}, format="json").status_code, 200)
        self.assertEqual(client.delete(f"/api/admin/knowledge-points/{point_id}").status_code, 204)

    def test_duplicate_name_in_course(self):
        response = self.client_for(self.teacher).post("/api/admin/knowledge-points", {"name": "循环", "course": "C 语言"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "课程「C 语言」下已有同名知识点「循环」")
        # 改名为同课程已有名称也被拒绝；同名但不同课程允许
        response = self.client_for(self.teacher).patch(f"/api/admin/knowledge-points/{self.array.id}", {"name": "循环"}, format="json")
        self.assertEqual(response.status_code, 400)
        response = self.client_for(self.teacher).post("/api/admin/knowledge-points", {"name": "循环", "course": "Java"}, format="json")
        self.assertEqual(response.status_code, 201)

    def test_cannot_create_cycle(self):
        response = self.client_for(self.teacher).patch(
            f"/api/admin/knowledge-points/{self.loop.id}", {"parent": self.for_loop.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("不能选择自身或下级", response.json()["message"])

    def test_cannot_delete_point_with_children(self):
        response = self.client_for(self.teacher).delete(f"/api/admin/knowledge-points/{self.loop.id}")
        self.assertEqual(response.status_code, 400)
        self.assertIn("下级知识点", response.json()["message"])

    def test_deleting_point_untags_problems(self):
        self.client_for(self.teacher).delete(f"/api/admin/knowledge-points/{self.array.id}")
        self.assertEqual(list(self.public_hard.knowledge_points.all()), [])
        self.assertTrue(Problem.objects.filter(pk=self.public_hard.id).exists())

    def test_students_cannot_manage(self):
        response = self.client_for(self.student).post("/api/admin/knowledge-points", {"name": "x"}, format="json")
        self.assertEqual(response.status_code, 403)
