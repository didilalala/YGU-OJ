from contextlib import contextmanager

from django.db import transaction
from django.db.models import F

from .models import JudgeServer


@contextmanager
def acquire_judge_server():
    """
    选出心跳正常、未满载且当前任务数最少的判题服务器，占用一个任务名额，离开时释放。
    没有可用服务器时得到 None，调用方应让任务稍后重试。

        with acquire_judge_server() as server:
            if server is None:
                raise self.retry()
            ...  # 请求 server.url
    """
    server = None
    with transaction.atomic():
        candidates = JudgeServer.objects.alive().select_for_update().order_by("task_count", "id")
        for candidate in candidates:
            if candidate.task_count < candidate.max_task_count:
                JudgeServer.objects.filter(pk=candidate.pk).update(task_count=F("task_count") + 1)
                server = candidate
                break
    try:
        yield server
    finally:
        if server is not None:
            JudgeServer.objects.filter(pk=server.pk).update(task_count=F("task_count") - 1)
