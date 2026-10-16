import secrets

from django.db.models import Count, OuterRef, ProtectedError, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from classroom.models import ClassMember, ScoreRecord
from stats.cache import bump_class
from submission.models import Submission
from utils.exceptions import BusinessError
from utils.permissions import IsTeacherOrAdmin
from utils.request import get_client_ip

from .access import active_exam, check_ip, student_exam
from .models import Exam, ExamParticipant
from .scoring import exam_rank
from .serializers import AdminExamSerializer, ExamItemSerializer, StudentExamSerializer


def _member_count_subquery():
    return Subquery(
        ClassMember.objects.filter(class_group=OuterRef("class_group"), is_removed=False)
        .values("class_group")
        .annotate(count=Count("id"))
        .values("count")[:1]
    )


def managed_exams(user):
    queryset = (
        Exam.objects.select_related("class_group")
        .prefetch_related("items__problem")
        .annotate(
            participant_count=Count("participants", distinct=True),
            member_count=Coalesce(_member_count_subquery(), 0),
        )
    )
    if user.role != user.Role.ADMIN:
        # 教师管理自己班级的考试，以及自己创建的公开竞赛
        queryset = queryset.filter(Q(class_group__teacher=user) | Q(class_group__isnull=True, created_by=user))
    return queryset


def _get_managed_exam(request, pk):
    exam = managed_exams(request.user).filter(pk=pk).first()
    if exam is None:
        raise NotFound("考试不存在")
    return exam


# ---------------------------------------------------------------- 管理端


class AdminExamListCreateView(generics.ListCreateAPIView):
    """考试列表（可按 class_id 筛选）与创建考试。"""

    permission_classes = [IsTeacherOrAdmin]
    serializer_class = AdminExamSerializer

    def get_queryset(self):
        queryset = managed_exams(self.request.user)
        if self.request.query_params.get("scope") == "public":
            return queryset.filter(class_group__isnull=True)
        class_id = self.request.query_params.get("class_id")
        if class_id:
            if not class_id.isdigit():
                raise ValidationError({"class_id": "必须是整数"})
            queryset = queryset.filter(class_group_id=int(class_id))
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exam = serializer.save()
        return Response(AdminExamSerializer(managed_exams(request.user).get(pk=exam.pk)).data, status=status.HTTP_201_CREATED)


class AdminExamDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = AdminExamSerializer

    def get_object(self):
        return _get_managed_exam(self.request, self.kwargs["pk"])

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(AdminExamSerializer(self.get_object()).data)

    def perform_destroy(self, exam):
        bump_class(exam.class_group_id)
        try:
            exam.delete()
        except ProtectedError:
            raise BusinessError("已有学生提交，不能删除；如需隐藏请取消发布")


class ExamMonitorView(APIView):
    """
    监考：班级每名学生的考试状态（未进入 / 考试中 / 已交卷）、进入 IP、提交数与成绩，以及排名。
    公开竞赛没有班级名单，列出已进入的参加者。
    """

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, pk):
        exam = _get_managed_exam(request, pk)
        participants = {p.student_id: p for p in ExamParticipant.objects.filter(exam=exam)}
        records = {r.student_id: r for r in ScoreRecord.objects.filter(exam=exam)}
        submission_counts = dict(
            Submission.objects.filter(exam=exam).values("user_id").annotate(n=Count("id")).values_list("user_id", "n")
        )
        if exam.is_public:
            # 公开竞赛没有班级名单，列出已进入的参加者
            users = [p.student for p in ExamParticipant.objects.filter(exam=exam).select_related("student__student_profile")]
        else:
            users = [
                m.student
                for m in ClassMember.objects.active()
                .filter(class_group=exam.class_group)
                .select_related("student__student_profile")
            ]

        students = []
        for student in users:
            profile = getattr(student, "student_profile", None)
            participant = participants.get(student.id)
            record = records.get(student.id)
            if participant is None:
                state = "absent"
            elif participant.finished_at:
                state = "finished"
            else:
                state = "in_exam"
            students.append(
                {
                    "user_id": student.id,
                    "student_no": profile.student_no if profile else student.username,
                    "real_name": profile.real_name if profile else "",
                    "state": state,
                    "joined_at": participant.joined_at if participant else None,
                    "join_ip": participant.join_ip if participant else None,
                    "finished_at": participant.finished_at if participant else None,
                    "submission_count": submission_counts.get(student.id, 0),
                    "score": record.score if record else 0,
                    "solved_count": record.solved_count if record else 0,
                }
            )
        students.sort(key=lambda s: s["student_no"])

        return Response(
            {
                "exam": AdminExamSerializer(exam).data,
                "problems": ExamItemSerializer(exam.items.all(), many=True).data,
                "students": students,
                "rank": exam_rank(exam),
                "summary": {
                    "member_count": len(students),
                    "in_exam": sum(1 for s in students if s["state"] == "in_exam"),
                    "finished": sum(1 for s in students if s["state"] == "finished"),
                    "absent": sum(1 for s in students if s["state"] == "absent"),
                },
            }
        )


