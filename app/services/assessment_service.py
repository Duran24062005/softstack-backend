import secrets
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.config.config import assessment_config
from app.core.exception import AssessmentUnavailableError, AttemptLimitError, InvalidAssessmentAnswerError, NotFoundError
from app.models.content import ContentStatus
from app.repositories.assessment_repository import AssessmentRepository
from app.repositories.content_repository import LessonRepository, ModuleRepository, ProgressRepository


def parse_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as error:
        raise NotFoundError from error


def oid(value: str | ObjectId) -> ObjectId:
    return value if isinstance(value, ObjectId) else parse_id(value)


def user_id(user: dict[str, Any]) -> ObjectId:
    return user.get("_id") or ObjectId(user["id"])


def public_question(document: dict[str, Any], options: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id": str(document.get("_id") or document.get("question_id")),
        "prompt": document["prompt"],
        "options": options if options is not None else document["options"],
        "competency": document.get("competency", "Comprensión del tema"),
        "difficulty": document.get("difficulty", "intermediate"),
    }


def admin_question(document: dict[str, Any]) -> dict[str, Any]:
    return {
        **public_question(document),
        "assessment_id": str(document["assessment_id"]),
        "correct_option_id": document["correct_option_id"],
        "explanation": document.get("explanation", ""),
        "status": document.get("status", "suggested"),
        "source_provider": document.get("source_provider"),
        "source_model": document.get("source_model"),
        "created_at": document["created_at"],
        "updated_at": document["updated_at"],
    }


def _defaults(repository: AssessmentRepository) -> dict[str, Any]:
    return repository.get_settings({
        "passing_score": assessment_config["DEFAULT_PASSING_SCORE"],
        "max_attempts": assessment_config["MAX_ATTEMPTS"],
        "default_question_count": assessment_config["DEFAULT_QUESTION_COUNT"],
    })


def _target_exists(target_type: str, target_id: ObjectId, modules: ModuleRepository, lessons: LessonRepository) -> dict[str, Any]:
    target = modules.find_by_id(target_id) if target_type == "module" else lessons.find_by_id(target_id)
    if not target:
        raise NotFoundError
    return target


def ensure_assessment(repository: AssessmentRepository, target_type: str, target_id: str, title: str, user: dict[str, Any], modules: ModuleRepository, lessons: LessonRepository) -> dict[str, Any]:
    parsed = parse_id(target_id)
    _target_exists(target_type, parsed, modules, lessons)
    existing = repository.find_by_target(target_type, parsed)
    if existing:
        return existing
    settings = _defaults(repository)
    now = datetime.now(timezone.utc)
    return repository.create_assessment({
        "target_type": target_type,
        "target_id": parsed,
        "title": title,
        "status": "draft",
        "question_count": settings.get("default_question_count", 5),
        "passing_score": settings.get("passing_score", 80),
        "max_attempts": settings.get("max_attempts", 3),
        "created_by": user_id(user),
        "created_at": now,
        "updated_at": now,
    })


def _state(repository: AssessmentRepository, student_id: ObjectId, assessment_id: ObjectId) -> dict[str, Any]:
    return repository.find_state(student_id, assessment_id) or repository.save_state(
        student_id,
        assessment_id,
        {"cycle": 1, "submitted_count": 0, "passed": False, "active_attempt_id": None},
    )


def _lesson_unlocked(lesson_id: ObjectId, progress: ProgressRepository, student_id: ObjectId) -> tuple[bool, str | None]:
    completed = {str(item["lesson_id"]) for item in progress.completed_for_user(student_id) if item.get("completion_source") == "quiz"}
    if str(lesson_id) in completed:
        return True, None
    return True, None


