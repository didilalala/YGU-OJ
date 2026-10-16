"""
网站参数（设计说明书 M6）：站点信息、开放策略、提交限制、题目默认值。

参数集中定义在 SETTINGS 中，包括类型、默认值、取值范围与说明；管理员只能修改已定义的参数，
修改时按定义校验。读取时先取数据库中的值，没有保存过的参数使用默认值。
"""

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from judge.models import Language

from .models import SiteSetting


@dataclass(frozen=True)
class Setting:
    key: str
    label: str
    group: str
    kind: str  # text | bool | int
    default: object
    description: str = ""
    max_length: int = 0  # text 用
    min_length: int = 0  # text 用
    min_value: int = 0  # int 用
    max_value: int = 0  # int 用
    multiline: bool = False


SETTINGS = [
    Setting("site_name", "网站名称", "站点", "text", "阳光学院在线评测平台", "显示在首页横幅", max_length=64, min_length=1),
    Setting("home_announcement", "首页公告", "站点", "text", "", "显示在首页横幅下方，留空则不显示", max_length=2000, multiline=True),
    Setting("allow_registration", "允许普通用户注册", "开放策略", "bool", True, "关闭后登录页不再显示注册入口，已有账号不受影响"),
    Setting(
        "submit_interval_seconds",
        "提交间隔（秒）",
        "提交限制",
        "int",
        5,
        "同一用户两次提交之间的最短间隔，0 表示不限制",
        min_value=0,
        max_value=300,
    ),
    Setting("max_code_kb", "代码长度上限（KB）", "提交限制", "int", 64, "单次提交的代码最大长度", min_value=1, max_value=1024),
    Setting(
        "default_time_limit_ms",
        "新题默认时间限制（毫秒）",
        "题目默认值",
        "int",
        1000,
        "新建题目时的默认值，教师仍可修改",
        min_value=100,
        max_value=10000,
    ),
    Setting(
        "default_memory_limit_mb",
        "新题默认内存限制（MB）",
        "题目默认值",
        "int",
        256,
        "新建题目时的默认值，教师仍可修改",
        min_value=16,
        max_value=1024,
    ),
]
_BY_KEY = {s.key: s for s in SETTINGS}


def stored_values():
    return {row.key: row.value for row in SiteSetting.objects.all()}


def values():
    """所有参数的当前值：已保存的覆盖默认值。"""
    stored = stored_values()
    return {s.key: stored.get(s.key, s.default) for s in SETTINGS}


def get(key):
    return values()[key]


def _validate(setting, value):
    if setting.kind == "bool":
        if not isinstance(value, bool):
            raise ValueError("应为是或否")
        return value
    if setting.kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("应为整数")
        if not setting.min_value <= value <= setting.max_value:
            raise ValueError(f"应在 {setting.min_value}–{setting.max_value} 之间")
        return value
    if not isinstance(value, str):
        raise ValueError("应为文字")
    value = value.strip()
    if len(value) < setting.min_length:
        raise ValueError("不能为空")
    if len(value) > setting.max_length:
        raise ValueError(f"不能超过 {setting.max_length} 个字符")
    return value


def update(user, changes):
    """批量修改参数，任何一项不合法则全部不保存。返回 (错误字典, 当前值)。"""
    errors, clean = {}, {}
    for key, value in changes.items():
        setting = _BY_KEY.get(key)
        if setting is None:
            errors[key] = "未知的参数"
            continue
        try:
            clean[key] = _validate(setting, value)
        except ValueError as exc:
            errors[key] = str(exc)
    if errors:
        return errors, None
    with transaction.atomic():
        for key, value in clean.items():
            SiteSetting.objects.update_or_create(
                key=key, defaults={"value": value, "updated_by": user, "updated_at": timezone.now()}
            )
    return {}, values()


def definitions():
    """供管理页面展示：定义 + 当前值 + 默认值。"""
    current = values()
    return [
        {
            "key": s.key,
            "label": s.label,
            "group": s.group,
            "kind": s.kind,
            "description": s.description,
            "default": s.default,
            "value": current[s.key],
            "max_length": s.max_length,
            "min_length": s.min_length,
            "min_value": s.min_value,
            "max_value": s.max_value,
            "multiline": s.multiline,
        }
        for s in SETTINGS
    ]


def public_languages():
    """学生提交与编辑器需要的已启用语言。"""
    return [
        {"key": lang.key, "name": lang.name, "monaco_id": lang.monaco_id, "starter_code": lang.starter_code}
        for lang in Language.objects.filter(enabled=True)
    ]


def public_payload():
    """访客也能读取的站点信息。"""
    current = values()
    return {"settings": current, "languages": public_languages()}
