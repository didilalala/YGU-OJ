"""
知识点掌握度（设计说明书 M12、9.4 知识点视角与学生视角）。

题目范围：班级已发布且已开始的作业与考试中的题目。上级知识点包含其全部下级知识点的题目。
某学生对某知识点的掌握度 = 该知识点下各题「最佳得分比例」的平均值：
    通过为 1，否则为通过测试点的比例，没做过为 0；
    作业、考试与平时练习的提交都计入（掌握度反映能力，与计分规则无关）。
通过率 = 已通过的题数 / 题数。班级值为在班学生的平均。
"""

from problem.models import KnowledgePoint, ProblemKnowledge
from submission.models import Submission

from .cache import cached
from .service import class_members, class_works

_UNSCORED = (Submission.Result.PENDING, Submission.Result.JUDGING, Submission.Result.SE)
# 最薄弱的若干知识点，提示教师重点讲解
WEAKEST_COUNT = 3


def _percent(value):
    return round(value * 100, 1)


def _point_problems(problem_ids):
    """各知识点（含下级）覆盖的题目：{知识点编号: set(题目编号)}，以及知识点信息。"""
    points = {p.id: p for p in KnowledgePoint.objects.all()}
    children = {}
    for point in points.values():
        children.setdefault(point.parent_id, []).append(point.id)

    direct = {}
    for link in ProblemKnowledge.objects.filter(problem_id__in=problem_ids).values("problem_id", "knowledge_point_id"):
        direct.setdefault(link["knowledge_point_id"], set()).add(link["problem_id"])

    def collect(point_id):
        result = set(direct.get(point_id, set()))
        for child_id in children.get(point_id, []):
            result |= collect(child_id)
        return result

    def depth(point):
        level = 0
        while point.parent_id and point.parent_id in points:
            point = points[point.parent_id]
            level += 1
        return level

    # 树形顺序：每个上级后面紧跟其下级，便于对照
    order = []

    def visit(point_id):
        order.append(point_id)
        for child_id in sorted(children.get(point_id, [])):
            visit(child_id)

    for root in sorted((p for p in points.values() if p.parent_id not in points), key=lambda p: (p.course, p.id)):
        visit(root.id)

    covered = {pid: collect(pid) for pid in points}
    tree_order = {pid: index for index, pid in enumerate(order)}
    return {pid: problems for pid, problems in covered.items() if problems}, points, depth, tree_order


def _best_ratios(member_ids, problem_ids):
    """{(学生, 题目): 最佳得分比例}"""
    best = {}
    submissions = (
        Submission.objects.filter(user_id__in=member_ids, problem_id__in=problem_ids)
        .exclude(result__in=_UNSCORED)
        .only("user_id", "problem_id", "result", "case_info")
    )
    for submission in submissions:
        ratio = 1.0 if submission.result == Submission.Result.AC else submission.passed_ratio
        key = (submission.user_id, submission.problem_id)
        if ratio > best.get(key, 0.0):
            best[key] = ratio
    return best


def _compute(class_group):
    works = class_works(class_group)
    problem_titles = {}
    for work in works:
        for item in work.items.select_related("problem"):
            problem_titles[item.problem_id] = item.problem.title

    covered, points, depth, tree_order = _point_problems(problem_titles)
    members = class_members(class_group)
    member_ids = [user.id for user, _, _ in members]
    best = _best_ratios(member_ids, problem_titles)

    students = []
    for user, no, name in members:
        mastery, accepted = {}, {}
        for point_id, problems in covered.items():
            ratios = [best.get((user.id, pid), 0.0) for pid in problems]
            mastery[str(point_id)] = _percent(sum(ratios) / len(ratios))
            accepted[str(point_id)] = sum(1 for r in ratios if r >= 1.0)
        students.append({"user_id": user.id, "student_no": no, "real_name": name, "mastery": mastery, "accepted": accepted})

    rows = []
    for point_id, problems in covered.items():
        point = points[point_id]
        key = str(point_id)
        rows.append(
            {
                "id": point_id,
                "name": point.name,
                "parent": point.parent_id,
                "depth": depth(point),
                "course": point.course,
                "problem_count": len(problems),
                "problems": sorted(({"id": pid, "title": problem_titles[pid]} for pid in problems), key=lambda p: p["id"]),
                "average_mastery": round(sum(s["mastery"][key] for s in students) / len(students), 1) if students else 0,
                "average_pass_rate": _percent(
                    sum(s["accepted"][key] for s in students) / (len(students) * len(problems))
                )
                if students
                else 0,
            }
        )
    rows.sort(key=lambda r: tree_order[r["id"]])
    weakest = sorted(rows, key=lambda r: r["average_mastery"])[:WEAKEST_COUNT] if students else []

    return {
        "class_id": class_group.id,
        "class_name": class_group.name,
        "points": rows,
        "students": students,
        "weakest": [r["id"] for r in weakest],
        "problem_count": len(problem_titles),
        "untagged_problem_count": len(set(problem_titles) - set().union(*covered.values())) if covered else len(problem_titles),
    }


def class_knowledge(class_group):
    return cached(class_group.id, "knowledge", lambda: _compute(class_group))


def student_knowledge(class_group, user_id):
    """某学生在班级中的知识点掌握度，附班级平均。"""
    data = class_knowledge(class_group)
    mine = next((s for s in data["students"] if s["user_id"] == user_id), None)
    if mine is None:
        return []
    return [
        {
            "id": point["id"],
            "name": point["name"],
            "parent": point["parent"],
            "depth": point["depth"],
            "problem_count": point["problem_count"],
            "mastery": mine["mastery"][str(point["id"])],
            "accepted_count": mine["accepted"][str(point["id"])],
            "class_average": point["average_mastery"],
        }
        for point in data["points"]
    ]