class ReopenParticipantView(APIView):
    """撤销交卷：学生误点交卷时，监考老师可让其继续作答。"""

    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, pk, user_id):
        exam = _get_managed_exam(request, pk)
        updated = ExamParticipant.objects.filter(exam=exam, student_id=user_id, finished_at__isnull=False).update(
            finished_at=None
        )
        if not updated:
            raise BusinessError("该学生没有交卷")
        return Response(None)


# ---------------------------------------------------------------- 学生端


def _student_exams(user):
    return (
        Exam.objects.filter(
            is_published=True,
            class_group__members__student=user,
            class_group__members__is_removed=False,
        )
        .select_related("class_group")
        .prefetch_related("items__problem")
        .distinct()
    )


def _context(request, exams):
    ids = [exam.id for exam in exams]
    if not request.user.is_authenticated:
        return {"request": request, "participants": {}, "records": {}}
    return {
        "request": request,
        "participants": {p.exam_id: p for p in ExamParticipant.objects.filter(student=request.user, exam_id__in=ids)},
        "records": {r.exam_id: r for r in ScoreRecord.objects.filter(student=request.user, exam_id__in=ids)},
    }


class MyExamListView(APIView):
    """我的考试，按状态分组：进行中、未开始、已结束。"""

    def get(self, request):
        exams = list(_student_exams(request.user).order_by("start_time"))
        data = StudentExamSerializer(exams, many=True, context=_context(request, exams)).data
        return Response(data)


class ActiveExamView(APIView):
    """学生当前进行中且锁定题库的考试，前端据此提示并跳转到考场；没有时为 null。"""

    def get(self, request):
        exam = active_exam(request.user)
        if exam is None:
            return Response(None)
        return Response({"id": exam.id, "title": exam.title, "end_time": exam.end_time})


class MyExamDetailView(APIView):
    """
    考场信息。题目在进入考试后（考试进行中），或考试结束且公布成绩后才返回。
    server_time 用于前端校准倒计时。公开竞赛访客也可查看（不含题目）。
    """

    permission_classes = [AllowAny]

    def get(self, request, pk):
        exam = student_exam(request.user, pk, allow_anonymous=True)
        context = _context(request, [exam])
        data = StudentExamSerializer(exam, context=context).data
        now = timezone.now()
        participant = context["participants"].get(exam.id)
        record = context["records"].get(exam.id)
        status_ = exam.status_at(now)

        can_view_problems = (status_ == "in_progress" and participant is not None) or (
            status_ == "ended" and exam.is_score_published
        )
        problems = []
        if can_view_problems:
            details = record.details if record else {}
            for item in exam.items.all():
                mine = details.get(str(item.problem_id))
                problems.append(
                    {
                        "problem_id": item.problem_id,
                        "title": item.problem.title,
                        "score": item.score,
                        "accepted": bool(mine and mine["accepted"]),
                        "attempted": mine is not None,
                        # 得分在公布成绩后显示
                        "my_score": (mine["score"] if mine else 0) if exam.is_score_published else None,
                    }
                )

        data.update(
            {
                "description": exam.description,
                "server_time": now,
                "ip": get_client_ip(request),
                "ip_allowed": exam.ip_allowed(get_client_ip(request)),
                "problems": problems,
                "my_solved": record.solved_count if record and exam.is_score_published else None,
            }
        )
        return Response(data)


