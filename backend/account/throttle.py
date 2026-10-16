"""
账号安全：连续 5 次凭据错误后锁定 10 分钟（设计说明书 10.1）。

登录与绑定学号共用。计数以键名区分，例如 login:<用户名>、bind:<用户编号>。
锁定窗口从第一次失败开始计时，到期自动解除；登录成功后清零。
"""

from django.core.cache import cache

from utils.exceptions import BusinessError

MAX_FAILURES = 5
LOCK_SECONDS = 10 * 60


def _key(scope, identifier):
    return f"auth-fail:{scope}:{str(identifier).lower()}"


def ensure_not_locked(scope, identifier):
    if (cache.get(_key(scope, identifier)) or 0) >= MAX_FAILURES:
        raise BusinessError("失败次数过多，账号已临时锁定，请 10 分钟后再试")


def record_failure(scope, identifier):
    key = _key(scope, identifier)
    # add 只在键不存在时写入，因此锁定窗口从第一次失败开始，不会被后续失败延长
    cache.add(key, 0, timeout=LOCK_SECONDS)
    try:
        cache.incr(key)
    except ValueError:
        # 键刚好在两步之间过期，重新计数
        cache.set(key, 1, timeout=LOCK_SECONDS)


def clear(scope, identifier):
    cache.delete(_key(scope, identifier))
