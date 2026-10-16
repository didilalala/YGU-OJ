from io import BytesIO
from urllib.parse import quote

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from classroom.views import managed_assignments, managed_classes
from contest.access import ensure_not_locked
from contest.views import managed_exams
from utils.permissions import IsTeacherOrAdmin

from .export import build_class_workbook
from .knowledge import class_knowledge
from .overview import admin_overview
from .service import class_overview, my_scores, work_stats


class OverviewView(APIView):
    """后台仪表盘：班级与学生数、进行中的作业和考试、近 14 天提交趋势、需要关注的作业。"""

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        return Response(admin_overview(request.user))


class ClassStatsView(APIView):
    """班级总览：各次作业与考试的平均得分率、提交率，以及学生排名。"""

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, pk):
        class_group = managed_classes(request.user).filter(pk=pk).first()
        if class_group is None:
            raise NotFound("班级不存在")
        return Response(class_overview(class_group))


class AssignmentStatsView(APIView):
    """作业统计：成绩分布、各题满分率与错误类型、未提交名单。"""

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, pk):
        assignment = managed_assignments(request.user).filter(pk=pk).first()
        if assignment is None:
            raise NotFound("作业不存在")
        return Response(work_stats(assignment))


class ExamStatsView(APIView):
    """考试统计，内容同作业统计。"""

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, pk):
        exam = managed_exams(request.user).filter(pk=pk).first()
        if exam is None:
            raise NotFound("考试不存在")
        return Response(work_stats(exam))


class ClassExportView(APIView):
    """导出班级成绩单（.xlsx），返回文件本身，不经统一响应格式。"""

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, pk):
        class_group = managed_classes(request.user).filter(pk=pk).first()
        if class_group is None:
            raise NotFound("班级不存在")
        buffer = BytesIO()
        build_class_workbook(class_group).save(buffer)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = quote(f"{class_group.name}成绩单_{timezone.localdate():%Y%m%d}.xlsx")
        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{filename}"
        return response


class ClassKnowledgeView(APIView):
    """班级知识点掌握度：各知识点的班级平均掌握度与通过率、最薄弱的知识点、每名学生的掌握度。"""

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, pk):
        class_group = managed_classes(request.user).filter(pk=pk).first()
        if class_group is None:
            raise NotFound("班级不存在")
        return Response(class_knowledge(class_group))


class MyScoresView(APIView):
    """个人成绩、学习曲线与知识点掌握度。"""

    def get(self, request):
        ensure_not_locked(request.user)
        return Response({"classes": my_scores(request.user)})