def _module_unlocked(module_id: ObjectId, lessons: LessonRepository, progress: ProgressRepository, student_id: ObjectId) -> tuple[bool, str | None]:
    module_lessons = lessons.list(module_id, ContentStatus.PUBLISHED.value)
    completed = {
        str(item["lesson_id"])
        for item in progress.completed_for_user(student_id)
        if item.get("completion_source") == "quiz"
    }
    if not module_lessons:
        return False, "El módulo todavía no tiene lecciones publicadas."
    if any(str(lesson["_id"]) not in completed for lesson in module_lessons):
        return False, "Aprueba todos los quizzes de las lecciones para desbloquear esta evaluación."
    return True, None


def _assessment_state_payload(assessment: dict[str, Any], repository: AssessmentRepository, progress: ProgressRepository | None, lessons: LessonRepository | None, student_id: ObjectId | None) -> dict[str, Any]:
    settings = _defaults(repository)
    state = repository.find_state(student_id, assessment["_id"]) if student_id else None
    state = state or {"submitted_count": 0, "passed": False, "cycle": 1}
    locked = False
    lock_reason = None
    if student_id and progress and lessons and assessment["target_type"] == "module":
        _, lock_reason = _module_unlocked(assessment["target_id"], lessons, progress, student_id)
        locked = lock_reason is not None
    approved_count = len(repository.list_questions(assessment["_id"], "approved"))
    return {
        "id": str(assessment["_id"]),
        "target_type": assessment["target_type"],
        "target_id": str(assessment["target_id"]),
        "title": assessment["title"],
        "status": assessment.get("status", "draft"),
        "question_count": assessment.get("question_count", 5),
        "passing_score": settings.get("passing_score", 80),
        "max_attempts": settings.get("max_attempts", 3),
        "approved_question_count": approved_count,
        "attempts_used": state.get("submitted_count", 0),
        "attempts_remaining": max(0, settings.get("max_attempts", 3) - state.get("submitted_count", 0)),
        "passed": bool(state.get("passed")),
        "locked": locked,
        "lock_reason": lock_reason,
        "questions": [],
    }


def get_student_assessment(repository: AssessmentRepository, target_type: str, target_id: str, progress: ProgressRepository, lessons: LessonRepository, user: dict[str, Any]) -> dict[str, Any]:
    assessment = repository.find_by_target(target_type, parse_id(target_id))
    if not assessment or assessment.get("status") != "published":
        raise NotFoundError
    return _assessment_state_payload(assessment, repository, progress, lessons, user_id(user))


def get_admin_assessment(repository: AssessmentRepository, assessment_id: str) -> dict[str, Any]:
    assessment = repository.find_assessment(parse_id(assessment_id))
    if not assessment:
        raise NotFoundError
    payload = _assessment_state_payload(assessment, repository, None, None, None)
    payload["questions"] = [admin_question(question) for question in repository.list_questions(assessment["_id"])]
    return payload


