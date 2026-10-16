from datetime import timedelta

from django.db import models
from django.utils import timezone

# JudgeServer 容器每 5 秒上报一次心跳，超过该时长未上报则不再分配任务
HEARTBEAT_TIMEOUT = timedelta(seconds=30)


class JudgeServerQuerySet(models.QuerySet):
    def alive(self):
        """已启用且心跳正常的判题服务器。"""
        return self.filter(is_enabled=True, last_heartbeat__gte=timezone.now() - HEARTBEAT_TIMEOUT)


class JudgeServer(models.Model):
    """
    判题服务器，由心跳自动注册。

    以服务地址 url 作为唯一标识：容器重建后主机名会变，而服务地址不变。
    """

    hostname = models.CharField("主机名", max_length=128)
    url = models.CharField("服务地址", max_length=255, unique=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    judger_version = models.CharField("Judger 版本", max_length=32, blank=True)
    cpu_core = models.PositiveSmallIntegerField("CPU 核数", default=1)
    cpu_usage = models.FloatField("CPU 使用率（%）", default=0)
    memory_usage = models.FloatField("内存使用率（%）", default=0)
    task_count = models.IntegerField("当前任务数", default=0)
    last_heartbeat = models.DateTimeField("最近心跳")
    is_enabled = models.BooleanField("是否启用", default=True)
    created_at = models.DateTimeField("注册时间", auto_now_add=True)

    objects = JudgeServerQuerySet.as_manager()

    class Meta:
        db_table = "judge_server"
        ordering = ["id"]
        verbose_name = verbose_name_plural = "判题服务器"

    def __str__(self):
        return f"{self.hostname} ({self.url})"

    @property
    def is_alive(self):
        return timezone.now() - self.last_heartbeat <= HEARTBEAT_TIMEOUT

    @property
    def max_task_count(self):
        """同时评测的任务上限，与 JudgeServer 的工作进程数（CPU 核数）相当。"""
        return self.cpu_core * 2


class Language(models.Model):
    """
    支持的编程语言（M6 系统配置）。编译与运行配置直接对应 JudgeServer 的请求格式，
    见 judge.client；编译配置为空表示解释执行，无需编译。

    停用后学生不能再选该语言提交，但已有提交仍可重判，因此不提供删除。
    """

    key = models.SlugField("标识", max_length=32, unique=True, help_text="提交时使用的语言标识，如 cpp")
    name = models.CharField("名称", max_length=64)
    enabled = models.BooleanField("启用", default=True)
    sort_order = models.PositiveIntegerField("排序", default=0)
    monaco_id = models.CharField("编辑器语言", max_length=32, help_text="代码编辑器的语法高亮，如 cpp、python")
    starter_code = models.TextField("初始代码", blank=True)
    compile_config = models.JSONField("编译配置", null=True, blank=True)
    run_config = models.JSONField("运行配置")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "language"
        ordering = ["sort_order", "id"]
        verbose_name = verbose_name_plural = "编程语言"

    def __str__(self):
        return self.name

    def judge_config(self):
        """JudgeServer 请求中的 language_config。"""
        config = {"run": self.run_config}
        if self.compile_config:
            config["compile"] = self.compile_config
        return config
