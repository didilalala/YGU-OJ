"""管理后台仪表盘：教师看自己班级的概况，管理员看全站。"""

from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from classroom.models import ClassMember
from classroom.views import managed_assignments, managed_classes
from contest.views import managed_exams
from submission.models import Submission

TREND_DAYS = 14
# 作业提交率低于该值，且已开始，列入「待关注」
LOW_SUBMISSION_RATE = 50.0
# 距截止不到这么久、或截止后这么久内的作业才需要关注
ATTENTION_WINDOW = timedelta(days=3)


def _submissions_scope(user, classes):
    """教师只看本人班级学生的提交，管理员看全部。"""
    queryset = Submission.objects.all()
    if user.role != user.Role.ADMIN:
        student_ids = ClassMember.objects.active().filter(class_group__in=classes).values("student_id")
        queryset = queryset.filter(user_id__in=student_ids)
    return queryset


def _trend(submissions, today):
    start = today - timedelta(days=TREND_DAYS - 1)
    rows = (
        submissions.filter(created_at__date__gte=start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"), accepted=Count("id", filter=Q(result=Submission.Result.AC)))
    )
    by_day = {row["day"]: row for row in rows}
    result = []
    for offset in range(TREND_DAYS):
        day = start + timedelta(days=offset)
        row = by_day.get(day)
        result.append({"date": day.isoformat(), "count": row["total"] if row else 0, "accepted": row["accepted"] if row else 0})
    return result


def _attention(user, now):
    """提交率偏低的作业，按截止时间排序。"""
    rows = []
    assignments = managed_assignments(user).filter(
        is_published=True,
        start_time__lte=now,
        end_time__gte=now - ATTENTION_WINDOW,
        end_time__lte=now + ATTENTION_WINDOW,
    )
    for item in assignments:
        if not item.member_count:
            continue
        rate = round(item.submitted_count / item.member_count * 100, 1)
        if rate >= LOW_SUBMISSION_RATE:
            continue
        rows.append(
            {
                "kind": "assignment",
                "id": item.id,
                "title": item.title,
                "class_name": item.class_group.name,
                "end_time": item.end_time,
                "ended": item.end_time < now,
                "submitted": item.submitted_count,
                "member_count": item.member_count,
                "rate": rate,
            }
        )
    rows.sort(key=lambda row: row["end_time"])
    return rows[:6]


def admin_overview(user):
    now = timezone.now()
    today = timezone.localdate()
    classes = managed_classes(user)
    submissions = _submissions_scope(user, classes)

    exams = managed_exams(user).filter(is_published=True)
    return {
        "summary": {
            "class_count": classes.count(),
            "student_count": ClassMember.objects.active().filter(class_group__in=classes).values("student_id").distinct().count(),
            "active_assignments": managed_assignments(user).filter(is_published=True, start_time__lte=now, end_time__gte=now).count(),
            "active_exams": exams.filter(start_time__lte=now, end_time__gte=now).count(),
            "today_submissions": submissions.filter(created_at__date=today).count(),
            # 判题队列是全站共用的，教师也只看总数
            "queue_size": Submission.objects.filter(result__in=[Submission.Result.PENDING, Submission.Result.JUDGING]).count(),
        },
        "trend": _trend(submissions, today),
        "attention": _attention(user, now),
        "upcoming_exams": [
            {
                "id": exam.id,
                "title": exam.title,
                "class_name": exam.class_group.name if exam.class_group_id else "公开竞赛",
                "start_time": exam.start_time,
                "end_time": exam.end_time,
                "in_progress": exam.start_time <= now,
            }
            for exam in exams.filter(end_time__gte=now).order_by("start_time")[:5]
        ],
    }
