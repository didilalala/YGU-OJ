import shutil
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from problem import test_cases
from problem.models import Problem


class Command(BaseCommand):
    help = "删除未被任何题目引用的测试数据（上传后未保存题目、FPS 导入失败等遗留的目录）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours", type=float, default=24, help="只删除早于该时长的目录，避免误删刚上传、尚未保存题目的数据（默认 24）"
        )
        parser.add_argument("--dry-run", action="store_true", help="只列出，不删除")

    def handle(self, hours, dry_run, **options):
        root = Path(settings.TEST_CASE_DIR)
        if not root.is_dir():
            return
        used = set(Problem.objects.exclude(test_case_id="").values_list("test_case_id", flat=True))
        deadline = time.time() - hours * 3600

        removed = 0
        for directory in root.iterdir():
            try:
                test_cases.test_case_dir(directory.name)
            except ValueError:
                continue  # 不是测试数据目录（如 .gitkeep）
            if directory.name in used or directory.stat().st_mtime > deadline:
                continue
            self.stdout.write(f"{'将删除' if dry_run else '删除'} {directory.name}")
            if not dry_run:
                shutil.rmtree(directory, ignore_errors=True)
            removed += 1
        self.stdout.write(self.style.SUCCESS(f"共 {removed} 个未使用的测试数据目录"))
