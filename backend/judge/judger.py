"""
单次评测：组装请求、调用判题服务器、汇总结果（设计说明书 8.1 第 4–8 步）。
任务调度、重试与判题机选择见 judge/tasks.py。
"""

import math
import re

from django.db.models import Count, Q
from django.utils import timezone

from problem import test_cases
from problem.models import Problem
from submission.models import Submission

from .client import CompileError, request_judge
from .models import Language

Result = Submission.Result

# Judger 的结果码
_JUDGER_RESULTS = {
    0: Result.AC,
    -1: Result.WA,
    1: Result.TLE,  # CPU 时间超限
    2: Result.TLE,  # 实际运行时间超限（如 sleep、等待输入）
    3: Result.MLE,
    4: Result.RE,
    5: Result.SE,
}

_MAX_ERROR_INFO = 10000
# 编译信息中的临时目录，如 /judger/run/<32 位十六进制>/main.cpp
_JUDGER_PATH_RE = re.compile(r"/judger/run/[0-9a-f]{32}/")
# 只对不太大的输出做逐行比对，避免超大输出占用内存
_MAX_RECHECK_SIZE = 16 * 1024 * 1024


class JudgeOutcome:
    def __init__(self, result, time_cost=None, memory_cost=None, case_info=None, error_info=""):
        self.result = result
        self.time_cost = time_cost
        self.memory_cost = memory_cost
        self.case_info = case_info or []
        self.error_info = error_info


def build_source(problem, language, code):
    """模板题拼接固定的前后代码（M8）；普通题原样返回。"""
    template = (problem.template_code or {}).get(language) if problem.is_template else None
    if not template:
        return code
    return "\n".join([template.get("prepend", ""), code, template.get("append", "")])


def request_timeout(problem, case_count, cpu_core):
    """
    等待判题服务器返回的最长时间：编译至多 20 秒；测试点按 CPU 核数并行，
    每个测试点的实际运行时间上限为时间限制的 3 倍。
    """
    rounds = math.ceil(max(case_count, 1) / max(cpu_core, 1))
    return 30 + rounds * problem.time_limit * 3 / 1000


def clean_compile_error(message):
    return _JUDGER_PATH_RE.sub("", message or "")[:_MAX_ERROR_INFO]


