from datetime import datetime, timedelta, timezone

from bson import ObjectId

from app.services.analytics_service import build_analytics


class BatchProgress:
    def __init__(self, lessons, modules):
        self.lessons = lessons
        self.modules = modules

    def completed_for_users(self, _user_ids):
        return self.lessons

    def completed_modules_for_users(self, _user_ids):
        return self.modules


def test_build_analytics_aggregates_real_events_by_period_and_deduplicates_progress():
    now = datetime.now(timezone.utc)
    student_id = ObjectId()
    lesson_one = ObjectId()
    lesson_two = ObjectId()
    module_id = ObjectId()

    progress = BatchProgress(
        [
            {"user_id": student_id, "lesson_id": lesson_one, "module_id": module_id, "completed_at": now - timedelta(days=2)},
            {"user_id": student_id, "lesson_id": lesson_one, "module_id": module_id, "completed_at": now - timedelta(days=2)},
            {"user_id": student_id, "lesson_id": lesson_two, "module_id": module_id, "completed_at": now - timedelta(days=20)},
        ],
        [{"user_id": student_id, "module_id": module_id, "completed_at": now - timedelta(days=2)}],
    )
    attempts = [
        {"user_id": student_id, "status": "submitted", "score": 80, "submitted_at": now - timedelta(days=1), "answers": [{"is_correct": False, "competency": "Comunicación"}]},
        {"user_id": student_id, "status": "in_progress", "score": 0, "submitted_at": now - timedelta(days=1), "answers": []},
        {"user_id": student_id, "status": "submitted", "score": 20, "submitted_at": now - timedelta(days=20), "answers": []},
    ]

    result = build_analytics(
        period="7d",
        student_ids=[student_id],
        attempts=attempts,
        progress=progress,
        published_lesson_ids={str(lesson_one), str(lesson_two)},
        published_module_ids={str(module_id)},
    )

    assert result["attempts_count"] == 1
    assert result["average_score"] == 80
    assert result["active_students"] == 1
    assert result["snapshot"] == {
        "completed_lessons": 2,
        "total_lessons": 2,
        "percentage": 100,
        "completed_modules": 1,
        "total_modules": 1,
        "module_percentage": 100,
    }
    assert result["failed_competencies"] == [{"competency": "Comunicación", "count": 1}]
    assert len(result["progress_series"]) == 1
    assert result["progress_series"][0]["value"] == 100
    assert sum(point["lessons_completed"] for point in result["activity_series"]) == 1
    assert sum(point["assessments_submitted"] for point in result["activity_series"]) == 1


def test_build_analytics_returns_empty_series_for_empty_scope():
    result = build_analytics(
        period="30d",
        student_ids=[],
        attempts=[],
        progress=BatchProgress([], []),
        published_lesson_ids={"lesson-1"},
        published_module_ids={"module-1"},
    )

    assert result["active_students"] == 0
    assert result["attempts_count"] == 0
    assert result["snapshot"]["total_lessons"] == 1
    assert result["progress_series"] == []
