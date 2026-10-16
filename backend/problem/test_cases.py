"""
测试数据存储。目录结构与 QDUOJ JudgeServer 约定一致（判题容器以只读方式挂载同一目录）：

    TEST_CASE_DIR/<test_case_id>/
        1.in  1.out  2.in  2.out ...
        info    {"test_case_number": n, "spj": false, "test_cases": {"1": {...}, ...}}

JudgeServer 用 info 中的 stripped_output_md5 比对输出，缺少该文件会判为系统错误。
"""

import hashlib
import json
import os
import re
import shutil
import uuid
import zipfile
import zlib
from pathlib import Path, PurePosixPath

from django.conf import settings

_TEST_CASE_ID_RE = re.compile(r"^[0-9a-f]{32}$")

# 上传限制
MAX_ZIP_SIZE = 100 * 1024 * 1024
MAX_TOTAL_SIZE = 512 * 1024 * 1024
MAX_CASES = 200


class TestCaseError(ValueError):
    """测试数据压缩包不符合要求，消息可直接展示给教师。"""


def test_case_dir(test_case_id):
    # 编号直接拼进路径，必须校验，防止目录穿越
    if not _TEST_CASE_ID_RE.match(test_case_id or ""):
        raise ValueError(f"非法的测试数据编号：{test_case_id!r}")
    return Path(settings.TEST_CASE_DIR) / test_case_id


def _to_bytes(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    # Windows 下编辑的数据统一为 \n 换行
    return data.replace(b"\r\n", b"\n")


def save_test_cases(cases):
    """
    保存一组测试数据，返回新的 test_case_id。

    cases: 可迭代的 (输入, 输出)，str 或 bytes；逐组读取写入，不会一次性载入全部数据。
    """
    test_case_id = uuid.uuid4().hex
    directory = test_case_dir(test_case_id)
    directory.mkdir(parents=True)
    os.chmod(directory, 0o755)

    try:
        info = {"test_case_number": 0, "spj": False, "test_cases": {}}
        for index, (input_data, output_data) in enumerate(cases, start=1):
            input_data, output_data = _to_bytes(input_data), _to_bytes(output_data)
            input_name, output_name = f"{index}.in", f"{index}.out"
            for name, data in ((input_name, input_data), (output_name, output_data)):
                path = directory / name
                path.write_bytes(data)
                os.chmod(path, 0o644)
            info["test_cases"][str(index)] = {
                "input_name": input_name,
                "input_size": len(input_data),
                "output_name": output_name,
                "output_size": len(output_data),
                "output_md5": hashlib.md5(output_data).hexdigest(),
                "stripped_output_md5": hashlib.md5(output_data.rstrip()).hexdigest(),
            }
        info["test_case_number"] = len(info["test_cases"])

        info_path = directory / "info"
        info_path.write_text(json.dumps(info), encoding="utf-8")
        os.chmod(info_path, 0o644)
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    return test_case_id


def load_info(test_case_id):
    return json.loads((test_case_dir(test_case_id) / "info").read_text(encoding="utf-8"))


def read_expected_output(test_case_id, case_id, info=None):
    info = info or load_info(test_case_id)
    output_name = info["test_cases"][str(case_id)]["output_name"]
    return (test_case_dir(test_case_id) / output_name).read_bytes()


def _natural_key(name):
    # 1, 2, 10 而不是 1, 10, 2
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]


def _scan_zip(archive):
    """校验压缩包结构，返回按名称自然排序的 [(名称, 输入成员, 输出成员)]，此时尚未解压任何数据。"""
    members = {".in": {}, ".out": {}}
    total_size = 0
    for member in archive.infolist():
        if member.is_dir():
            continue
        path = PurePosixPath(member.filename.replace("\\", "/"))
        if "__MACOSX" in path.parts or path.name.startswith("."):
            continue
        suffix = path.suffix.lower()
        if suffix not in members:
            continue
        if path.stem in members[suffix]:
            raise TestCaseError(f"文件 {path.stem}{suffix} 重复出现")
        members[suffix][path.stem] = member
        total_size += member.file_size
        if total_size > MAX_TOTAL_SIZE:
            raise TestCaseError(f"解压后的测试数据超过 {MAX_TOTAL_SIZE // 1024 // 1024}MB")

    inputs, outputs = members[".in"], members[".out"]
    if not inputs and not outputs:
        raise TestCaseError("压缩包中没有 .in / .out 文件")
    for missing, suffix in ((inputs.keys() - outputs.keys(), ".out"), (outputs.keys() - inputs.keys(), ".in")):
        if missing:
            names = "、".join(f"{name}{suffix}" for name in sorted(missing, key=_natural_key)[:5])
            raise TestCaseError(f"缺少对应的文件：{names}")
    if len(inputs) > MAX_CASES:
        raise TestCaseError(f"测试点不能超过 {MAX_CASES} 组")

    return [(name, inputs[name], outputs[name]) for name in sorted(inputs, key=_natural_key)]


def save_test_cases_from_zip(file):
    """
    从上传的 zip 保存测试数据，返回 (test_case_id, 原文件名列表)。

    压缩包中每组数据为同名的 .in 与 .out（如 1.in / 1.out），可以放在子目录中；
    按名称自然排序后重新编号为 1、2、3……。格式不符时抛出 TestCaseError。
    """
    try:
        archive = zipfile.ZipFile(file)
    except (zipfile.BadZipFile, OSError):
        raise TestCaseError("不是有效的 zip 压缩包")

    with archive:
        pairs = _scan_zip(archive)
        try:
            test_case_id = save_test_cases(
                (archive.read(input_member), archive.read(output_member)) for _, input_member, output_member in pairs
            )
        except (zipfile.BadZipFile, zlib.error, EOFError) as exc:
            raise TestCaseError("压缩包已损坏，无法解压") from exc
        except (RuntimeError, NotImplementedError) as exc:
            # 加密或使用了不支持的压缩算法
            raise TestCaseError(f"无法解压：{exc}") from exc
    return test_case_id, [name for name, _, _ in pairs]
