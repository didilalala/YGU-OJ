"""
个人主页与做题统计（设计说明书 M1）。

统计只看本人的提交（不含评测中、系统错误）。题目总数按当前用户可见的题目计算：
访客可见公开题，教师与管理员还能看到自己的私有题。
"""

from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from classroom.models import ClassMember
from problem.models import Problem
from submission.models import Submission

Result = Submission.Result
_UNSCORED = (Result.PENDING, Result.JUDGING, Result.SE)
ACTIVITY_DAYS = 30
RECENT_COUNT = 10


def _rate(part, whole):
    return round(part / whole * 100, 1) if whole else 0.0


def profile_detail(user):
    """个人信息：角色、姓名、学号或工号、所在班级数。"""
    profile = getattr(user, "student_profile", None) or getattr(user, "teacher_profile", None)
    data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "real_name": getattr(profile, "real_name", "") if profile else "",
        "created_at": user.created_at,
        "class_count": ClassMember.objects.active().filter(student=user).count(),
    }
    if user.role == user.Role.STUDENT and profile:
        data.update({"student_no": profile.student_no, "college": profile.college, "major": profile.major, "grade": profile.grade})
    if user.role == user.Role.TEACHER and profile:
        data.update({"staff_no": profile.staff_no, "college": profile.college})
    return data


def practice_stats(user):
    """做题统计：通过与尝试的题数、提交结果分布、各难度完成情况、近 30 天每日提交数、最近提交。"""
    now = timezone.now()
    submissions = Submission.objects.filter(user=user).exclude(result__in=_UNSCORED)

    totals = submissions.aggregate(
        submitted=Count("id"),
        accepted=Count("id", filter=Q(result=Result.AC)),
        attempted_problems=Count("problem", distinct=True),
        solved_problems=Count("problem", distinct=True, filter=Q(result=Result.AC)),
    )

    results = {row["result"]: row["n"] for row in submissions.values("result").annotate(n=Count("id"))}
    distribution = [{"result": code, "count": results.get(code, 0)} for code in Result.values if code not in _UNSCORED]

    # 题目总数按可见范围统计
    visible = Problem.objects.visible_to(user)
    solved_ids = set(
        submissions.filter(result=Result.AC).values_list("problem_id", flat=True).distinct()
    )
    by_difficulty = []
    for value, label in Problem.Difficulty.choices:
        in_level = visible.filter(difficulty=value)
        total = in_level.count()
        solved = in_level.filter(pk__in=solved_ids).count()
        by_difficulty.append({"difficulty": value, "label": label, "total": total, "solved": solved, "percent": _rate(solved, total)})

    # 按本地日期统计近 30 天（含今天）每天的提交数，没有提交的日子记 0
    first_day = timezone.localdate(now) - timedelta(days=ACTIVITY_DAYS - 1)
    daily = {
        row["day"]: row["n"]
        for row in submissions.filter(created_at__date__gte=first_day)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(n=Count("id"))
        .order_by()
    }
    activity = [
        {"date": (first_day + timedelta(days=offset)).isoformat(), "count": daily.get(first_day + timedelta(days=offset), 0)}
        for offset in range(ACTIVITY_DAYS)
    ]

    recent = [
        {
            "id": s.id,
            "problem_id": s.problem_id,
            "problem_title": s.problem.title,
            "language": s.language,
            "result": s.result,
            "created_at": s.created_at,
        }
        for s in submissions.select_related("problem").order_by("-id")[:RECENT_COUNT]
    ]

    return {
        "submitted": totals["submitted"],
        "accepted": totals["accepted"],
        "accept_rate": _rate(totals["accepted"], totals["submitted"]),
        "attempted_problems": totals["attempted_problems"],
        "solved_problems": totals["solved_problems"],
        "visible_problems": visible.count(),
        "distribution": distribution,
        "by_difficulty": by_difficulty,
        "activity": activity,
        "recent": recent,
    }


def profile(user):
    return {"profile": profile_detail(user), "stats": practice_stats(user)}
