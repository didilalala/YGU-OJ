"""
成绩统计与分析（设计说明书 M11、9.4）。

只统计在班级中的在校学生（role 为 student 且未被移出），普通用户与已移出的学生不计入。
「得分率」= 得分 / 满分；平均值按全班计算，未提交按 0 分（另给出已提交学生的平均分）。
"""

import statistics as pystats

from django.db.models import Count
from django.utils import timezone

from account.models import User
from classroom.models import Assignment, ClassMember, ScoreRecord
from contest.models import Exam
from submission.models import Submission

from .cache import cached

# 成绩分布：按得分率（%）划分的等级区间 [下限, 上限)
GRADE_BUCKETS = [("不及格", 0, 60), ("及格", 60, 70), ("中等", 70, 80), ("良好", 80, 90), ("优秀", 90, 101)]
# 错误类型（不含通过）；顺序与前端图表配色一致
ERROR_TYPES = ["WA", "CE", "TLE", "MLE", "RE", "PAC"]
_UNSCORED = (Submission.Result.PENDING, Submission.Result.JUDGING, Submission.Result.SE)


def _rate(score, total):
    return round(score / total * 100, 1) if total else 0.0


def class_members(class_group):
    """在班的在校学生，按学号排序：[(user, 学号, 姓名)]。"""
    members = (
        ClassMember.objects.active()
        .filter(class_group=class_group, student__role=User.Role.STUDENT)
        .select_related("student__student_profile")
    )
    rows = []
    for member in members:
        student = member.student
        profile = getattr(student, "student_profile", None)
        rows.append((student, profile.student_no if profile else student.username, profile.real_name if profile else ""))
    rows.sort(key=lambda row: row[1])
    return rows


def work_filter(work):
    return {"assignment": work} if isinstance(work, Assignment) else {"exam": work}


def _work_kind(work):
    return "assignment" if isinstance(work, Assignment) else "exam"


# ---------------------------------------------------------------- 单次作业 / 考试


def work_members(work):
    """统计对象：课堂作业与考试为在班学生；公开竞赛没有班级，为已进入的参加者。"""
    if work.class_group_id is not None:
        return class_members(work.class_group)
    rows = []
    for participant in work.participants.select_related("student__student_profile"):
        user = participant.student
        profile = getattr(user, "student_profile", None)
        rows.append((user, profile.student_no if profile else user.username, profile.real_name if profile else ""))
    rows.sort(key=lambda row: row[1])
    return rows


