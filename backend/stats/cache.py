"""
统计结果缓存（设计说明书 9.4：统计结果缓存在 Redis，有新提交时失效重算）。

每个班级一个版本号，统计结果的缓存键包含版本号。成绩重算、学生导入与移出、
作业或考试增删改时调用 bump_class，旧缓存自然失效，不必逐个删除。
"""

from django.core.cache import cache
from django.db import transaction

CACHE_TIMEOUT = 10 * 60


def _version_key(class_id):
    return f"stats_version:{class_id}"


def class_version(class_id):
    key = _version_key(class_id)
    cache.add(key, 1, timeout=None)
    return cache.get(key) or 1


def bump_class(class_id):
    """在当前事务提交后使班级的统计缓存失效。"""
    if not class_id:
        return

    def bump():
        key = _version_key(class_id)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 2, timeout=None)

    transaction.on_commit(bump)


def bump_user_classes(user_id):
    """学生的提交评测完成后，使其所在全部班级的统计失效（练习提交也影响知识点掌握度）。"""
    # classroom 的计分模块导入了本模块，放在函数内导入以避免循环导入
    from classroom.models import ClassMember

    for class_id in ClassMember.objects.active().filter(student_id=user_id).values_list("class_group_id", flat=True):
        bump_class(class_id)


def cached(class_id, name, compute):
    key = f"stats:{class_id}:{class_version(class_id)}:{name}"
    return cache.get_or_set(key, compute, CACHE_TIMEOUT)