class JoinExamView(APIView):
    """进入考试：考试进行中、IP 在允许范围内、口令正确。重复进入无副作用。"""

    def post(self, request, pk):
        exam = student_exam(request.user, pk)
        status_ = exam.status_at(timezone.now())
        if status_ == "not_started":
            raise BusinessError("考试尚未开始")
        if status_ == "ended":
            raise BusinessError("考试已结束")
        check_ip(exam, request)
        if not ExamParticipant.objects.filter(exam=exam, student=request.user).exists():
            given = str(request.data.get("password", ""))
            if exam.password and not secrets.compare_digest(given.encode(), exam.password.encode()):
                raise BusinessError("考试口令不正确")
            ExamParticipant.objects.get_or_create(
                exam=exam, student=request.user, defaults={"join_ip": get_client_ip(request)}
            )
        return Response(None)


class FinishExamView(APIView):
    """交卷：之后不能再提交，监考老师可撤销。"""

    def post(self, request, pk):
        exam = student_exam(request.user, pk)
        if exam.status_at(timezone.now()) != "in_progress":
            raise BusinessError("考试不在进行中")
        updated = ExamParticipant.objects.filter(exam=exam, student=request.user, finished_at__isnull=True).update(
            finished_at=timezone.now()
        )
        if not updated:
            raise BusinessError("你还没有进入考试或已经交卷")
        return Response(None)


def _mask(student_no):
    """公开排名中隐藏学号中间几位，如 20260001 → 2026**01。"""
    if len(student_no) <= 4:
        return student_no[0] + "*" * (len(student_no) - 1)
    return student_no[:4] + "*" * (len(student_no) - 6) + student_no[-2:]


def public_rank(rows):
    """公开竞赛的排名对所有人可见：在校学生只显示打码后的账号，不显示姓名。"""
    masked = []
    for row in rows:
        row = dict(row)
        # 更新前缓存的排名没有 is_student，按学生处理（宁可多打码）
        if row.get("is_student", True):
            row["student_no"] = _mask(row["student_no"])
        row["real_name"] = ""
        masked.append(row)
    return masked


class ExamRankView(APIView):
    """
    考试排名：考试中仅在开启「学生可看排名」时可见，结束后公布成绩时可见。
    公开竞赛的排名访客也可查看，在校学生的学号打码、不显示姓名。
    """

    permission_classes = [AllowAny]

    def get(self, request, pk):
        exam = student_exam(request.user, pk, allow_anonymous=True)
        status_ = exam.status_at(timezone.now())
        visible = (status_ == "in_progress" and exam.show_rank) or (status_ == "ended" and exam.is_score_published)
        if not visible:
            raise BusinessError("排名暂不公开")
        rank = exam_rank(exam)
        if exam.is_public:
            rank = public_rank(rank)
        return Response(
            {
                "rule_type": exam.rule_type,
                "is_public": exam.is_public,
                "problems": ExamItemSerializer(exam.items.all(), many=True).data,
                "rank": rank,
            }
        )


class ContestListView(APIView):
    """公开竞赛列表，访客也可浏览；登录用户附带自己的参加状态。"""

    permission_classes = [AllowAny]

    def get(self, request):
        contests = list(
            Exam.objects.filter(is_published=True, class_group__isnull=True)
            .prefetch_related("items")
            .annotate(participant_count=Count("participants", distinct=True))
            .order_by("-start_time")
        )
        return Response(StudentExamSerializer(contests, many=True, context=_context(request, contests)).data)
