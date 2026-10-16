import hashlib
import json
import urllib.request

from django.conf import settings


class JudgeServerError(Exception):
    """判题服务器不可达、超时或返回异常；判题任务会重试。"""


class CompileError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def request_judge(server_url, payload, timeout):
    """
    调用 JudgeServer 的 /judge 接口，返回各测试点的运行结果列表。

    JudgeServer 的响应为 {"err": null | "<异常类名>", "data": ...}。
    """
    token = hashlib.sha256(settings.JUDGE_SERVER_TOKEN.encode()).hexdigest()
    request = urllib.request.Request(
        f"{server_url}/judge",
        data=json.dumps(payload).encode(),
        headers={"X-Judge-Server-Token": token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.load(response)
    except (OSError, ValueError) as exc:  # 连接失败、超时（均为 OSError）或响应不是 JSON
        raise JudgeServerError(f"请求判题服务器 {server_url} 失败：{exc}") from exc

    err, data = body.get("err"), body.get("data")
    if err == "CompileError":
        raise CompileError(data or "")
    if err:
        raise JudgeServerError(f"{err}: {data}")
    return data
