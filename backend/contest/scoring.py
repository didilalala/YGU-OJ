"""
考试计分与排名（设计说明书 M7、8.1 第 8 步）。

OI 赛制：每题得分 = 分值 × 通过测试点比例，取最高分；按总分排名。
ACM 赛制：通过得满分，否则 0 分；按通过题数、罚时排名。
          罚时 = 各题首次通过的用时 + 首次通过前每次错误提交 20 分钟（编译错误不计）。

成绩写入 score_record，排名缓存在 Redis，成绩变化时失效。
details 各题明细：{题目编号: {"score", "accepted", "attempts", "ac_time"}}，
attempts 为首次通过前（或至今）的错误提交次数，ac_time 为首次通过距开考的秒数。
"""

from django.core.cache import cache
from django.db import transaction

from account.models import User
from classroom.models import ScoreRecord
from stats.cache import bump_class
from submission.models import Submission

from .models import Exam, ExamParticipant

Result = Submission.Result
WRONG_SUBMISSION_PENALTY = 20 * 60
RANK_CACHE_TIMEOUT = 60
_UNSCORED = (Result.PENDING, Result.JUDGING, Result.SE)


def rank_cache_key(exam_id):
    return f"exam_rank:{exam_id}"


def _ratio(submission):
    return 1.0 if submission.result == Result.AC else submission.passed_ratio


def _problem_details(exam, item, submissions):
    accepted, attempts, ac_time, best = False, 0, None, 0.0
    for submission in submissions:  # 按提交时间顺序
        if exam.rule_type == Exam.Rule.OI:
            best = max(best, item.score * _ratio(submission))
        if submission.result == Result.AC:
            if not accepted:
                accepted = True
                ac_time = int((submission.created_at - exam.start_time).total_seconds())
        elif not accepted and submission.result != Result.CE:
            attempts += 1
    score = item.score if accepted else (best if exam.rule_type == Exam.Rule.OI else 0)
    return {"score": round(score, 2), "accepted": accepted, "attempts": attempts, "ac_time": ac_time}


@transaction.atomic
def recalculate_exam_score(exam, student_id):
    record, _ = ScoreRecord.objects.get_or_create(student_id=student_id, exam=exam)
    # 锁住成绩记录，同一学生同时完成的评测依次计算
    record = ScoreRecord.objects.select_for_update().get(pk=record.pk)

    items = list(exam.items.all())
    submissions = list(
        Submission.objects.filter(exam=exam, user_id=student_id)
        .exclude(result__in=_UNSCORED)
        .only("problem_id", "result", "case_info", "created_at")
        .order_by("created_at", "id")
    )
    by_problem = {}
    for submission in submissions:
        by_problem.setdefault(submission.problem_id, []).append(submission)

    details = {
        str(item.problem_id): _problem_details(exam, item, by_problem[item.problem_id])
        for item in items
        if item.problem_id in by_problem
    }
    if not details:
        record.delete()
    else:
        record.details = details
        record.score = round(sum(d["score"] for d in details.values()), 2)
        record.solved_count = sum(1 for d in details.values() if d["accepted"])
        record.penalty = sum(
            d["ac_time"] + d["attempts"] * WRONG_SUBMISSION_PENALTY for d in details.values() if d["accepted"]
        )
        record.is_late = False
        record.save()
    transaction.on_commit(lambda: cache.delete(rank_cache_key(exam.id)))
    bump_class(exam.class_group_id)


def recalculate_exam(exam):
    """修改赛制、题目或分值后重算全部成绩。"""
    student_ids = set(Submission.objects.filter(exam=exam).values_list("user_id", flat=True))
    ScoreRecord.objects.filter(exam=exam).exclude(student_id__in=student_ids).delete()
    for student_id in student_ids:
        recalculate_exam_score(exam, student_id)
    cache.delete(rank_cache_key(exam.id))


def on_submission_judged(submission):
    if submission.exam_id:
        recalculate_exam_score(Exam.objects.get(pk=submission.exam_id), submission.user_id)


def _compute_rank(exam):
    records = {r.student_id: r for r in ScoreRecord.objects.filter(exam=exam)}
    # 进入过考试的学生都上榜（没有计分提交的记 0 分）
    student_ids = set(records) | set(ExamParticipant.objects.filter(exam=exam).values_list("student_id", flat=True))
    students = {u.id: u for u in User.objects.filter(pk__in=student_ids).select_related("student_profile")}

    rows = []
    for student_id in student_ids:
        user = students.get(student_id)
        if user is None:
            continue
        profile = getattr(user, "student_profile", None)
        record = records.get(student_id)
        rows.append(
            {
                "user_id": student_id,
                "student_no": profile.student_no if profile else user.username,
                "is_student": user.role == User.Role.STUDENT,
                "real_name": profile.real_name if profile else "",
                "score": record.score if record else 0,
                "solved_count": record.solved_count if record else 0,
                "penalty": record.penalty if record else 0,
                "problems": record.details if record else {},
            }
        )

    if exam.rule_type == Exam.Rule.ACM:
        key = lambda row: (-row["solved_count"], row["penalty"])  # noqa: E731
    else:
        key = lambda row: (-row["score"],)  # noqa: E731
    rows.sort(key=lambda row: (*key(row), row["student_no"]))

    # 并列同名次
    for index, row in enumerate(rows):
        row["rank"] = rows[index - 1]["rank"] if index and key(rows[index - 1]) == key(row) else index + 1
    return rows


def exam_rank(exam):
    return cache.get_or_set(rank_cache_key(exam.id), lambda: _compute_rank(exam), RANK_CACHE_TIMEOUT)
