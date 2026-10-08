from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from bson import ObjectId

from app.schemas.analytics import AnalyticsPeriod


PERIOD_DAYS: dict[str, int | None] = {"7d": 7, "30d": 30, "90d": 90, "all": None}


def period_start(period: AnalyticsPeriod, now: datetime | None = None) -> datetime | None:
    days = PERIOD_DAYS[period]
    if days is None:
        return None
    current = now or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)


def _utc_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return None


def _event_date(value: Any) -> date | None:
    parsed = _utc_datetime(value)
    return parsed.astimezone(timezone.utc).date() if parsed else None


def _in_period(value: Any, start: datetime | None) -> bool:
    parsed = _utc_datetime(value)
    return parsed is not None and (start is None or parsed >= start)


def in_period(value: Any, start: datetime | None) -> bool:
    return _in_period(value, start)


def _id_string(value: Any) -> str:
    return str(value)


def _progress_documents(progress: Any, student_ids: list[ObjectId]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not student_ids:
        return [], []
    if hasattr(progress, "completed_for_users") and hasattr(progress, "completed_modules_for_users"):
        return progress.completed_for_users(student_ids), progress.completed_modules_for_users(student_ids)

    lessons: list[dict[str, Any]] = []
    modules: list[dict[str, Any]] = []
    for student_id in student_ids:
        try:
            lessons.extend(progress.completed_for_user(student_id))
            modules.extend(progress.completed_modules_for_user(student_id))
        except (AttributeError, TypeError):
            continue
    return lessons, modules


def _empty_payload(period: AnalyticsPeriod, total_lessons: int, total_modules: int) -> dict[str, Any]:
    return {
        "period": period,
        "snapshot": {
            "completed_lessons": 0,
            "total_lessons": total_lessons,
            "percentage": 0,
            "completed_modules": 0,
            "total_modules": total_modules,
            "module_percentage": 0,
        },
        "active_students": 0,
        "attempts_count": 0,
        "average_score": 0,
        "progress_series": [],
        "score_series": [],
        "activity_series": [],
        "failed_competencies": [],
    }


def build_analytics(
    *,
    period: AnalyticsPeriod,
    student_ids: list[ObjectId],
    attempts: list[dict[str, Any]],
    progress: Any,
    published_lesson_ids: set[str],
    published_module_ids: set[str],
) -> dict[str, Any]:
    total_lessons = len(published_lesson_ids)
    total_modules = len(published_module_ids)
    payload = _empty_payload(period, total_lessons, total_modules)
    start = period_start(period)
    if not student_ids:
        return payload

    student_id_strings = {_id_string(student_id) for student_id in student_ids}
    lesson_documents, module_documents = _progress_documents(progress, student_ids)
    lesson_documents = [document for document in lesson_documents if _id_string(document.get("user_id")) in student_id_strings]
    module_documents = [document for document in module_documents if _id_string(document.get("user_id")) in student_id_strings]

    completed_by_student: dict[str, set[str]] = {student_id: set() for student_id in student_id_strings}
    completed_modules_by_student: dict[str, set[str]] = {student_id: set() for student_id in student_id_strings}
    for document in lesson_documents:
        owner = _id_string(document.get("user_id"))
        lesson_id = _id_string(document.get("lesson_id"))
        if owner in completed_by_student and lesson_id in published_lesson_ids:
            completed_by_student[owner].add(lesson_id)
    for document in module_documents:
        owner = _id_string(document.get("user_id"))
        module_id = _id_string(document.get("module_id"))
        if owner in completed_modules_by_student and module_id in published_module_ids:
            completed_modules_by_student[owner].add(module_id)

    student_percentages = [
        (len(completed_by_student[student_id]) / total_lessons * 100) if total_lessons else 0
        for student_id in student_id_strings
    ]
    module_percentages = [
        (len(completed_modules_by_student[student_id]) / total_modules * 100) if total_modules else 0
        for student_id in student_id_strings
    ]
    payload["snapshot"] = {
        "completed_lessons": sum(len(completed) for completed in completed_by_student.values()),
        "total_lessons": total_lessons * len(student_id_strings),
        "percentage": round(sum(student_percentages) / len(student_percentages), 1) if student_percentages else 0,
        "completed_modules": sum(len(completed) for completed in completed_modules_by_student.values()),
        "total_modules": total_modules * len(student_id_strings),
        "module_percentage": round(sum(module_percentages) / len(module_percentages), 1) if module_percentages else 0,
    }

    submitted_attempts = [
        attempt
        for attempt in attempts
        if attempt.get("status") == "submitted"
        and _id_string(attempt.get("user_id")) in student_id_strings
        and _in_period(attempt.get("submitted_at"), start)
    ]
    payload["attempts_count"] = len(submitted_attempts)
    scores = [float(attempt.get("score", 0)) for attempt in submitted_attempts]
    payload["average_score"] = round(sum(scores) / len(scores), 1) if scores else 0

    active_student_ids = {
        _id_string(attempt.get("user_id"))
        for attempt in submitted_attempts
    }
    for document in lesson_documents:
        if _in_period(document.get("completed_at"), start):
            active_student_ids.add(_id_string(document.get("user_id")))
    for document in module_documents:
        if _in_period(document.get("completed_at"), start):
            active_student_ids.add(_id_string(document.get("user_id")))
    payload["active_students"] = len(active_student_ids)

    activity_by_day: dict[date, dict[str, int]] = defaultdict(lambda: {"lessons_completed": 0, "modules_completed": 0, "assessments_submitted": 0})
    seen_lesson_events: set[tuple[str, str]] = set()
    for document in lesson_documents:
        if not _in_period(document.get("completed_at"), start):
            continue
        lesson_key = (_id_string(document.get("user_id")), _id_string(document.get("lesson_id")))
        if lesson_key in seen_lesson_events:
            continue
        seen_lesson_events.add(lesson_key)
        day = _event_date(document.get("completed_at"))
        if day:
            activity_by_day[day]["lessons_completed"] += 1
    seen_module_events: set[tuple[str, str]] = set()
    for document in module_documents:
        if not _in_period(document.get("completed_at"), start):
            continue
        module_key = (_id_string(document.get("user_id")), _id_string(document.get("module_id")))
        if module_key in seen_module_events:
            continue
        seen_module_events.add(module_key)
        day = _event_date(document.get("completed_at"))
        if day:
            activity_by_day[day]["modules_completed"] += 1
    for attempt in submitted_attempts:
        day = _event_date(attempt.get("submitted_at"))
        if day:
            activity_by_day[day]["assessments_submitted"] += 1

    payload["activity_series"] = [
        {
            "time": day,
            **values,
            "total": sum(values.values()),
        }
        for day, values in sorted(activity_by_day.items())
    ]

    scores_by_day: dict[date, list[float]] = defaultdict(list)
    for attempt in submitted_attempts:
        day = _event_date(attempt.get("submitted_at"))
        if day:
            scores_by_day[day].append(float(attempt.get("score", 0)))
    payload["score_series"] = [
        {"time": day, "value": round(sum(values) / len(values), 1)}
        for day, values in sorted(scores_by_day.items())
    ]

    baseline: dict[str, set[str]] = {student_id: set() for student_id in student_id_strings}
    lesson_events: dict[date, list[tuple[str, str]]] = defaultdict(list)
    for document in lesson_documents:
        owner = _id_string(document.get("user_id"))
        lesson_id = _id_string(document.get("lesson_id"))
        completed_at = document.get("completed_at")
        if owner not in baseline or lesson_id not in published_lesson_ids:
            continue
        if start is not None and not _in_period(completed_at, start):
            completed_at_utc = _utc_datetime(completed_at)
            if completed_at_utc and completed_at_utc < start:
                baseline[owner].add(lesson_id)
            continue
        day = _event_date(completed_at)
        if day:
            lesson_events[day].append((owner, lesson_id))

    progress_by_day: dict[date, float] = {}
    for day in sorted(lesson_events):
        for owner, lesson_id in lesson_events[day]:
            baseline[owner].add(lesson_id)
        percentages = [
            (len(completed) / total_lessons * 100) if total_lessons else 0
            for completed in baseline.values()
        ]
        progress_by_day[day] = round(sum(percentages) / len(percentages), 1) if percentages else 0
    payload["progress_series"] = [
        {"time": day, "value": value}
        for day, value in sorted(progress_by_day.items())
    ]

    competency_counts: dict[str, int] = defaultdict(int)
    for attempt in submitted_attempts:
        for answer in attempt.get("answers", []):
            if not answer.get("is_correct"):
                competency_counts[answer.get("competency", "Sin clasificar")] += 1
    payload["failed_competencies"] = [
        {"competency": competency, "count": count}
        for competency, count in sorted(competency_counts.items(), key=lambda item: item[1], reverse=True)
    ]
    return payload
