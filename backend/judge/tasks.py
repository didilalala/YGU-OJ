"""
判题任务（M5），流程见设计说明书第八章。

提交接口写入 submission（状态 PENDING）后调用 enqueue_judge() 投递任务并立即返回；
Celery 工作进程执行 judge_submission：选择判题服务器 → 状态改为 JUDGING → 评测 → 回写结果。
"""

import logging

from celery import shared_task
from django.db import transaction

from submission.models import Submission

from .dispatcher import acquire_judge_server
from .judger import JudgeOutcome, on_judged, run_judge, save_outcome

logger = logging.getLogger(__name__)

Result = Submission.Result

# 评测失败（判题服务器异常、超时等）的重试次数，仍失败则判为系统错误
MAX_FAILURE_RETRIES = 3
# 重试间隔 5、10、20 秒，合计超过心跳超时（30 秒）：判题服务器重启时，
# 重试期间它会被判为离线，任务转入等待可用服务器，而不是直接判为系统错误
FAILURE_RETRY_BASE_DELAY = 5
# 没有可用判题服务器（全部离线或满载）时的等待：每 5 秒重试，最多等 5 分钟
NO_SERVER_RETRY_DELAY = 5
MAX_NO_SERVER_RETRIES = 60


def enqueue_judge(submission):
    """在当前事务提交后投递判题任务，避免工作进程读到尚未入库的提交。"""
    submission_id = submission.pk
    transaction.on_commit(lambda: judge_submission.delay(submission_id))


def rejudge(submission):
    """重判：清空上次结果后重新投递。"""
    save_outcome(submission, JudgeOutcome(Result.PENDING))
    enqueue_judge(submission)


def _finish(submission, outcome):
    save_outcome(submission, outcome)
    on_judged(submission)
    logger.info("提交 #%s 评测完成：%s", submission.pk, outcome.result)


# 两类重试分别计数（failures、waits），由任务参数传递，因此不使用 Celery 自带的 max_retries。
# 重试时必须同时传 args：Celery 会沿用原来的位置参数，只传 kwargs 会导致 submission_id 重复。
@shared_task(bind=True, max_retries=None)
def judge_submission(self, submission_id, failures=0, waits=0):
    submission = Submission.objects.select_related("problem").filter(pk=submission_id).first()
    if submission is None:
        logger.warning("提交 #%s 不存在，跳过评测", submission_id)
        return

    with acquire_judge_server() as server:
        if server is None:
            if waits >= MAX_NO_SERVER_RETRIES:
                _finish(submission, JudgeOutcome(Result.SE, error_info="没有可用的判题服务器"))
                return
            raise self.retry(
                args=[submission_id],
                kwargs={"failures": failures, "waits": waits + 1},
                countdown=NO_SERVER_RETRY_DELAY,
            )

        Submission.objects.filter(pk=submission_id).update(result=Result.JUDGING)
        try:
            outcome = run_judge(submission, server)
        except Exception as exc:
            if failures < MAX_FAILURE_RETRIES:
                logger.warning("提交 #%s 第 %s 次评测失败，稍后重试：%s", submission_id, failures + 1, exc)
                Submission.objects.filter(pk=submission_id).update(result=Result.PENDING)
                raise self.retry(
                    exc=exc,
                    args=[submission_id],
                    kwargs={"failures": failures + 1, "waits": waits},
                    countdown=FAILURE_RETRY_BASE_DELAY * 2**failures,
                ) from exc
            logger.exception("提交 #%s 评测失败 %s 次，判为系统错误", submission_id, failures + 1)
            outcome = JudgeOutcome(Result.SE, error_info=f"{type(exc).__name__}: {exc}")

    _finish(submission, outcome)
