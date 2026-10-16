import shutil
import tempfile
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from account.models import User
from classroom.models import ScoreRecord  # noqa: F401  确保应用加载
from problem import test_cases
from problem.models import Problem
from submission.models import Submission

from . import tasks
from .judger import run_judge
from .models import JudgeServer, Language
from .serializers import LanguageSerializer

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
RUBY = {
    "key": "ruby",
    "name": "Ruby",
    "monaco_id": "ruby",
    "starter_code": "# 在这里写代码\n",
    "compile_config": None,
    "run_config": {
        "command": "/usr/bin/ruby {exe_path}",
        "seccomp_rule": "general",
        "env": ["LANG=C.UTF-8"],
        "exe_name": "solution.rb",
    },
}


def valid_compiled(key="zig"):
    return {
        "key": key,
        "name": "Zig",
        "monaco_id": "plaintext",
        "starter_code": "",
        "compile_config": {
            "src_name": "main.zig",
            "exe_name": "main",
            "max_cpu_time": 5000,
            "max_real_time": 10000,
            "max_memory": 256 * 1024 * 1024,
            "compile_command": "/usr/bin/zig build-exe {src_path} -femit-bin={exe_path}",
        },
        "run_config": {"command": "{exe_path}", "seccomp_rule": "c_cpp", "env": ["LANG=C.UTF-8"]},
    }


@override_settings(CACHES=LOCMEM_CACHE)
class LanguageAdminApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user("admin1", password="x", role=User.Role.ADMIN)
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)

    def client_for(self, user=None):
        client = APIClient()
        if user:
            client.force_authenticate(user)
        return client

    def test_admin_lists_all_including_disabled(self):
        Language.objects.filter(key="java").update(enabled=False)
        keys = [item["key"] for item in self.client_for(self.admin).get("/api/admin/languages").json()["data"]]
        self.assertEqual(keys, ["c", "cpp", "java", "python"])

    def test_teachers_cannot_manage_languages(self):
        self.assertEqual(self.client_for(self.teacher).get("/api/admin/languages").status_code, 403)
        self.assertEqual(self.client_for(self.teacher).post("/api/admin/languages", RUBY, format="json").status_code, 403)

    def test_create_interpreted_language(self):
        response = self.client_for(self.admin).post("/api/admin/languages", RUBY, format="json")

        self.assertEqual(response.status_code, 201)
        ruby = Language.objects.get(key="ruby")
        self.assertIsNone(ruby.compile_config)
        self.assertEqual(ruby.judge_config()["run"]["command"], RUBY["run_config"]["command"])
        self.assertEqual(ruby.judge_config()["run"]["exe_name"], "solution.rb")
        self.assertEqual(ruby.judge_config()["run"]["env"], RUBY["run_config"]["env"])
        self.assertNotIn("compile", ruby.judge_config())

    def test_create_compiled_language_and_it_appears_publicly(self):
        self.assertEqual(self.client_for(self.admin).post("/api/admin/languages", valid_compiled(), format="json").status_code, 201)
        public = [lang["key"] for lang in self.client_for().get("/api/site").json()["data"]["languages"]]
        self.assertIn("zig", public)

    def test_validation_messages(self):
        cases = [
            ({"key": "Bad Key"}, "key"),
            ({"key": "c"}, "已存在"),
            ({"compile_config": {"src_name": "x"}}, "缺少编译配置项"),
            ({"compile_config": "gcc"}, "编译配置应为对象"),
            ({"compile_config": {**valid_compiled()["compile_config"], "max_cpu_time": 0}}, "编译时间上限必须大于 0"),
            ({"compile_config": {**valid_compiled()["compile_config"], "max_memory": 0}}, "编译内存上限"),
            ({"run_config": {"command": "", "seccomp_rule": None, "env": []}}, "运行命令不能为空"),
            ({"run_config": {"command": "x", "env": ["NOEQUALS"]}}, "环境变量"),
            ({"run_config": {"command": "x", "memory_limit_check_only": 2}}, "只能是 0 或 1"),
        ]
        for overrides, message in cases:
            with self.subTest(overrides=list(overrides)):
                payload = {**valid_compiled(key="zig2"), **overrides}
                response = self.client_for(self.admin).post("/api/admin/languages", payload, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, response.json()["message"])

    def test_key_cannot_change_but_other_fields_can(self):
        java = Language.objects.get(key="java")
        response = self.client_for(self.admin).patch(
            f"/api/admin/languages/{java.id}", {"key": "java2", "name": "Java 21", "enabled": False, "sort_order": 9}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        java.refresh_from_db()
        self.assertEqual((java.key, java.name, java.enabled, java.sort_order), ("java", "Java 21", False, 9))

    def test_no_delete(self):
        java = Language.objects.get(key="java")
        self.assertEqual(self.client_for(self.admin).delete(f"/api/admin/languages/{java.id}").status_code, 405)

    def test_run_config_is_normalised(self):
        payload = {**RUBY, "run_config": {"command": " /usr/bin/ruby {exe_path} ", "seccomp_rule": "", "env": [], "exe_name": "a.rb"}}
        serializer = LanguageSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["run_config"]["command"], "/usr/bin/ruby {exe_path}")
        self.assertIsNone(serializer.validated_data["run_config"]["seccomp_rule"])


