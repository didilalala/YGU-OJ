import shutil
import tempfile
from datetime import timedelta
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from account.models import User
from classroom.models import Assignment, AssignmentProblem, ClassGroup, ScoreRecord
from problem import test_cases
from problem.models import Problem
from submission.models import Submission

from . import tasks
from .client import CompileError, JudgeServerError
from .judger import build_source, clean_compile_error, normalize_output, request_timeout, summarize
from .models import JudgeServer

Result = Submission.Result


def raw_case(case, result=0, output="", cpu_time=10, memory=2 * 1024 * 1024):
    """JudgeServer /judge 返回的单个测试点结果。"""
    return {
        "test_case": str(case),
        "result": result,
        "cpu_time": cpu_time,
        "real_time": cpu_time,
        "memory": memory,
        "exit_code": 0,
        "signal": 0,
        "error": 0,
        "output_md5": None,
        "output": output,
    }


class SummarizeTests(SimpleTestCase):
    def test_all_passed(self):
        outcome = summarize([raw_case(2, cpu_time=30, memory=4 << 20), raw_case(1, cpu_time=50)], False)

        self.assertEqual(outcome.result, Result.AC)
        self.assertEqual(outcome.time_cost, 50)
        self.assertEqual(outcome.memory_cost, 4096)
        self.assertEqual([case["case"] for case in outcome.case_info], [1, 2])

    def test_first_failed_case_decides_result(self):
        cases = [raw_case(3, result=1), raw_case(1), raw_case(2, result=-1)]
        self.assertEqual(summarize(cases, False).result, Result.WA)

    def test_partial_score_gives_pac(self):
        cases = [raw_case(1), raw_case(2, result=-1)]
        self.assertEqual(summarize(cases, True).result, Result.PAC)
        # 一个都没通过时仍是具体错误
        self.assertEqual(summarize([raw_case(1, result=4)], True).result, Result.RE)

    def test_system_error_wins(self):
        cases = [raw_case(1, result=-1), raw_case(2, result=5)]
        self.assertEqual(summarize(cases, True).result, Result.SE)

    def test_real_time_limit_is_tle(self):
        self.assertEqual(summarize([raw_case(1, result=2)], False).result, Result.TLE)


class HelperTests(SimpleTestCase):
    def test_normalize_output_ignores_trailing_whitespace_per_line(self):
        self.assertEqual(normalize_output("1 2 \r\n3\t\n\n\n"), normalize_output(b"1 2\n3"))
        self.assertNotEqual(normalize_output("1  2\n"), normalize_output("1 2\n"))
        self.assertNotEqual(normalize_output("\n1\n"), normalize_output("1\n"))

    def test_build_source_for_template_problem(self):
        problem = Problem(
            is_template=True,
            template_code={"c": {"prepend": "#include <stdio.h>", "template": "int add(int a, int b) {}", "append": "int main(){}"}},
        )
        self.assertEqual(build_source(problem, "c", "int add(){}"), "#include <stdio.h>\nint add(){}\nint main(){}")
        # 未配置该语言模板、或不是模板题时原样评测
        self.assertEqual(build_source(problem, "python", "x"), "x")
        problem.is_template = False
        self.assertEqual(build_source(problem, "c", "x"), "x")

    def test_clean_compile_error_hides_sandbox_path(self):
        message = "/judger/run/51651e2f27a2415fa958c2ecace71be9/main.cpp:1:18: error: expected"
        self.assertEqual(clean_compile_error(message), "main.cpp:1:18: error: expected")

    def test_request_timeout_grows_with_cases(self):
        problem = Problem(time_limit=2000)
        self.assertEqual(request_timeout(problem, 4, 4), 36)
        self.assertEqual(request_timeout(problem, 10, 4), 48)
class JudgeTaskTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.override = override_settings(TEST_CASE_DIR=self.tmp, JUDGE_SERVER_TOKEN="t")
        self.override.enable()

        self.user = User.objects.create_user("20260001", password="x", role=User.Role.STUDENT)
        self.problem = Problem.objects.create(
            title="A+B",
            description="",
            test_case_id=test_cases.save_test_cases([("1 2\n", "3\n"), ("1 1\n", "1 1\n2\n")]),
        )
        self.server = JudgeServer.objects.create(
            hostname="judge-server", url="http://judge-server:8080", cpu_core=4, last_heartbeat=timezone.now()
        )
        patcher = mock.patch("judge.judger.request_judge")
        self.request_judge = patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.tmp)

    def submit(self, **fields):
        fields = {"user": self.user, "problem": self.problem, "language": "cpp", "code": "int main(){}", **fields}
        return Submission.objects.create(**fields)

    def judge(self, submission):
        tasks.judge_submission.apply(args=[submission.id])
        submission.refresh_from_db()
        return submission

    def test_accepted_submission_is_saved_and_counted(self):
        self.request_judge.return_value = [raw_case(1, output="3\n", cpu_time=12), raw_case(2, output="1 1\n2\n")]
        submission = self.judge(self.submit())

        self.assertEqual(submission.result, Result.AC)
        self.assertEqual(submission.time_cost, 12)
        self.assertEqual(len(submission.case_info), 2)
        self.assertIsNotNone(submission.judged_at)
        self.problem.refresh_from_db()
        self.assertEqual((self.problem.submission_count, self.problem.accepted_count), (1, 1))
        # 判题机名额已释放
        self.server.refresh_from_db()
        self.assertEqual(self.server.task_count, 0)

        url, payload, timeout = self.request_judge.call_args.args
        self.assertEqual(url, "http://judge-server:8080")
        self.assertEqual(payload["test_case_id"], self.problem.test_case_id)
        self.assertEqual(payload["max_memory"], 256 * 1024 * 1024)
        self.assertTrue(payload["output"])

    def test_trailing_spaces_are_accepted(self):
        # JudgeServer 因行末空格判为 WA（-1），二次比对后改为通过
        self.request_judge.return_value = [raw_case(1, output="3 \n"), raw_case(2, result=-1, output="1 1 \n2  \n\n")]
        self.assertEqual(self.judge(self.submit()).result, Result.AC)

    def test_real_wrong_answer_stays_wrong(self):
        self.request_judge.return_value = [raw_case(1, output="3\n"), raw_case(2, result=-1, output="1 1\n3\n")]
        submission = self.judge(self.submit())

        self.assertEqual(submission.result, Result.WA)
        self.problem.refresh_from_db()
        self.assertEqual((self.problem.submission_count, self.problem.accepted_count), (1, 0))

    def test_assignment_submission_gets_partial_result_and_score(self):
        teacher = User.objects.create_user("t1", password="x", role=User.Role.TEACHER)
        klass = ClassGroup.objects.create(name="班", teacher=teacher)
        now = timezone.now()
        assignment = Assignment.objects.create(
            class_group=klass, title="作业", start_time=now - timedelta(hours=1), end_time=now + timedelta(hours=1)
        )
        AssignmentProblem.objects.create(assignment=assignment, problem=self.problem, score=40)
        self.request_judge.return_value = [raw_case(1, output="3\n"), raw_case(2, result=-1, output="x\n")]
        submission = self.judge(self.submit(assignment=assignment))

        self.assertEqual(submission.result, Result.PAC)
        self.assertEqual(submission.passed_ratio, 0.5)
        # 评测完成后自动计入作业成绩：40 分 × 通过一半
        record = ScoreRecord.objects.get(student=self.user, assignment=assignment)
        self.assertEqual((record.score, record.solved_count), (20, 0))

    def test_java_out_of_memory_is_mle(self):
        oom = 'Exception in thread "main" java.lang.OutOfMemoryError: Java heap space'
        # 每次返回新列表：评测会就地修改测试点结果
        self.request_judge.side_effect = lambda *args: [raw_case(1, output="3\n"), raw_case(2, result=4, output=oom)]
        self.assertEqual(self.judge(self.submit(language="java")).result, Result.MLE)
        # 其他语言的输出不做此判断
        self.assertEqual(self.judge(self.submit(language="python")).result, Result.RE)

    def test_compile_error(self):
        self.request_judge.side_effect = CompileError("/judger/run/" + "a" * 32 + "/main.cpp: error: x")
        submission = self.judge(self.submit())

        self.assertEqual(submission.result, Result.CE)
        self.assertEqual(submission.error_info, "main.cpp: error: x")

    def test_template_code_is_sent(self):
        self.problem.is_template = True
        self.problem.template_code = {"cpp": {"prepend": "// head", "append": "// tail"}}
        self.problem.save()
        self.request_judge.return_value = [raw_case(1, output="3\n"), raw_case(2, output="1 1\n2\n")]
        self.judge(self.submit(code="int f(){}"))

        self.assertEqual(self.request_judge.call_args.args[1]["src"], "// head\nint f(){}\n// tail")

    def test_server_errors_retry_three_times_then_system_error(self):
        self.request_judge.side_effect = JudgeServerError("connection refused")
        with self.assertLogs("judge.tasks", "WARNING"):
            submission = self.judge(self.submit())

        self.assertEqual(self.request_judge.call_count, 1 + tasks.MAX_FAILURE_RETRIES)
        self.assertEqual(submission.result, Result.SE)
        self.assertIn("connection refused", submission.error_info)
        self.server.refresh_from_db()
        self.assertEqual(self.server.task_count, 0)

    def test_recovers_after_transient_failure(self):
        self.request_judge.side_effect = [
            JudgeServerError("timeout"),
            [raw_case(1, output="3\n"), raw_case(2, output="1 1\n2\n")],
        ]
        with self.assertLogs("judge.tasks", "WARNING"):
            submission = self.judge(self.submit())
        self.assertEqual(submission.result, Result.AC)

    def test_waits_for_judge_server_then_system_error(self):
        self.server.delete()
        with mock.patch.object(tasks, "MAX_NO_SERVER_RETRIES", 2):
            submission = self.judge(self.submit())

        self.request_judge.assert_not_called()
        self.assertEqual(submission.result, Result.SE)
        self.assertEqual(submission.error_info, "没有可用的判题服务器")

    def test_missing_test_cases_is_system_error_without_retry(self):
        self.problem.test_case_id = ""
        self.problem.save()
        submission = self.judge(self.submit())

        self.request_judge.assert_not_called()
        self.assertEqual(submission.result, Result.SE)

    def test_rejudge_resets_and_judges_again(self):
        self.request_judge.return_value = [raw_case(1, output="3\n"), raw_case(2, result=-1, output="0\n")]
        submission = self.judge(self.submit())
        self.assertEqual(submission.result, Result.WA)

        self.request_judge.return_value = [raw_case(1, output="3\n"), raw_case(2, output="1 1\n2\n")]
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            tasks.rejudge(submission)
        submission.refresh_from_db()
        self.assertEqual(submission.result, Result.PENDING)
        self.assertIsNone(submission.judged_at)
        self.assertEqual(len(callbacks), 1)

        self.assertEqual(self.judge(submission).result, Result.AC)
        self.problem.refresh_from_db()
        self.assertEqual((self.problem.submission_count, self.problem.accepted_count), (1, 1))

    def test_enqueue_waits_for_commit(self):
        submission = self.submit()
        with mock.patch.object(tasks.judge_submission, "delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                tasks.enqueue_judge(submission)
                delay.assert_not_called()
        delay.assert_called_once_with(submission.id)

    def test_missing_submission_is_skipped(self):
        with self.assertLogs("judge.tasks", "WARNING"):
            tasks.judge_submission.apply(args=[999999])
        self.request_judge.assert_not_called()


class SeededLanguageTests(TestCase):
    def test_seeded_languages_have_judge_config(self):
        # 迁移中写入的四种语言都有完整的判题配置
        from .models import Language

        for key in ("c", "cpp", "java", "python"):
            with self.subTest(key=key):
                config = Language.objects.get(key=key).judge_config()
                self.assertIn("run", config)
                self.assertIn("compile", config)
