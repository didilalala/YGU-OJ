"""
FPS（Free Problem Set，HUSTOJ 等系统的题目导出格式）导入。

    <fps version="1.2">
      <item>
        <title>, <time_limit unit="s|ms">, <memory_limit unit="mb|kb">,
        <description>, <input>, <output>, <hint>, <source>,
        <sample_input>/<sample_output>（可多组）, <test_input>/<test_output>（可多组）,
        <img><src>原路径</src><base64>图片数据</base64></img>（可多张）,
        <spj>（特判程序）, <solution>（参考代码，忽略）
      </item>
    </fps>

题面为 HTML，原样保存（前端渲染时统一过滤脚本）；内嵌图片改写为 data URI。
"""

import mimetypes
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field

from .serializers import MEMORY_LIMIT_RANGE, MAX_SAMPLES, TIME_LIMIT_RANGE

MAX_FPS_SIZE = 64 * 1024 * 1024
MAX_FPS_ITEMS = 200


class FPSError(ValueError):
    """FPS 文件无法解析，消息可直接展示给教师。"""


@dataclass
class FPSProblem:
    title: str
    description: str = ""
    input_desc: str = ""
    output_desc: str = ""
    hint: str = ""
    source: str = ""
    time_limit: int = 1000
    memory_limit: int = 256
    samples: list = field(default_factory=list)
    test_cases: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    skip_reason: str = ""


def _text(item, tag):
    node = item.find(tag)
    return (node.text or "").strip() if node is not None else ""


def _clamp(value, value_range, label, warnings):
    low, high = value_range
    clamped = min(max(value, low), high)
    if clamped != value:
        warnings.append(f"{label} {value} 超出范围，已调整为 {clamped}")
    return clamped


def _time_limit_ms(item, warnings):
    node = item.find("time_limit")
    if node is None or not (node.text or "").strip():
        return 1000
    try:
        value = float(node.text.strip())
    except ValueError:
        warnings.append(f"时间限制「{node.text.strip()}」无法识别，使用 1000 毫秒")
        return 1000
    if node.get("unit", "s").lower() != "ms":
        value *= 1000
    return _clamp(round(value), TIME_LIMIT_RANGE, "时间限制（毫秒）", warnings)


def _memory_limit_mb(item, warnings):
    node = item.find("memory_limit")
    if node is None or not (node.text or "").strip():
        return 256
    try:
        value = float(node.text.strip())
    except ValueError:
        warnings.append(f"内存限制「{node.text.strip()}」无法识别，使用 256 MB")
        return 256
    if node.get("unit", "mb").lower() == "kb":
        value /= 1024
    return _clamp(round(value), MEMORY_LIMIT_RANGE, "内存限制（MB）", warnings)


def _pairs(item, input_tag, output_tag):
    inputs = [node.text or "" for node in item.findall(input_tag)]
    outputs = [node.text or "" for node in item.findall(output_tag)]
    return list(zip(inputs, outputs)), len(inputs) != len(outputs)


def _embed_images(item, problem):
    """把题面中引用的图片路径替换为 FPS 内嵌的 base64 数据。"""
    for img in item.findall("img"):
        src, data = _text(img, "src"), "".join(_text(img, "base64").split())
        if not src or not data:
            continue
        mime = mimetypes.guess_type(src)[0] or "image/png"
        data_uri = f"data:{mime};base64,{data}"
        for attr in ("description", "input_desc", "output_desc", "hint"):
            setattr(problem, attr, getattr(problem, attr).replace(src, data_uri))


def _parse_item(item):
    problem = FPSProblem(title=_text(item, "title")[:128])
    if not problem.title:
        problem.title = "（无标题）"
        problem.warnings.append("缺少标题")

    if item.find("spj") is not None:
        problem.skip_reason = "特判（spj）题目暂不支持"
        return problem

    problem.description = _text(item, "description")
    problem.input_desc = _text(item, "input")
    problem.output_desc = _text(item, "output")
    problem.hint = _text(item, "hint")
    problem.source = _text(item, "source")[:128]
    problem.time_limit = _time_limit_ms(item, problem.warnings)
    problem.memory_limit = _memory_limit_mb(item, problem.warnings)

    samples, mismatched = _pairs(item, "sample_input", "sample_output")
    if mismatched:
        problem.warnings.append("样例输入与输出数量不一致，多余的已忽略")
    if len(samples) > MAX_SAMPLES:
        problem.warnings.append(f"样例超过 {MAX_SAMPLES} 组，只保留前 {MAX_SAMPLES} 组")
    problem.samples = [{"input": i, "output": o} for i, o in samples[:MAX_SAMPLES]]

    problem.test_cases, mismatched = _pairs(item, "test_input", "test_output")
    if mismatched:
        problem.warnings.append("测试输入与输出数量不一致，多余的已忽略")
    if not problem.test_cases:
        problem.warnings.append("没有测试数据，导入后需上传测试数据才能提交")

    _embed_images(item, problem)
    return problem


def parse_fps(file):
    """解析 FPS 文件，返回 FPSProblem 列表（含需跳过的题目及原因）。格式错误时抛出 FPSError。"""
    try:
        root = ElementTree.parse(file).getroot()
    except ElementTree.ParseError as exc:
        raise FPSError(f"不是有效的 FPS 文件：{exc}") from exc
    if root.tag != "fps":
        raise FPSError("不是有效的 FPS 文件：根元素应为 <fps>")

    items = root.findall("item")
    if not items:
        raise FPSError("FPS 文件中没有题目")
    if len(items) > MAX_FPS_ITEMS:
        raise FPSError(f"一次最多导入 {MAX_FPS_ITEMS} 道题目")
    return [_parse_item(item) for item in items]
