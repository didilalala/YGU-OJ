import hashlib
import io
import shutil
import tempfile
import zipfile
from pathlib import Path
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient, APITestCase

from account.models import User

from . import test_cases

UPLOAD_URL = "/api/admin/problems/test-cases"


def make_zip(files, **zip_kwargs):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", **zip_kwargs) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


class TempTestCaseDirMixin:
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        self.override = override_settings(TEST_CASE_DIR=self.tmp)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.tmp)
        super().tearDown()

    def stored_ids(self):
        return [path.name for path in Path(self.tmp).iterdir()]


class TestCaseStorageTests(TempTestCaseDirMixin, SimpleTestCase):
    def test_save_writes_files_and_qduoj_info(self):
        test_case_id = test_cases.save_test_cases([("1 2\n", "3\n"), (b"5 7\r\n", b"12\r\n\r\n")])

        info = test_cases.load_info(test_case_id)
        self.assertEqual(info["test_case_number"], 2)
        self.assertFalse(info["spj"])
        second = info["test_cases"]["2"]
        self.assertEqual(second["input_name"], "2.in")
        # \r\n 统一为 \n
        self.assertEqual(test_cases.read_expected_output(test_case_id, 2), b"12\n\n")
        self.assertEqual(second["output_size"], 4)
        self.assertEqual(second["stripped_output_md5"], hashlib.md5(b"12").hexdigest())
        self.assertEqual((test_cases.test_case_dir(test_case_id) / "2.in").read_bytes(), b"5 7\n")

    def test_rejects_invalid_ids(self):
        for bad in ("", "../etc", "ABCDEF" * 6, "a" * 31, None):
            with self.assertRaises(ValueError):
                test_cases.test_case_dir(bad)

    def test_failed_save_leaves_nothing_behind(self):
        def cases():
            yield ("1", "1")
            raise OSError("disk full")

        with self.assertRaises(OSError):
            test_cases.save_test_cases(cases())
        self.assertEqual(self.stored_ids(), [])


class ZipImportTests(TempTestCaseDirMixin, SimpleTestCase):
    def save(self, files, **zip_kwargs):
        return test_cases.save_test_cases_from_zip(io.BytesIO(make_zip(files, **zip_kwargs)))

    def assert_rejected(self, files, message):
        with self.assertRaisesMessage(test_cases.TestCaseError, message):
            self.save(files)
        self.assertEqual(self.stored_ids(), [])

    def test_natural_order_and_subdirectories(self):
        test_case_id, names = self.save(
            {
                "data/10.in": "10",
                "data/10.out": "100",
                "data/2.in": "2",
                "data/2.out": "4",
                "data/1.IN": "1",
                "data/1.OUT": "1",
                "data/readme.txt": "ignored",
                "__MACOSX/data/._1.in": "junk",
                "data/.DS_Store": "junk",
            },
            compression=zipfile.ZIP_DEFLATED,
        )
        self.assertEqual(names, ["1", "2", "10"])
        # 按排序重新编号：第 3 组是原来的 10.in
        directory = test_cases.test_case_dir(test_case_id)
        self.assertEqual((directory / "3.in").read_bytes(), b"10")
        self.assertEqual(test_cases.load_info(test_case_id)["test_case_number"], 3)

    def test_windows_style_paths(self):
        _, names = self.save({"case\\a.in": "1", "case\\a.out": "1"})
        self.assertEqual(names, ["a"])

    def test_missing_pair(self):
        self.assert_rejected({"1.in": "1", "1.out": "1", "2.in": "2", "3.out": "3"}, "缺少对应的文件：2.out")

    def test_input_only_special_judge_not_supported(self):
        self.assert_rejected({"1.in": "1"}, "缺少对应的文件：1.out")

    def test_no_test_case_files(self):
        self.assert_rejected({"readme.md": "x"}, "没有 .in / .out 文件")

    def test_duplicate_names_in_different_folders(self):
        self.assert_rejected({"a/1.in": "1", "a/1.out": "1", "b/1.in": "1"}, "重复出现")

    def test_too_many_cases(self):
        with mock.patch.object(test_cases, "MAX_CASES", 2):
            self.assert_rejected({f"{i}.{ext}": "x" for i in range(3) for ext in ("in", "out")}, "不能超过 2 组")

    def test_uncompressed_size_limit(self):
        with mock.patch.object(test_cases, "MAX_TOTAL_SIZE", 10):
            self.assert_rejected({"1.in": "123456", "1.out": "123456"}, "解压后的测试数据超过")

    def test_not_a_zip(self):
        with self.assertRaisesMessage(test_cases.TestCaseError, "不是有效的 zip"):
            test_cases.save_test_cases_from_zip(io.BytesIO(b"plain text"))

    def test_corrupted_member(self):
        data = bytearray(make_zip({"1.in": "a" * 1000, "1.out": "b" * 1000}, compression=zipfile.ZIP_DEFLATED))
        # 破坏第一个成员的压缩数据（本地文件头 30 字节 + 文件名 4 字节之后）
        data[40:60] = b"\xff" * 20
        with self.assertRaisesMessage(test_cases.TestCaseError, "压缩包已损坏"):
            test_cases.save_test_cases_from_zip(io.BytesIO(bytes(data)))
        self.assertEqual(self.stored_ids(), [])


class TestCaseUploadApiTests(TempTestCaseDirMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        self.student = User.objects.create_user("s1", password="x", role=User.Role.STUDENT)

    def upload(self, user, content, name="cases.zip"):
        client = APIClient()
        client.force_authenticate(user)
        data = {} if content is None else {"file": SimpleUploadedFile(name, content, "application/zip")}
        return client.post(UPLOAD_URL, data, format="multipart")

    def test_teacher_uploads_zip(self):
        response = self.upload(self.teacher, make_zip({"1.in": "1 2\n", "1.out": "3\n", "2.in": "", "2.out": "0\n"}))

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertTrue(test_cases.test_case_dir(data["test_case_id"]).is_dir())
        self.assertEqual(
            data["test_cases"],
            [
                {"index": 1, "name": "1", "input_size": 4, "output_size": 2},
                {"index": 2, "name": "2", "input_size": 0, "output_size": 2},
            ],
        )

    def test_invalid_zip_returns_readable_error(self):
        response = self.upload(self.teacher, make_zip({"1.in": "1"}))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "缺少对应的文件：1.out")

    def test_missing_file(self):
        response = self.upload(self.teacher, None)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "file: 请选择测试数据压缩包")

    def test_size_limit(self):
        with mock.patch.object(test_cases, "MAX_ZIP_SIZE", 10):
            response = self.upload(self.teacher, make_zip({"1.in": "1", "1.out": "1"}))
        self.assertEqual(response.status_code, 400)
        self.assertIn("压缩包不能超过", response.json()["message"])

    def test_students_cannot_upload(self):
        response = self.upload(self.student, make_zip({"1.in": "1", "1.out": "1"}))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.stored_ids(), [])
