from rest_framework import serializers

from .models import JudgeServer, Language

COMPILE_KEYS = {
    "src_name": str,
    "exe_name": str,
    "compile_command": str,
    "max_cpu_time": int,
    "max_real_time": int,
    "max_memory": int,
}


class HeartbeatSerializer(serializers.Serializer):
    """JudgeServer 上报的心跳数据（字段名由 QDUOJ JudgeServer 决定）。"""

    hostname = serializers.CharField(max_length=128)
    judger_version = serializers.CharField(max_length=32)
    cpu_core = serializers.IntegerField(min_value=1)
    cpu = serializers.FloatField(min_value=0)
    memory = serializers.FloatField(min_value=0)
    # 不用 URLField：容器内地址如 http://judge-server:8080 没有顶级域名，过不了 URL 校验
    service_url = serializers.CharField(max_length=255)
    action = serializers.CharField(required=False)

    def validate_service_url(self, value):
        if not value.startswith(("http://", "https://")):
            raise serializers.ValidationError("服务地址必须以 http:// 或 https:// 开头")
        return value.rstrip("/")


class JudgeServerSerializer(serializers.ModelSerializer):
    is_alive = serializers.BooleanField(read_only=True)
    max_task_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = JudgeServer
        fields = [
            "id",
            "hostname",
            "url",
            "ip",
            "judger_version",
            "cpu_core",
            "cpu_usage",
            "memory_usage",
            "task_count",
            "max_task_count",
            "last_heartbeat",
            "is_enabled",
            "is_alive",
            "created_at",
        ]
        read_only_fields = [f for f in fields if f != "is_enabled"]


class LanguageSerializer(serializers.ModelSerializer):
    """
    编程语言。key 创建后不可修改。编译配置为空表示解释执行。
    编译配置与运行配置的字段直接对应 JudgeServer 的请求格式，错误在保存前给出。
    """

    class Meta:
        model = Language
        fields = [
            "id",
            "key",
            "name",
            "enabled",
            "sort_order",
            "monaco_id",
            "starter_code",
            "compile_config",
            "run_config",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]
        extra_kwargs = {"starter_code": {"allow_blank": True}}

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            fields["key"].read_only = True
        return fields

    def validate_key(self, value):
        if Language.objects.filter(key=value).exists():
            raise serializers.ValidationError("该标识已存在")
        return value

    def validate_compile_config(self, value):
        if value in (None, {}):
            return None
        if not isinstance(value, dict):
            raise serializers.ValidationError("编译配置应为对象或留空")
        for key, kind in COMPILE_KEYS.items():
            if key not in value:
                raise serializers.ValidationError(f"缺少编译配置项：{key}")
            if not isinstance(value[key], kind) or isinstance(value[key], bool):
                raise serializers.ValidationError(f"编译配置项 {key} 类型不正确")
        if not value["compile_command"].strip() or not value["src_name"].strip():
            raise serializers.ValidationError("编译命令与源文件名不能为空")
        if value["max_cpu_time"] <= 0 or value["max_real_time"] <= 0:
            raise serializers.ValidationError("编译时间上限必须大于 0")
        if value["max_memory"] == 0 or value["max_memory"] < -1:
            raise serializers.ValidationError("编译内存上限应为正数，或 -1 表示不限制")
        return value

    def validate_run_config(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("运行配置应为对象")
        command = value.get("command")
        if not isinstance(command, str) or not command.strip():
            raise serializers.ValidationError("运行命令不能为空")
        if value.get("seccomp_rule") is not None and not isinstance(value.get("seccomp_rule"), str):
            raise serializers.ValidationError("系统调用白名单应为文字或留空")
        env = value.get("env", [])
        if not isinstance(env, list) or not all(isinstance(item, str) and "=" in item for item in env):
            raise serializers.ValidationError("环境变量应为 名称=值 的列表")
        check = value.get("memory_limit_check_only", 0)
        if check not in (0, 1):
            raise serializers.ValidationError("memory_limit_check_only 只能是 0 或 1")
        result = {
            "command": command.strip(),
            "seccomp_rule": value.get("seccomp_rule") or None,
            "env": env,
            "memory_limit_check_only": check,
        }
        # 解释执行时 JudgeServer 把源代码写到 exe_name 指定的文件再直接运行，因此必须给出文件名
        exe_name = value.get("exe_name")
        # 部分更新时可能不带编译配置，此时沿用已保存的配置判断
        if "compile_config" in self.initial_data:
            compile_config = self.initial_data["compile_config"]
        else:
            compile_config = getattr(self.instance, "compile_config", None)
        if compile_config in (None, {}):
            if not isinstance(exe_name, str) or not exe_name.strip() or "/" in exe_name:
                raise serializers.ValidationError("解释执行的语言需要源文件名（不含路径）")
            result["exe_name"] = exe_name.strip()
        elif exe_name:
            result["exe_name"] = exe_name
        return result

