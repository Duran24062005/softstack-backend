from datetime import datetime, timezone
from unittest.mock import Mock

from bson import ObjectId

from app.models.content import ContentStatus
from app.services.content_service import get_progress, list_admin_module_lessons, list_admin_modules, slugify


def test_slugify_normalizes_accents_and_punctuation():
    assert slugify("Comunicación profesional / CV") == "comunicacion-profesional-cv"


def test_progress_is_calculated_from_unique_completed_lessons():
    user_id = ObjectId()
    lesson_one = ObjectId()
    lesson_two = ObjectId()
    progress = Mock()
    lessons = Mock()
    progress.completed_for_user.return_value = [
        {"lesson_id": lesson_one, "completed_at": datetime.now(timezone.utc)},
        {"lesson_id": lesson_two, "completed_at": datetime.now(timezone.utc)},
    ]
    lessons.list.return_value = [{"_id": lesson_one}, {"_id": lesson_two}, {"_id": ObjectId()}]

    result = get_progress(progress, lessons, {"_id": user_id})

    assert result == {"completed_lesson_ids": [str(lesson_one), str(lesson_two)], "completed_count": 2, "total_lessons": 3, "percentage": 66.7, "completed_module_ids": [], "completed_module_count": 0, "total_modules": 0, "module_percentage": 0}
    progress.completed_for_user.assert_called_once_with(user_id)
    lessons.list.assert_called_once_with(status=ContentStatus.PUBLISHED.value)


def test_admin_module_list_includes_unpublished_modules():
    module_id = ObjectId()
    timestamp = datetime.now(timezone.utc)
    modules = Mock()
    modules.list.return_value = [
        {
            "_id": module_id,
            "title": "Borrador de empleabilidad",
            "slug": "borrador-de-empleabilidad",
            "description": "Contenido en preparación",
            "order": 0,
            "status": ContentStatus.DRAFT.value,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    ]

    result = list_admin_modules(modules)

    assert result[0]["id"] == str(module_id)
    assert result[0]["status"] == ContentStatus.DRAFT.value
    modules.list.assert_called_once_with()


def test_admin_lesson_list_includes_unpublished_lessons_for_module():
    module_id = ObjectId()
    lesson_id = ObjectId()
    timestamp = datetime.now(timezone.utc)
    modules = Mock()
    lessons = Mock()
    modules.find_by_id.return_value = {"_id": module_id}
    lessons.list.return_value = [
        {
            "_id": lesson_id,
            "module_id": module_id,
            "title": "Lección en preparación",
            "slug": "leccion-en-preparacion",
            "description": "Contenido en preparación",
            "content": {"type": "doc", "content": []},
            "order": 0,
            "status": ContentStatus.DRAFT.value,
            "estimated_minutes": 10,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    ]

    result = list_admin_module_lessons(modules, lessons, str(module_id))

    assert result[0]["id"] == str(lesson_id)
    assert result[0]["status"] == ContentStatus.DRAFT.value
    lessons.list.assert_called_once_with(module_id)


def test_progress_includes_completed_modules_from_quiz_progress():
    user_id = ObjectId()
    module_id = ObjectId()
    lesson_id = ObjectId()
    progress = Mock()
    lessons = Mock()
    progress.completed_for_user.return_value = [{"lesson_id": lesson_id, "module_id": module_id, "completion_source": "quiz"}]
    progress.completed_modules_for_user.return_value = [{"module_id": module_id}]
    lessons.list.return_value = [{"_id": lesson_id, "module_id": module_id}]

    result = get_progress(progress, lessons, {"_id": user_id})

    assert result["completed_module_ids"] == [str(module_id)]
    assert result["completed_module_count"] == 1
    assert result["total_modules"] == 1
    assert result["module_percentage"] == 100
