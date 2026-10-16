import hashlib
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from account.models import User

from .dispatcher import acquire_judge_server
from .models import HEARTBEAT_TIMEOUT, JudgeServer

TOKEN = "test-judge-token"
TOKEN_HEADER = hashlib.sha256(TOKEN.encode()).hexdigest()
HEARTBEAT_URL = "/api/judge-server/heartbeat"


def heartbeat_payload(**overrides):
    # 与 QDUOJ JudgeServer service.py 发送的字段一致
    payload = {
        "hostname": "3ce65dad33de",
        "judger_version": "2.1.1",
        "cpu_core": 4,
        "cpu": 12.5,
        "memory": 50.7,
        "action": "heartbeat",
        "service_url": "http://judge-server:8080",
    }
    payload.update(overrides)
    return payload


def make_server(**fields):
    defaults = {"hostname": "h", "cpu_core": 1, "last_heartbeat": timezone.now()}
    defaults.update(fields)
    return JudgeServer.objects.create(**defaults)


@override_settings(JUDGE_SERVER_TOKEN=TOKEN)
class HeartbeatTests(APITestCase):
    def post(self, payload, token=TOKEN_HEADER):
        return self.client.post(
            HEARTBEAT_URL, payload, format="json", HTTP_X_JUDGE_SERVER_TOKEN=token
        )

    def test_first_heartbeat_registers_server(self):
        response = self.post(heartbeat_payload())

        self.assertEqual(response.status_code, 200)
        # JudgeServer 只认 {"error": null, ...}，不能是统一响应格式
        self.assertEqual(response.json(), {"error": None, "data": None})
        server = JudgeServer.objects.get()
        self.assertEqual(server.url, "http://judge-server:8080")
        self.assertEqual(server.cpu_core, 4)
        self.assertEqual(server.ip, "127.0.0.1")
        self.assertTrue(server.is_alive)

    def test_heartbeat_updates_existing_server_by_url(self):
        self.post(heartbeat_payload())
        # 容器重建后主机名变化，服务地址不变（末尾斜杠也视为同一地址）
        self.post(heartbeat_payload(hostname="new-container", cpu=80, service_url="http://judge-server:8080/"))

        server = JudgeServer.objects.get()
        self.assertEqual(server.hostname, "new-container")
        self.assertEqual(server.cpu_usage, 80)

    def test_heartbeat_keeps_task_count_and_enabled_flag(self):
        self.post(heartbeat_payload())
        JudgeServer.objects.update(task_count=3, is_enabled=False)
        self.post(heartbeat_payload())

        server = JudgeServer.objects.get()
        self.assertEqual(server.task_count, 3)
        self.assertFalse(server.is_enabled)

    def test_wrong_token_rejected(self):
        response = self.post(heartbeat_payload(), token="wrong")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "invalid-token")
        self.assertFalse(JudgeServer.objects.exists())

    def test_missing_and_non_ascii_token_rejected(self):
        self.assertEqual(self.client.post(HEARTBEAT_URL, heartbeat_payload(), format="json").status_code, 403)
        self.assertEqual(self.post(heartbeat_payload(), token="令牌").status_code, 403)

    @override_settings(JUDGE_SERVER_TOKEN="")
    def test_unconfigured_token_rejects_everything(self):
        empty_hash = hashlib.sha256(b"").hexdigest()
        with self.assertLogs("judge.views", "ERROR"):
            response = self.post(heartbeat_payload(), token=empty_hash)
        self.assertEqual(response.status_code, 403)

    def test_invalid_payload_uses_qduoj_error_format(self):
        response = self.post(heartbeat_payload(cpu_core="many", service_url="judge-server:8080"))

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["error"], "invalid-data")
        self.assertIn("cpu_core", body["data"])
        self.assertIn("service_url", body["data"])

    def test_malformed_json_uses_qduoj_error_format(self):
        response = self.client.post(
            HEARTBEAT_URL, "{bad", content_type="application/json", HTTP_X_JUDGE_SERVER_TOKEN=TOKEN_HEADER
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid-data")


class AliveAndDispatchTests(TestCase):
    def test_alive_excludes_stale_and_disabled_servers(self):
        alive = make_server(url="http://a")
        make_server(url="http://stale", last_heartbeat=timezone.now() - HEARTBEAT_TIMEOUT - timedelta(seconds=1))
        make_server(url="http://disabled", is_enabled=False)

        self.assertEqual(list(JudgeServer.objects.alive()), [alive])

    def test_acquire_picks_least_loaded_and_releases(self):
        make_server(url="http://busy", task_count=1)
        idle = make_server(url="http://idle", task_count=0)

        with acquire_judge_server() as server:
            self.assertEqual(server, idle)
            idle.refresh_from_db()
            self.assertEqual(idle.task_count, 1)
        idle.refresh_from_db()
        self.assertEqual(idle.task_count, 0)

    def test_acquire_releases_on_exception(self):
        server = make_server(url="http://a")
        with self.assertRaises(RuntimeError):
            with acquire_judge_server():
                raise RuntimeError
        server.refresh_from_db()
        self.assertEqual(server.task_count, 0)

    def test_acquire_skips_full_servers(self):
        make_server(url="http://full", cpu_core=1, task_count=2)
        with acquire_judge_server() as server:
            self.assertIsNone(server)

    def test_acquire_without_servers_returns_none(self):
        make_server(url="http://stale", last_heartbeat=timezone.now() - timedelta(minutes=5))
        with acquire_judge_server() as server:
            self.assertIsNone(server)


class AdminJudgeServerApiTests(APITestCase):
    def setUp(self):
        self.server = make_server(url="http://judge-server:8080", cpu_core=4)
        self.admin = User.objects.create_user("admin1", password="x", role=User.Role.ADMIN)
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_admin_lists_servers_with_status(self):
        response = self.client_for(self.admin).get("/api/admin/judge-servers")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        [item] = body["data"]
        self.assertTrue(item["is_alive"])
        self.assertEqual(item["max_task_count"], 8)

    def test_admin_can_disable_but_not_edit_other_fields(self):
        url = f"/api/admin/judge-servers/{self.server.id}"
        response = self.client_for(self.admin).patch(url, {"is_enabled": False, "task_count": 99}, format="json")

        self.assertEqual(response.status_code, 200)
        self.server.refresh_from_db()
        self.assertFalse(self.server.is_enabled)
        self.assertEqual(self.server.task_count, 0)

    def test_admin_can_delete(self):
        response = self.client_for(self.admin).delete(f"/api/admin/judge-servers/{self.server.id}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(JudgeServer.objects.exists())

    def test_teacher_and_anonymous_forbidden(self):
        self.assertEqual(self.client_for(self.teacher).get("/api/admin/judge-servers").status_code, 403)
        self.assertEqual(APIClient().get("/api/admin/judge-servers").status_code, 401)