def normalize_output(data):
    """忽略每行行末空白和末尾空行（设计说明书 8.1 第 7 步）。"""
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="replace")
    lines = [line.rstrip() for line in data.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def recheck_wrong_answers(raw_cases, test_case_id):
    """
    JudgeServer 只去掉整个输出末尾的空白再比对，行末多一个空格就会判为答案错误。
    这里对答案错误的测试点按逐行忽略行末空白重新比对。
    """
    info = None
    for case in raw_cases:
        output = case.get("output")
        if case["result"] != -1 or output is None or len(output) > _MAX_RECHECK_SIZE:
            continue
        info = info or test_cases.load_info(test_case_id)
        expected = test_cases.read_expected_output(test_case_id, case["test_case"], info)
        if normalize_output(output) == normalize_output(expected):
            case["result"] = 0


def mark_java_out_of_memory(raw_cases):
    """Java 堆用尽时抛出 OutOfMemoryError 并以非 0 退出，Judger 判为运行错误，这里改为超出内存限制。"""
    for case in raw_cases:
        if case["result"] == 4 and "java.lang.OutOfMemoryError" in (case.get("output") or ""):
            case["result"] = 3


def summarize(raw_cases, partial_score):
    """
    汇总各测试点结果：
    - 全部通过为 AC；任一测试点系统错误则为 SE，便于管理员重判；
    - 按比例给分且部分通过时为 PAC；
    - 否则取第一个未通过测试点的结果。
    """
    case_info = [
        {
            "case": int(case["test_case"]),
            "result": _JUDGER_RESULTS.get(case["result"], Result.SE),
            "time": case["cpu_time"],
            "memory": case["memory"] // 1024,
            "exit_code": case["exit_code"],
            "signal": case["signal"],
        }
        for case in raw_cases
    ]
    case_info.sort(key=lambda case: case["case"])

    failed = [case for case in case_info if case["result"] != Result.AC]
    if not failed:
        result = Result.AC
    elif any(case["result"] == Result.SE for case in failed):
        result = Result.SE
    elif partial_score and len(failed) < len(case_info):
        result = Result.PAC
    else:
        result = failed[0]["result"]

    return JudgeOutcome(
        result=result,
        time_cost=max((case["time"] for case in case_info), default=0),
        memory_cost=max((case["memory"] for case in case_info), default=0),
        case_info=case_info,
    )


def _language_config(key):
    """语言的判题配置；语言已被删除时返回 None。"""
    language = Language.objects.filter(key=key).first()
    return language.judge_config() if language else None


def run_judge(submission, server):
    """把提交发给判题服务器评测，返回 JudgeOutcome。服务器异常时抛出 JudgeServerError。"""
    problem = submission.problem
    try:
        info = test_cases.load_info(problem.test_case_id)
    except (ValueError, OSError):
        # 数据问题，重试无用，直接判为系统错误
        return JudgeOutcome(Result.SE, error_info=f"题目 {problem.id} 的测试数据缺失或损坏")
    language_config = _language_config(submission.language)
    if language_config is None:
        # 语言已被删除，重试无用
        return JudgeOutcome(Result.SE, error_info=f"语言 {submission.language} 不存在，无法评测")
    payload = {
        "language_config": language_config,
        "src": build_source(problem, submission.language, submission.code),
        "max_cpu_time": problem.time_limit,
        "max_memory": problem.memory_limit * 1024 * 1024,
        "test_case_id": problem.test_case_id,
        # 取回用户输出，用于逐行忽略行末空白的二次比对
        "output": True,
    }
    timeout = request_timeout(problem, info["test_case_number"], server.cpu_core)
    try:
        raw_cases = request_judge(server.url, payload, timeout)
    except CompileError as exc:
        return JudgeOutcome(Result.CE, error_info=clean_compile_error(exc.message))

    recheck_wrong_answers(raw_cases, problem.test_case_id)
    if submission.language == "java":
        mark_java_out_of_memory(raw_cases)
    return summarize(raw_cases, submission.uses_partial_score)


def save_outcome(submission, outcome):
    submission.result = outcome.result
    submission.time_cost = outcome.time_cost
    submission.memory_cost = outcome.memory_cost
    submission.case_info = outcome.case_info
    submission.error_info = outcome.error_info
    submission.judged_at = timezone.now() if submission.is_finished else None
    submission.save(
        update_fields=["result", "time_cost", "memory_cost", "case_info", "error_info", "judged_at"]
    )


def update_problem_statistics(problem_id):
    """按提交记录重新统计题目的提交数与通过数；重判时也能保持准确。"""
    stats = Submission.objects.filter(problem_id=problem_id).aggregate(
        total=Count("id"), accepted=Count("id", filter=Q(result=Result.AC))
    )
    Problem.objects.filter(pk=problem_id).update(
        submission_count=stats["total"], accepted_count=stats["accepted"]
    )


def on_judged(submission):
    """评测完成后的统计更新（设计说明书 8.1 第 8 步）。"""
    from classroom import scoring as assignment_scoring
    from contest import scoring as exam_scoring
    from stats.cache import bump_user_classes

    update_problem_statistics(submission.problem_id)
    # 属于作业时重算该学生的作业成绩（每题取最高得分，迟交按比例扣分）
    assignment_scoring.on_submission_judged(submission)
    # 属于考试时重算考试成绩，并使 Redis 中的排名缓存失效
    exam_scoring.on_submission_judged(submission)
    # 练习提交也影响知识点掌握度
    bump_user_classes(submission.user_id)
    # TODO(M1)：用户做题统计