def update_assessment(repository: AssessmentRepository, assessment_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    assessment = repository.find_assessment(parse_id(assessment_id))
    if not assessment:
        raise NotFoundError
    if "question_count" in changes and not 3 <= changes["question_count"] <= 5:
        raise AssessmentUnavailableError
    if changes.get("status") == "published":
        approved_count = len(repository.list_questions(assessment["_id"], "approved"))
        count = changes.get("question_count", assessment.get("question_count", 5))
        if approved_count < count:
            raise AssessmentUnavailableError
    updated = repository.update_assessment(assessment["_id"], changes)
    if not updated:
        raise NotFoundError
    return get_admin_assessment(repository, assessment_id)


def create_question(repository: AssessmentRepository, assessment_id: str, payload: dict[str, Any], user: dict[str, Any], source_provider: str | None = None, source_model: str | None = None) -> dict[str, Any]:
    parsed = parse_id(assessment_id)
    if not repository.find_assessment(parsed):
        raise NotFoundError
    now = datetime.now(timezone.utc)
    document = {
        "assessment_id": parsed,
        **payload,
        "created_by": user_id(user),
        "source_provider": source_provider,
        "source_model": source_model,
        "created_at": now,
        "updated_at": now,
    }
    return admin_question(repository.create_question(document))


def update_question(repository: AssessmentRepository, question_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_id(question_id)
    current = repository.find_question(parsed)
    if not current:
        raise NotFoundError
    merged = {**current, **changes}
    options = merged.get("options", [])
    ids = [option["id"] for option in options]
    if len(ids) != 4 or len(set(ids)) != 4 or merged.get("correct_option_id") not in ids:
        raise InvalidAssessmentAnswerError
    updated = repository.update_question(parsed, changes)
    if not updated:
        raise NotFoundError
    return admin_question(updated)


def _shuffle_options(options: list[dict[str, Any]], correct_id: str, previous_position: int | None) -> list[dict[str, Any]]:
    shuffled = [dict(option) for option in options]
    rng = secrets.SystemRandom()
    for _ in range(12):
        rng.shuffle(shuffled)
        if previous_position is None or next(index for index, option in enumerate(shuffled) if option["id"] == correct_id) != previous_position:
            return shuffled
    if previous_position is not None:
        current_position = next(index for index, option in enumerate(shuffled) if option["id"] == correct_id)
        swap_position = (current_position + 1) % len(shuffled)
        shuffled[current_position], shuffled[swap_position] = shuffled[swap_position], shuffled[current_position]
    return shuffled


def _attempt_public(attempt: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(attempt["_id"]),
        "assessment_id": str(attempt["assessment_id"]),
        "attempt_number": attempt["attempt_number"],
        "cycle": attempt["cycle"],
        "questions": [public_question(snapshot) for snapshot in attempt["question_snapshots"]],
        "attempts_remaining": attempt["max_attempts"] - attempt["attempt_number"] + 1,
    }


def start_attempt(repository: AssessmentRepository, assessment_id: str, progress: ProgressRepository, lessons: LessonRepository, user: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_id(assessment_id)
    assessment = repository.find_assessment(parsed)
    if not assessment or assessment.get("status") != "published":
        raise NotFoundError
    student_id = user_id(user)
    if assessment["target_type"] == "module":
        unlocked, _ = _module_unlocked(assessment["target_id"], lessons, progress, student_id)
        if not unlocked:
            raise AssessmentUnavailableError
    active = repository.find_active_attempt(student_id, parsed)
    if active:
        return _attempt_public(active)
    state = _state(repository, student_id, parsed)
    max_attempts = _defaults(repository).get("max_attempts", 3)
    if state.get("passed") or state.get("submitted_count", 0) >= max_attempts:
        raise AttemptLimitError
    approved = repository.list_questions(parsed, "approved")
    question_count = assessment.get("question_count", 5)
    if len(approved) < question_count:
        raise AssessmentUnavailableError
    previous = repository.list_attempts(student_id, parsed)
    previous_positions = {}
    for snapshot in (previous[0].get("question_snapshots", []) if previous else []):
        previous_positions[snapshot["question_id"]] = next(index for index, option in enumerate(snapshot["options"]) if option["id"] == snapshot["correct_option_id"])
    selected = secrets.SystemRandom().sample(approved, question_count)
    snapshots = []
    for question in selected:
        snapshots.append({
            "question_id": str(question["_id"]),
            "prompt": question["prompt"],
            "options": _shuffle_options(question["options"], question["correct_option_id"], previous_positions.get(str(question["_id"]))),
            "correct_option_id": question["correct_option_id"],
            "explanation": question.get("explanation", ""),
            "competency": question.get("competency", "Comprensión del tema"),
            "difficulty": question.get("difficulty", "intermediate"),
        })
    attempt = repository.create_attempt({
        "assessment_id": parsed,
        "user_id": student_id,
        "cycle": state.get("cycle", 1),
        "attempt_number": state.get("submitted_count", 0) + 1,
        "status": "in_progress",
        "question_snapshots": snapshots,
        "max_attempts": max_attempts,
        "started_at": datetime.now(timezone.utc),
    })
    repository.save_state(student_id, parsed, {"active_attempt_id": attempt["_id"]})
    return _attempt_public(attempt)


def submit_attempt(repository: AssessmentRepository, assessment_id: str, attempt_id: str, payload: dict[str, Any], progress: ProgressRepository, lessons: LessonRepository, user: dict[str, Any]) -> dict[str, Any]:
    attempt = repository.find_attempt(parse_id(attempt_id))
    if not attempt or attempt["assessment_id"] != parse_id(assessment_id) or attempt["user_id"] != user_id(user):
        raise NotFoundError
    if attempt.get("status") != "in_progress":
        raise InvalidAssessmentAnswerError
    answers = payload["answers"]
    by_question = {answer["question_id"]: answer["selected_option_id"] for answer in answers}
    snapshots = attempt["question_snapshots"]
    expected_ids = {snapshot["question_id"] for snapshot in snapshots}
    if set(by_question) != expected_ids or len(answers) != len(expected_ids):
        raise InvalidAssessmentAnswerError
    question_results = []
    correct_count = 0
    for snapshot in snapshots:
        selected = by_question[snapshot["question_id"]]
        valid_options = {option["id"] for option in snapshot["options"]}
        if selected not in valid_options:
            raise InvalidAssessmentAnswerError
        correct = selected == snapshot["correct_option_id"]
        correct_count += int(correct)
        question_results.append({
            "question_id": snapshot["question_id"],
            "selected_option_id": selected,
            "correct_option_id": snapshot["correct_option_id"],
            "is_correct": correct,
            "explanation": snapshot.get("explanation", ""),
            "competency": snapshot.get("competency", "Comprensión del tema"),
        })
    score = round((correct_count / len(snapshots)) * 100, 1)
    assessment = repository.find_assessment(attempt["assessment_id"])
    if not assessment:
        raise NotFoundError
    passed = score >= _defaults(repository).get("passing_score", 80)
    submitted_at = datetime.now(timezone.utc)
    repository.update_attempt(attempt["_id"], {"status": "submitted", "answers": question_results, "score": score, "passed": passed, "submitted_at": submitted_at})
    state = _state(repository, attempt["user_id"], attempt["assessment_id"])
    repository.save_state(attempt["user_id"], attempt["assessment_id"], {"submitted_count": state.get("submitted_count", 0) + 1, "passed": passed, "active_attempt_id": None})
    lesson_completed = False
    module_completed = False
    if passed:
        if assessment["target_type"] == "lesson":
            lesson = lessons.find_by_id(assessment["target_id"])
            if lesson:
                progress.complete(attempt["user_id"], lesson["_id"], lesson["module_id"], source="quiz")
                lesson_completed = True
        else:
            progress.complete_module(attempt["user_id"], assessment["target_id"])
            module_completed = True
    state_after = repository.find_state(attempt["user_id"], attempt["assessment_id"]) or state
    return {
        "id": str(attempt["_id"]),
        "assessment_id": str(attempt["assessment_id"]),
        "attempt_number": attempt["attempt_number"],
        "cycle": attempt["cycle"],
        "score": score,
        "passed": passed,
        "attempts_used": state_after.get("submitted_count", 0),
        "attempts_remaining": max(0, _defaults(repository).get("max_attempts", 3) - state_after.get("submitted_count", 0)),
        "question_results": question_results,
        "lesson_completed": lesson_completed,
        "module_completed": module_completed,
        "submitted_at": submitted_at,
    }


def list_attempt_summaries(repository: AssessmentRepository, user: dict[str, Any], assessment_id: str | None = None) -> list[dict[str, Any]]:
    return [{
        "id": str(attempt["_id"]),
        "assessment_id": str(attempt["assessment_id"]),
        "attempt_number": attempt["attempt_number"],
        "cycle": attempt["cycle"],
        "score": attempt.get("score", 0),
        "passed": bool(attempt.get("passed")),
        "submitted_at": attempt["submitted_at"],
    } for attempt in repository.list_attempts(user_id(user), parse_id(assessment_id) if assessment_id else None) if attempt.get("status") == "submitted"]
