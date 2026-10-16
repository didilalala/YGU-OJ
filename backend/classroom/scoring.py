"""
作业计分（设计说明书 9.2）。

- 每次提交的得分 = 题目分值 × 通过测试点比例（全部通过为 1）；
- 截止后的迟交提交再乘以 (1 - 迟交扣分比例)；
- 每题取该学生在本作业中的最高得分，同分时优先取未迟交的；
- 系统错误（SE）及评测中的提交不计分。

成绩记录每次都由全部提交重新计算，重判、修改分值或截止时间后结果依然正确。
"""

from django.db import transaction

from stats.cache import bump_class
from submission.models import Submission

from .models import Assignment, ScoreRecord

Result = Submission.Result
_UNSCORED = (Result.PENDING, Result.JUDGING, Result.SE)


def submission_ratio(submission):
    """通过测试点的比例：通过为 1；编译错误等没有测试点信息时为 0。"""
    if submission.result == Result.AC:
        return 1.0
    return submission.passed_ratio


def _best_per_problem(assignment, items, submissions):
    penalty = min(max(assignment.late_penalty, 0.0), 1.0)
    best, accepted = {}, set()
    for submission in submissions:
        item = items.get(submission.problem_id)
        if item is None:
            continue  # 题目已从作业中移除
        late = assignment.is_late(submission.created_at)
        score = round(item.score * submission_ratio(submission) * ((1 - penalty) if late else 1), 2)
        if submission.result == Result.AC:
            accepted.add(submission.problem_id)
        current = best.get(submission.problem_id)
        if (
            current is None
            or score > current["score"]
            or (score == current["score"] and current["late"] and not late)
        ):
            best[submission.problem_id] = {"score": score, "late": late}
    # 「是否通过」以任意一次通过为准，与取哪次的得分无关（迟交扣分后的通过也算通过）
    for problem_id, entry in best.items():
        entry["accepted"] = problem_id in accepted
    return best


@transaction.atomic
def recalculate_score(assignment, student_id):
    """重新计算某学生在某作业的成绩记录。没有任何计分提交时删除记录（视为未提交）。"""
    record, _ = ScoreRecord.objects.get_or_create(student_id=student_id, assignment=assignment)
    # 锁住该学生的成绩记录，同时完成的两次评测依次计算，后者能看到前者的提交
    record = ScoreRecord.objects.select_for_update().get(pk=record.pk)

    items = {item.problem_id: item for item in assignment.items.all()}
    submissions = (
        Submission.objects.filter(assignment=assignment, user_id=student_id)
        .exclude(result__in=_UNSCORED)
        .only("problem_id", "result", "case_info", "created_at")
    )
    best = _best_per_problem(assignment, items, submissions)

    bump_class(assignment.class_group_id)
    if not best:
        record.delete()
        return None
    record.details = {str(pid): entry for pid, entry in best.items()}
    record.score = round(sum(entry["score"] for entry in best.values()), 2)
    record.solved_count = sum(1 for entry in best.values() if entry["accepted"])
    record.is_late = any(entry["late"] and entry["score"] > 0 for entry in best.values())
    record.save()
    return record


def recalculate_assignment(assignment):
    """修改作业的题目、分值、截止时间或迟交规则后，重算全部学生的成绩。"""
    student_ids = set(Submission.objects.filter(assignment=assignment).values_list("user_id", flat=True))
    ScoreRecord.objects.filter(assignment=assignment).exclude(student_id__in=student_ids).delete()
    for student_id in student_ids:
        recalculate_score(assignment, student_id)


def on_submission_judged(submission):
    if submission.assignment_id:
        assignment = Assignment.objects.get(pk=submission.assignment_id)
        recalculate_score(assignment, submission.user_id)