def _compute_work_stats(work):
    items = list(work.items.select_related("problem"))
    total = sum(item.score for item in items)
    members = work_members(work)
    member_ids = [user.id for user, _, _ in members]
    records = {r.student_id: r for r in ScoreRecord.objects.filter(student_id__in=member_ids, **work_filter(work))}

    scores = [records[uid].score if uid in records else 0 for uid in member_ids]
    submitted = [records[uid].score for uid in member_ids if uid in records]

    distribution = [
        {"label": label, "range": f"{low}–{min(high, 100)}%", "count": sum(1 for s in submitted if low <= _rate(s, total) < high)}
        for label, low, high in GRADE_BUCKETS
    ]

    # 各题：满分率（按全班）、平均得分、提交次数与各类错误次数
    counts = (
        Submission.objects.filter(user_id__in=member_ids, **work_filter(work))
        .exclude(result__in=_UNSCORED)
        .values("problem_id", "result")
        .annotate(n=Count("id"))
    )
    by_problem = {}
    for row in counts:
        by_problem.setdefault(row["problem_id"], {})[row["result"]] = row["n"]

    problems, overall_errors = [], dict.fromkeys(ERROR_TYPES, 0)
    for index, item in enumerate(items):
        key = str(item.problem_id)
        entries = [records[uid].details.get(key) for uid in member_ids if uid in records]
        entries = [e for e in entries if e]
        results = by_problem.get(item.problem_id, {})
        errors = {t: results.get(t, 0) for t in ERROR_TYPES}
        for t, n in errors.items():
            overall_errors[t] += n
        problems.append(
            {
                "index": index,
                "problem_id": item.problem_id,
                "title": item.problem.title,
                "score": item.score,
                "attempted_count": len(entries),
                "accepted_count": sum(1 for e in entries if e["accepted"]),
                "accepted_rate": _rate(sum(1 for e in entries if e["accepted"]), len(members)),
                "average_score": round(sum(e["score"] for e in entries) / len(members), 2) if members else 0,
                "submission_count": sum(results.values()),
                "ac_submission_count": results.get(Submission.Result.AC, 0),
                "errors": errors,
            }
        )

    return {
        "kind": _work_kind(work),
        "id": work.id,
        "title": work.title,
        "class_id": work.class_group_id,
        "class_name": work.class_group.name if work.class_group_id else "公开竞赛",
        "total_score": total,
        "summary": {
            "member_count": len(members),
            "submitted_count": len(submitted),
            "submission_rate": _rate(len(submitted), len(members)),
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
            "average_submitted": round(sum(submitted) / len(submitted), 2) if submitted else 0,
            "median_submitted": round(pystats.median(submitted), 2) if submitted else 0,
            "max_score": max(submitted, default=0),
            "min_score": min(submitted, default=0),
            "full_score_count": sum(1 for s in submitted if total and s >= total),
            # 及格率按全班计算
            "pass_rate": _rate(sum(1 for s in scores if total and _rate(s, total) >= 60), len(members)),
        },
        "distribution": distribution,
        "problems": problems,
        "errors": overall_errors,
        "not_submitted": [
            {"user_id": user.id, "student_no": no, "real_name": name}
            for user, no, name in members
            if user.id not in records
        ],
    }


def work_stats(work):
    # 公开竞赛不属于任何班级，班级版本号失效机制不适用，直接计算（参加人数通常不多）
    if work.class_group_id is None:
        return _compute_work_stats(work)
    return cached(work.class_group_id, f"{_work_kind(work)}:{work.id}", lambda: _compute_work_stats(work))


# ---------------------------------------------------------------- 班级总览


def class_works(class_group, now=None, only_published_exam_scores=False):
    """已发布且已开始的作业与考试，按时间排序（作业按截止时间，考试按开始时间）。"""
    now = now or timezone.now()
    assignments = Assignment.objects.filter(class_group=class_group, is_published=True, start_time__lte=now).prefetch_related("items")
    exams = Exam.objects.filter(class_group=class_group, is_published=True, start_time__lte=now).prefetch_related("items")
    if only_published_exam_scores:
        exams = exams.filter(is_score_published=True)
    works = [(a.end_time, a) for a in assignments] + [(e.start_time, e) for e in exams]
    works.sort(key=lambda pair: (pair[0], pair[1].id))
    return [work for _, work in works]


