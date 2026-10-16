from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from account.models import User
from judge.models import Language
from options import site
from problem.models import Problem

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CPP = "#include <cstdio>\nint main(){return 0;}"


@override_settings(CACHES=LOCMEM_CACHE)
class SiteSettingsTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user("admin1", password="x", role=User.Role.ADMIN)
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        self.student = User.objects.create_user("20260001", password="x", role=User.Role.STUDENT)
        self.problem = Problem.objects.create(title="A+B", description="d", is_public=True, test_case_id="a" * 32)

    def client_for(self, user=None):
        client = APIClient()
        if user:
            client.force_authenticate(user)
        return client

    def submit(self, user, language="cpp", code=CPP):
        with mock.patch("judge.tasks.judge_submission.delay"):
            return self.client_for(user).post(
                "/api/submissions", {"problem_id": self.problem.id, "language": language, "code": code}, format="json"
            )

    def test_public_site_info_for_visitors(self):
        data = self.client_for().get("/api/site").json()["data"]

        self.assertEqual(data["settings"]["site_name"], "阳光学院在线评测平台")
        self.assertEqual(data["settings"]["submit_interval_seconds"], 5)
        self.assertEqual([lang["key"] for lang in data["languages"]], ["c", "cpp", "java", "python"])
        self.assertIn("monaco_id", data["languages"][0])
        self.assertNotIn("run_config", data["languages"][0])  # 判题配置不对外

    def test_admin_lists_definitions_with_defaults(self):
        items = {i["key"]: i for i in self.client_for(self.admin).get("/api/admin/settings").json()["data"]["items"]}

        self.assertEqual(items["max_code_kb"]["value"], 64)
        self.assertEqual((items["max_code_kb"]["min_value"], items["max_code_kb"]["max_value"]), (1, 1024))
        self.assertEqual(items["allow_registration"]["kind"], "bool")

    def test_only_admins_manage_settings(self):
        url = "/api/admin/settings"
        self.assertEqual(self.client_for(self.teacher).get(url).status_code, 403)
        self.assertEqual(self.client_for(self.teacher).patch(url, {"max_code_kb": 8}, format="json").status_code, 403)
        self.assertEqual(self.client_for().get(url).status_code, 401)

    def test_update_saves_and_records_editor(self):
        response = self.client_for(self.admin).patch(
            "/api/admin/settings", {"site_name": "  校园 OJ  ", "submit_interval_seconds": 0}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        items = {i["key"]: i["value"] for i in response.json()["data"]["items"]}
        self.assertEqual((items["site_name"], items["submit_interval_seconds"]), ("校园 OJ", 0))
        self.assertEqual(site.get("site_name"), "校园 OJ")

    def test_invalid_update_saves_nothing(self):
        response = self.client_for(self.admin).patch(
            "/api/admin/settings", {"site_name": "新名字", "max_code_kb": 0, "unknown": 1}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("未保存任何修改", response.json()["message"])
        self.assertEqual(set(response.json()["data"]), {"max_code_kb", "unknown"})
        self.assertEqual(site.get("site_name"), "阳光学院在线评测平台")

    def test_type_checks(self):
        cases = [
            {"allow_registration": "yes"},
            {"submit_interval_seconds": True},
            {"submit_interval_seconds": 1.5},
            {"submit_interval_seconds": 301},
            {"site_name": ""},
            {"site_name": "x" * 65},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertEqual(self.client_for(self.admin).patch("/api/admin/settings", changes, format="json").status_code, 400)

    def test_submit_interval_setting_is_enforced(self):
        site.update(self.admin, {"submit_interval_seconds": 60})
        self.assertEqual(self.submit(self.student).status_code, 201)
        self.assertEqual(self.submit(self.student).status_code, 429)

        site.update(self.admin, {"submit_interval_seconds": 0})
        self.assertEqual(self.submit(self.student).status_code, 201)
        self.assertEqual(self.submit(self.student).status_code, 201)

    def test_code_length_setting_is_enforced(self):
        site.update(self.admin, {"max_code_kb": 1})
        self.assertEqual(self.submit(self.student, code="x" * 1025).status_code, 400)
        self.assertIn("1 KB", self.submit(self.student, code="x" * 1025).json()["message"])
        self.assertEqual(self.submit(self.student, code="x" * 1000).status_code, 201)

    def test_closing_registration(self):
        payload = {"username": "newcoder", "email": "n@example.edu", "password": "Coder-2026!"}
        site.update(self.admin, {"allow_registration": False})
        response = self.client_for().post("/api/auth/register", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("注册已关闭", response.json()["message"])
        self.assertFalse(User.objects.filter(username="newcoder").exists())

        site.update(self.admin, {"allow_registration": True})
        self.assertEqual(self.client_for().post("/api/auth/register", payload, format="json").status_code, 201)

    def test_disabled_language_cannot_be_submitted(self):
        Language.objects.filter(key="python").update(enabled=False)
        self.assertIn("暂不支持", self.submit(self.student, language="python", code="print(1)").json()["message"])
        self.assertNotIn("python", [lang["key"] for lang in self.client_for().get("/api/site").json()["data"]["languages"]])
        self.assertEqual(self.problem.languages, ["c", "cpp", "java"])

    def test_unknown_language_rejected(self):
        self.assertEqual(self.submit(self.student, language="pascal").status_code, 400)

    def test_default_limits_match_settings(self):
        site.update(self.admin, {"default_time_limit_ms": 2000, "default_memory_limit_mb": 512})
        data = self.client_for().get("/api/site").json()["data"]["settings"]
        self.assertEqual((data["default_time_limit_ms"], data["default_memory_limit_mb"]), (2000, 512))