@override_settings(CACHES=LOCMEM_CACHE, JUDGE_SERVER_TOKEN="t")
class LanguageJudgingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.tmp = tempfile.mkdtemp()
        override = override_settings(TEST_CASE_DIR=self.tmp)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.user = User.objects.create_user("20260001", password="x", role=User.Role.STUDENT)
        self.problem = Problem.objects.create(
            title="A+B", description="d", is_public=True, test_case_id=test_cases.save_test_cases([("1 2\n", "3\n")])
        )
        self.server = JudgeServer.objects.create(
            hostname="judge-server", url="http://judge-server:8080", cpu_core=4, last_heartbeat=timezone.now()
        )

    def submission(self, language, code="puts 1"):
        return Submission.objects.create(user=self.user, problem=self.problem, language=language, code=code)

    def test_new_language_reaches_judge_payload(self):
        Language.objects.create(**RUBY)
        with mock.patch("judge.judger.request_judge", return_value=[]) as request_judge:
            run_judge(self.submission("ruby"), self.server)

        payload = request_judge.call_args.args[1]
        self.assertEqual(payload["language_config"], {"run": RUBY["run_config"]})
        self.assertEqual(payload["language_config"]["run"]["exe_name"], "solution.rb")

    def test_compiled_language_payload_includes_compile(self):
        Language.objects.create(**valid_compiled())
        with mock.patch("judge.judger.request_judge", return_value=[]) as request_judge:
            run_judge(self.submission("zig"), self.server)
        self.assertIn("compile", request_judge.call_args.args[1]["language_config"])

    def test_deleted_language_is_system_error_without_retry(self):
        submission = self.submission("cpp")
        Language.objects.filter(key="cpp").delete()
        with mock.patch("judge.judger.request_judge") as request_judge:
            outcome = run_judge(submission, self.server)

        request_judge.assert_not_called()
        self.assertEqual(outcome.result, "SE")
        self.assertIn("不存在", outcome.error_info)

    def test_java_out_of_memory_rule_follows_language_key(self):
        java = self.submission("java")
        oom = 'Exception in thread "main" java.lang.OutOfMemoryError: Java heap space'
        case = {"test_case": "1", "result": 4, "cpu_time": 1, "memory": 1024, "exit_code": 1, "signal": 0, "output": oom}
        with mock.patch("judge.judger.request_judge", return_value=[dict(case)]):
            self.assertEqual(run_judge(java, self.server).result, "MLE")
        with mock.patch("judge.judger.request_judge", return_value=[dict(case)]):
            self.assertEqual(run_judge(self.submission("python", "x"), self.server).result, "RE")


class InterpretedLanguageTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin1", password="x", role=User.Role.ADMIN)

    def test_interpreted_language_needs_source_name(self):
        payload = {**RUBY, "run_config": {k: v for k, v in RUBY["run_config"].items() if k != "exe_name"}}
        response = APIClient()
        response.force_authenticate(self.admin)
        self.assertEqual(response.post("/api/admin/languages", payload, format="json").status_code, 400)

        payload["run_config"]["exe_name"] = "../etc/x.rb"
        self.assertEqual(response.post("/api/admin/languages", payload, format="json").status_code, 400)

        payload["run_config"]["exe_name"] = "solution.rb"
        self.assertEqual(response.post("/api/admin/languages", payload, format="json").status_code, 201)
        self.assertEqual(Language.objects.get(key="ruby").run_config["exe_name"], "solution.rb")

    def test_partial_update_keeps_compiled_language_valid(self):
        java = Language.objects.get(key="java")
        response = APIClient()
        response.force_authenticate(self.admin)
        # 只改运行命令，不带编译配置：仍按已保存的编译配置判断，不要求源文件名
        payload = {"run_config": {**java.run_config, "command": java.run_config["command"]}}
        self.assertEqual(response.patch(f"/api/admin/languages/{java.id}", payload, format="json").status_code, 200)
