import io
import os
import time
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from rest_framework.test import APIClient, APITestCase

from account.models import User

from . import fps, test_cases
from .models import Problem
from .tests import TempTestCaseDirMixin

FPS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<fps version="1.2">
  <generator name="HUSTOJ" url="https://github.com/zhblue/hustoj/"/>
  <item>
    <title><![CDATA[A+B Problem]]></title>
    <time_limit unit="s"><![CDATA[0.5]]></time_limit>
    <memory_limit unit="mb"><![CDATA[128]]></memory_limit>
    <img><src><![CDATA[/upload/ab.png]]></src><base64><![CDATA[iVBORw0K
Gg==]]></base64></img>
    <description><![CDATA[<p>计算 a+b</p><img src="/upload/ab.png">]]></description>
    <input><![CDATA[两个整数]]></input>
    <output><![CDATA[它们的和]]></output>
    <sample_input><![CDATA[1 2]]></sample_input>
    <sample_output><![CDATA[3]]></sample_output>
    <test_input><![CDATA[1 2
]]></test_input>
    <test_output><![CDATA[3
]]></test_output>
    <test_input><![CDATA[100 200
]]></test_input>
    <test_output><![CDATA[300
]]></test_output>
    <hint><![CDATA[注意负数]]></hint>
    <source><![CDATA[经典题]]></source>
    <solution language="C"><![CDATA[int main(){}]]></solution>
  </item>
  <item>
    <title><![CDATA[Special Judge]]></title>
    <time_limit unit="ms">1000</time_limit>
    <description>x</description>
    <spj language="C"><![CDATA[int main(){}]]></spj>
  </item>
  <item>
    <title>No Data</title>
    <time_limit unit="s">100</time_limit>
    <memory_limit unit="kb">65536</memory_limit>
    <description>y</description>
  </item>
</fps>
"""


class ParseFPSTests(TempTestCaseDirMixin, APITestCase):
    def test_parse(self):
        problems = fps.parse_fps(io.BytesIO(FPS_XML.encode()))

        ab, spj, no_data = problems
        self.assertEqual((ab.title, ab.time_limit, ab.memory_limit), ("A+B Problem", 500, 128))
        self.assertEqual(ab.samples, [{"input": "1 2", "output": "3"}])
        self.assertEqual(ab.test_cases, [("1 2\n", "3\n"), ("100 200\n", "300\n")])
        self.assertIn('<img src="data:image/png;base64,iVBORw0KGg==">', ab.description)
        self.assertEqual((ab.hint, ab.source), ("注意负数", "经典题"))
        self.assertEqual(ab.warnings, [])

        self.assertEqual(spj.skip_reason, "特判（spj）题目暂不支持")

        # 100 秒超出范围被调整；65536 KB = 64 MB
        self.assertEqual((no_data.time_limit, no_data.memory_limit), (10000, 64))
        self.assertTrue(any("超出范围" in w for w in no_data.warnings))
        self.assertTrue(any("没有测试数据" in w for w in no_data.warnings))

    def test_invalid_files(self):
        for content, message in [
            (b"not xml", "不是有效的 FPS 文件"),
            (b"<problems/>", "根元素应为 <fps>"),
            (b"<fps></fps>", "没有题目"),
        ]:
            with self.subTest(content=content), self.assertRaisesMessage(fps.FPSError, message):
                fps.parse_fps(io.BytesIO(content))

    def test_entity_expansion_is_rejected(self):
        bomb = b"""<?xml version="1.0"?><!DOCTYPE fps [<!ENTITY a "aaaaaaaaaa">
            <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;"><!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">
            <!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;"><!ENTITY e "&d;&d;&d;&d;&d;&d;&d;&d;&d;&d;">
            <!ENTITY f "&e;&e;&e;&e;&e;&e;&e;&e;&e;&e;"><!ENTITY g "&f;&f;&f;&f;&f;&f;&f;&f;&f;&f;">
            <!ENTITY h "&g;&g;&g;&g;&g;&g;&g;&g;&g;&g;"><!ENTITY i "&h;&h;&h;&h;&h;&h;&h;&h;&h;&h;">
            ]><fps><item><title>&i;</title></item></fps>"""
        with self.assertRaises(fps.FPSError):
            fps.parse_fps(io.BytesIO(bomb))


class FPSImportApiTests(TempTestCaseDirMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        self.client = APIClient()
        self.client.force_authenticate(self.teacher)

    def upload(self, content):
        file = SimpleUploadedFile("problems.xml", content, "text/xml")
        return self.client.post("/api/admin/problems/import-fps", {"file": file}, format="multipart")

    def test_import(self):
        response = self.upload(FPS_XML.encode())

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual([item["title"] for item in data["created"]], ["A+B Problem", "No Data"])
        self.assertEqual(data["skipped"], [{"title": "Special Judge", "reason": "特判（spj）题目暂不支持"}])
        self.assertEqual(data["created"][0]["test_case_count"], 2)

        ab = Problem.objects.get(title="A+B Problem")
        self.assertEqual(ab.created_by, self.teacher)
        self.assertFalse(ab.is_public)
        self.assertEqual(test_cases.read_expected_output(ab.test_case_id, 2), b"300\n")
        self.assertEqual(Problem.objects.get(title="No Data").test_case_id, "")

    def test_failure_rolls_back_everything(self):
        with mock.patch.object(Problem.objects, "create", side_effect=[mock.DEFAULT, RuntimeError("db down")]):
            with self.assertRaises(RuntimeError):
                self.upload(FPS_XML.encode())
        self.assertEqual(Problem.objects.count(), 0)
        self.assertEqual(self.stored_ids(), [])

    def test_bad_file(self):
        response = self.upload(b"<html></html>")
        self.assertEqual(response.status_code, 400)
        self.assertIn("根元素应为 <fps>", response.json()["message"])


class CleanupCommandTests(TempTestCaseDirMixin, APITestCase):
    def test_removes_only_old_unused_directories(self):
        used = test_cases.save_test_cases([("1", "1")])
        Problem.objects.create(title="p", description="", test_case_id=used)
        old_unused = test_cases.save_test_cases([("1", "1")])
        new_unused = test_cases.save_test_cases([("1", "1")])
        two_days_ago = time.time() - 48 * 3600
        for test_case_id in (used, old_unused):
            os.utime(test_cases.test_case_dir(test_case_id), (two_days_ago, two_days_ago))

        call_command("cleanup_test_cases", "--dry-run", stdout=io.StringIO())
        self.assertEqual(len(self.stored_ids()), 3)

        call_command("cleanup_test_cases", stdout=io.StringIO())
        self.assertEqual(sorted(self.stored_ids()), sorted([used, new_unused]))
