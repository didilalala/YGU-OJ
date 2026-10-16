from django.db import migrations, models

# 初始语言配置：与迁移前写在代码里的配置一致（编译器版本以判题镜像 judge:1.6.1 为准）。
# 迁移中保存字面量，之后即使代码变化，历史迁移的结果也不会改变。
_ENV = ["LANG=en_US.UTF-8", "LANGUAGE=en_US:en", "LC_ALL=en_US.UTF-8"]
_MB = 1024 * 1024
_C_CPP_RUN = {"command": "{exe_path}", "seccomp_rule": "c_cpp", "env": _ENV}

SEED = [
    {
        "key": "c",
        "name": "C",
        "monaco_id": "c",
        "starter_code": '#include <stdio.h>\n\nint main(void) {\n    \n    return 0;\n}\n',
        "compile_config": {
            "src_name": "main.c",
            "exe_name": "main",
            "max_cpu_time": 3000,
            "max_real_time": 10000,
            "max_memory": 256 * _MB,
            "compile_command": "/usr/bin/gcc -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c11 {src_path} -lm -o {exe_path}",
        },
        "run_config": _C_CPP_RUN,
    },
    {
        "key": "cpp",
        "name": "C++",
        "monaco_id": "cpp",
        "starter_code": "#include <iostream>\nusing namespace std;\n\nint main() {\n    \n    return 0;\n}\n",
        "compile_config": {
            "src_name": "main.cpp",
            "exe_name": "main",
            "max_cpu_time": 10000,
            "max_real_time": 20000,
            "max_memory": 1024 * _MB,
            "compile_command": "/usr/bin/g++ -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c++17 {src_path} -lm -o {exe_path}",
        },
        "run_config": _C_CPP_RUN,
    },
    {
        # JVM 需要的系统调用很多，QDUOJ 对 Java 不启用 seccomp，网络隔离依赖 docker-compose 的内部网络。
        # 堆默认只有 MaxRAM 的 25%，256MB 的题目仅 64MB 堆；调到 75%，其余留给 JVM 自身。
        # 默认的 G1 会让 1MB 左右的大数组各占两个区域，实际可用堆减半；单线程评测用 Serial GC 更省内存。
        "key": "java",
        "name": "Java",
        "monaco_id": "java",
        "starter_code": (
            "import java.util.*;\n\n// 类名必须为 Main\npublic class Main {\n    public static void main(String[] args) {\n"
            "        Scanner in = new Scanner(System.in);\n        \n    }\n}\n"
        ),
        "compile_config": {
            "src_name": "Main.java",
            "exe_name": "Main",
            "max_cpu_time": 5000,
            "max_real_time": 10000,
            "max_memory": -1,
            "compile_command": "/usr/bin/javac {src_path} -d {exe_dir} -encoding UTF8",
        },
        "run_config": {
            "command": "/usr/bin/java -cp {exe_dir} -XX:MaxRAM={max_memory}k -XX:MaxRAMPercentage=75 "
            "-XX:+UseSerialGC -Dfile.encoding=UTF-8 -Djava.awt.headless=true Main",
            "seccomp_rule": None,
            "env": _ENV,
            # JVM 预留的虚拟内存远大于实际使用，只按实际占用判断是否超内存
            "memory_limit_check_only": 1,
        },
    },
    {
        "key": "python",
        "name": "Python 3",
        "monaco_id": "python",
        "starter_code": "",
        "compile_config": {
            "src_name": "solution.py",
            "exe_name": "__pycache__/solution.cpython-312.pyc",
            "max_cpu_time": 3000,
            "max_real_time": 10000,
            "max_memory": 128 * _MB,
            "compile_command": "/usr/bin/python3 -m py_compile {src_path}",
        },
        "run_config": {
            "command": "/usr/bin/python3 -BS {exe_path}",
            "seccomp_rule": "general",
            "env": _ENV + ["PYTHONIOENCODING=utf-8"],
        },
    },
]


def seed_languages(apps, schema_editor):
    Language = apps.get_model("judge", "Language")
    for order, data in enumerate(SEED, start=1):
        Language.objects.update_or_create(key=data["key"], defaults={**data, "sort_order": order, "enabled": True})


class Migration(migrations.Migration):
    dependencies = [("judge", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Language",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(help_text="提交时使用的语言标识，如 cpp", max_length=32, unique=True, verbose_name="标识")),
                ("name", models.CharField(max_length=64, verbose_name="名称")),
                ("enabled", models.BooleanField(default=True, verbose_name="启用")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="排序")),
                ("monaco_id", models.CharField(help_text="代码编辑器的语法高亮，如 cpp、python", max_length=32, verbose_name="编辑器语言")),
                ("starter_code", models.TextField(blank=True, verbose_name="初始代码")),
                ("compile_config", models.JSONField(blank=True, null=True, verbose_name="编译配置")),
                ("run_config", models.JSONField(verbose_name="运行配置")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "编程语言",
                "verbose_name_plural": "编程语言",
                "db_table": "language",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.RunPython(seed_languages, migrations.RunPython.noop),
    ]