def _compute_class_overview(class_group):
    works = class_works(class_group)
    members = class_members(class_group)
    member_ids = [user.id for user, _, _ in members]
    records = ScoreRecord.objects.filter(student_id__in=member_ids).filter(
        assignment__in=[w for w in works if isinstance(w, Assignment)]
    ) | ScoreRecord.objects.filter(student_id__in=member_ids).filter(exam__in=[w for w in works if isinstance(w, Exam)])
    scores = {}
    for record in records:
        key = ("assignment", record.assignment_id) if record.assignment_id else ("exam", record.exam_id)
        scores[(record.student_id, key)] = record

    now = timezone.now()
    work_rows = []
    for work in works:
        kind = _work_kind(work)
        total = sum(item.score for item in work.items.all())
        member_scores = [scores[(uid, (kind, work.id))].score if (uid, (kind, work.id)) in scores else 0 for uid in member_ids]
        submitted = sum(1 for uid in member_ids if (uid, (kind, work.id)) in scores)
        work_rows.append(
            {
                "kind": kind,
                "id": work.id,
                "title": work.title,
                "time": work.end_time if kind == "assignment" else work.start_time,
                "ended": work.end_time < now,
                "total_score": total,
                "average_rate": _rate(sum(member_scores) / len(member_ids), total) if member_ids else 0,
                "submission_rate": _rate(submitted, len(member_ids)),
            }
        )

    students = []
    for user, no, name in members:
        cells, got, full = {}, 0.0, 0
        for work, row in zip(works, work_rows):
            record = scores.get((user.id, (row["kind"], work.id)))
            cells[f"{row['kind']}:{work.id}"] = record.score if record else None
            got += record.score if record else 0
            full += row["total_score"]
        students.append(
            {
                "user_id": user.id,
                "student_no": no,
                "real_name": name,
                "scores": cells,
                "total_score": round(got, 2),
                "full_score": full,
                "rate": _rate(got, full),
                "submitted_count": sum(1 for v in cells.values() if v is not None),
            }
        )

    # 班级排名：按总得分率，并列同名次
    students.sort(key=lambda s: (-s["rate"], s["student_no"]))
    for index, student in enumerate(students):
        same = index and students[index - 1]["rate"] == student["rate"]
        student["rank"] = students[index - 1]["rank"] if same else index + 1

    return {
        "class_id": class_group.id,
        "class_name": class_group.name,
        "works": work_rows,
        "students": students,
        "summary": {
            "member_count": len(members),
            "assignment_count": sum(1 for w in work_rows if w["kind"] == "assignment"),
            "exam_count": sum(1 for w in work_rows if w["kind"] == "exam"),
            "average_rate": round(sum(s["rate"] for s in students) / len(students), 1) if students else 0,
        },
    }


def class_overview(class_group):
    return cached(class_group.id, "overview", lambda: _compute_class_overview(class_group))


# ---------------------------------------------------------------- 学生个人


def my_scores(user):
    """
    个人学习曲线：所在班级每次作业与考试的得分率，与班级平均得分率对照；
    以及各知识点的掌握度（见 stats.knowledge）。
    只包含已截止的作业、已有提交的进行中作业，以及已公布成绩的考试。
    """
    # knowledge 依赖本模块，放在函数内导入以避免循环导入
    from .knowledge import student_knowledge

    now = timezone.now()
    memberships = ClassMember.objects.active().filter(student=user).select_related("class_group")
    result = []
    for membership in memberships:
        class_group = membership.class_group
        averages = {(w["kind"], w["id"]): w["average_rate"] for w in class_overview(class_group)["works"]}
        works = class_works(class_group, now=now, only_published_exam_scores=True)
        records = {}
        for record in ScoreRecord.objects.filter(student=user).filter(
            assignment__class_group=class_group
        ) | ScoreRecord.objects.filter(student=user, exam__class_group=class_group):
            records[("assignment", record.assignment_id) if record.assignment_id else ("exam", record.exam_id)] = record

        points = []
        for work in works:
            kind = _work_kind(work)
            record = records.get((kind, work.id))
            if kind == "assignment" and work.end_time >= now and record is None:
                continue  # 进行中且还没提交的作业不计入曲线
            total = sum(item.score for item in work.items.all())
            score = record.score if record else 0
            points.append(
                {
                    "kind": kind,
                    "id": work.id,
                    "title": work.title,
                    "time": work.end_time if kind == "assignment" else work.start_time,
                    "score": score,
                    "total_score": total,
                    "rate": _rate(score, total),
                    "class_average_rate": averages.get((kind, work.id), 0),
                    "submitted": record is not None,
                }
            )
        got = sum(p["score"] for p in points)
        full = sum(p["total_score"] for p in points)
        result.append(
            {
                "class_id": class_group.id,
                "class_name": class_group.name,
                "course": class_group.course,
                "points": points,
                "rate": _rate(got, full),
                "knowledge": student_knowledge(class_group, user.id),
            }
        )
    return result
