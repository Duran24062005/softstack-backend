from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from bson import ObjectId

from app.core.exception import (
    AssessmentUnavailableError,
    AttemptLimitError,
    InvalidAssessmentAnswerError,
    NotFoundError,
)
from app.models.content import ContentStatus
from app.services.assessment_service import (
    _shuffle_options,
    _lesson_unlocked,
    _module_unlocked,
    create_question,
    ensure_assessment,
    get_student_assessment,
    list_attempt_summaries,
    start_attempt,
    submit_attempt,
    update_assessment,
    update_question,
    oid,
)


class FakeAssessmentRepository:
    def __init__(self):
        self.assessment_id = ObjectId()
        self.question_ids = [ObjectId() for _ in range(5)]
        self.assessment = {
            "_id": self.assessment_id,
            "target_type": "lesson",
            "target_id": ObjectId(),
            "title": "Evaluación",
            "status": "published",
            "question_count": 3,
            "passing_score": 80,
            "max_attempts": 3,
        }
        self.questions = [
            {"_id": question_id, "prompt": f"Pregunta {index}", "options": [{"id": option, "text": option} for option in ["a", "b", "c", "d"]], "correct_option_id": "a", "explanation": "Porque sí", "competency": "Tema", "status": "approved"}
            for index, question_id in enumerate(self.question_ids)
        ]
        self.states = {}
        self.attempts = []
        self.settings = {
            "passing_score": 80,
            "max_attempts": 3,
            "default_question_count": 5,
        }
        self.created_questions = []
        self.assignments = {}

    def find_assessment(self, assessment_id):
        return self.assessment if assessment_id == self.assessment_id else None

    def find_by_target(self, target_type, target_id):
        if not self.assessment:
            return None
        if self.assessment["target_type"] == target_type and self.assessment["target_id"] == target_id:
            return self.assessment
        return None

    def get_settings(self, defaults):
        return {**defaults, **self.settings}

    def update_settings(self, changes, defaults):
        self.settings = {**self.get_settings(defaults), **changes}
        return self.settings

    def create_assessment(self, document):
        self.assessment = {"_id": ObjectId(), **document}
        self.assessment_id = self.assessment["_id"]
        return self.assessment

    def update_assessment(self, assessment_id, changes):
        if assessment_id != self.assessment_id:
            return None
        self.assessment.update(changes)
        return self.assessment

    def find_state(self, user_id, assessment_id):
        return self.states.get((user_id, assessment_id))

    def save_state(self, user_id, assessment_id, changes):
        current = self.states.setdefault((user_id, assessment_id), {"cycle": 1, "submitted_count": 0, "passed": False})
        current.update(changes)
        return current

    def list_questions(self, assessment_id, status=None):
        return [question for question in self.questions if status is None or question["status"] == status]

    def find_question(self, question_id):
        return next((question for question in self.questions if question["_id"] == question_id), None)

    def create_question(self, document):
        created = {"_id": ObjectId(), **document}
        self.questions.append(created)
        self.created_questions.append(created)
        return created

    def update_question(self, question_id, changes):
        question = self.find_question(question_id)
        if not question:
            return None
        question.update(changes)
        return question

    def list_attempts(self, user_id=None, assessment_id=None, student_ids=None):
        return [attempt for attempt in self.attempts if (user_id is None or attempt["user_id"] == user_id) and (assessment_id is None or attempt["assessment_id"] == assessment_id)]

    def find_active_attempt(self, user_id, assessment_id):
        return next((attempt for attempt in self.attempts if attempt["user_id"] == user_id and attempt["assessment_id"] == assessment_id and attempt["status"] == "in_progress"), None)

    def create_attempt(self, document):
        document = {"_id": ObjectId(), **document}
        self.attempts.append(document)
        return document

    def find_attempt(self, attempt_id):
        return next((attempt for attempt in self.attempts if attempt["_id"] == attempt_id), None)

    def update_attempt(self, attempt_id, changes):
        attempt = self.find_attempt(attempt_id)
        attempt.update(changes)
        return attempt

    def reset_state(self, user_id, assessment_id, admin_id, reason):
        current = self.states.get((user_id, assessment_id), {"cycle": 1})
        next_state = {"cycle": current.get("cycle", 1) + 1, "submitted_count": 0, "passed": False, "active_attempt_id": None}
        self.states[(user_id, assessment_id)] = next_state
        for attempt in self.attempts:
            if attempt["user_id"] == user_id and attempt["assessment_id"] == assessment_id and attempt["status"] == "in_progress":
                attempt["status"] = "cancelled"
        return next_state

    def assignment_for_student(self, student_id):
        return self.assignments.get(student_id)

    def students_for_trainer(self, trainer_id):
        return [student_id for student_id, assignment in self.assignments.items() if assignment["trainer_id"] == trainer_id]


class FakeProgress:
    def __init__(self):
        self.completed = []
        self.completed_modules = []

    def completed_for_user(self, user_id):
        return self.completed

    def complete(self, user_id, lesson_id, module_id, source="manual_legacy"):
        self.completed.append({"lesson_id": lesson_id, "module_id": module_id, "completion_source": source})

    def complete_module(self, user_id, module_id):
        self.completed_modules.append({"user_id": user_id, "module_id": module_id})

    def completed_modules_for_user(self, user_id):
        return [item for item in self.completed_modules if item["user_id"] == user_id]


class FakeLessons:
    def __init__(self, lesson_id, module_id=None, module_lessons=None):
        self.lesson = {"_id": lesson_id, "module_id": module_id or ObjectId()}
        self.module_lessons = [self.lesson] if module_lessons is None else module_lessons

    def find_by_id(self, lesson_id):
        return self.lesson

    def list(self, *args, **kwargs):
        if args and args[0] == self.lesson["module_id"]:
            return self.module_lessons
        return [self.lesson]


def test_shuffle_moves_correct_option_when_previous_position_is_known():
    options = [{"id": value, "text": value} for value in ["a", "b", "c", "d"]]
    shuffled = _shuffle_options(options, "a", 0)
    assert next(index for index, option in enumerate(shuffled) if option["id"] == "a") != 0
    assert {option["id"] for option in shuffled} == {"a", "b", "c", "d"}


def test_attempt_is_snapshotted_and_submission_marks_lesson_complete():
    repository = FakeAssessmentRepository()
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    progress.completed = [{"lesson_id": lessons.lesson["_id"], "module_id": repository.assessment["target_id"], "completion_source": "quiz"}]
    user = {"_id": ObjectId()}

    attempt = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)
    stored = repository.find_attempt(ObjectId(attempt["id"]))
    assert len(stored["question_snapshots"]) == 3
    assert all("correct_option_id" not in question for question in attempt["questions"])

    result = submit_attempt(
        repository,
        str(repository.assessment_id),
        attempt["id"],
        {"answers": [{"question_id": question["id"], "selected_option_id": next(option["id"] for option in question["options"] if option["id"] == "a")} for question in attempt["questions"]]},
        progress,
        lessons,
        user,
    )

    assert result["passed"] is True
    assert result["score"] == 100
    assert result["lesson_completed"] is True
    assert progress.completed[0]["completion_source"] == "quiz"


def test_starting_an_active_attempt_is_idempotent_and_never_exposes_the_answer():
    repository = FakeAssessmentRepository()
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    user = {"_id": ObjectId()}

    first = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)
    second = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)

    assert second == first
    assert len(repository.attempts) == 1
    assert all("correct_option_id" not in question for question in second["questions"])
    assert len({question["id"] for question in second["questions"]}) == len(second["questions"])


def test_failed_submission_reports_competencies_and_does_not_complete_lesson():
    repository = FakeAssessmentRepository()
    repository.assessment["question_count"] = 3
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    user = {"_id": ObjectId()}
    attempt = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)

    answers = []
    for index, question in enumerate(attempt["questions"]):
        selected = next(option["id"] for option in question["options"] if option["id"] == "a")
        if index == 0:
            selected = next(option["id"] for option in question["options"] if option["id"] != "a")
        answers.append({"question_id": question["id"], "selected_option_id": selected})

    result = submit_attempt(repository, str(repository.assessment_id), attempt["id"], {"answers": answers}, progress, lessons, user)

    assert result["passed"] is False
    assert result["score"] == pytest.approx(66.7)
    assert result["attempts_remaining"] == 2
    assert result["lesson_completed"] is False
    assert result["question_results"][0]["is_correct"] is False
    assert result["question_results"][0]["competency"] == "Tema"
    assert progress.completed == []


@pytest.mark.parametrize(
    "answers_factory",
    [
        lambda questions: [],
        lambda questions: [{"question_id": questions[0]["id"], "selected_option_id": "a"}] * len(questions),
        lambda questions: [{"question_id": question["id"], "selected_option_id": "invalid"} for question in questions],
    ],
)
def test_submission_rejects_incomplete_duplicate_or_unknown_options(answers_factory):
    repository = FakeAssessmentRepository()
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    user = {"_id": ObjectId()}
    attempt = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)

    with pytest.raises(InvalidAssessmentAnswerError):
        submit_attempt(repository, str(repository.assessment_id), attempt["id"], {"answers": answers_factory(attempt["questions"])}, progress, lessons, user)


def test_submission_rejects_foreign_attempt_and_cannot_be_submitted_twice():
    repository = FakeAssessmentRepository()
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    owner = {"_id": ObjectId()}
    other_user = {"_id": ObjectId()}
    attempt = start_attempt(repository, str(repository.assessment_id), progress, lessons, owner)
    correct_answers = {"answers": [{"question_id": question["id"], "selected_option_id": "a"} for question in attempt["questions"]]}

    with pytest.raises(NotFoundError):
        submit_attempt(repository, str(repository.assessment_id), attempt["id"], correct_answers, progress, lessons, other_user)

    submit_attempt(repository, str(repository.assessment_id), attempt["id"], correct_answers, progress, lessons, owner)
    with pytest.raises(InvalidAssessmentAnswerError):
        submit_attempt(repository, str(repository.assessment_id), attempt["id"], correct_answers, progress, lessons, owner)


def test_three_attempt_limit_is_taken_from_settings_and_pass_stops_future_attempts():
    repository = FakeAssessmentRepository()
    repository.assessment["question_count"] = 3
    repository.settings["passing_score"] = 101
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    user = {"_id": ObjectId()}

    for expected_attempt_number in range(1, 4):
        attempt = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)
        assert attempt["attempt_number"] == expected_attempt_number
        answers = {"answers": [{"question_id": question["id"], "selected_option_id": "a"} for question in attempt["questions"]]}
        submit_attempt(repository, str(repository.assessment_id), attempt["id"], answers, progress, lessons, user)

    with pytest.raises(AttemptLimitError):
        start_attempt(repository, str(repository.assessment_id), progress, lessons, user)


def test_module_assessment_ignores_legacy_completion_until_every_lesson_has_quiz_completion():
    repository = FakeAssessmentRepository()
    module_id = ObjectId()
    lesson_one = {"_id": ObjectId(), "module_id": module_id}
    lesson_two = {"_id": ObjectId(), "module_id": module_id}
    repository.assessment.update({"target_type": "module", "target_id": module_id, "question_count": 3})
    repository.questions = repository.questions[:3]
    progress = FakeProgress()
    progress.completed = [{"lesson_id": lesson_one["_id"], "module_id": module_id, "completion_source": "manual_legacy"}, {"lesson_id": lesson_two["_id"], "module_id": module_id, "completion_source": "quiz"}]
    lessons = FakeLessons(lesson_one["_id"], module_id, [lesson_one, lesson_two])
    user = {"_id": ObjectId()}

    with pytest.raises(AssessmentUnavailableError):
        start_attempt(repository, str(repository.assessment_id), progress, lessons, user)

    progress.completed[0]["completion_source"] = "quiz"
    attempt = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)
    assert attempt["cycle"] == 1


def test_threshold_is_configurable_and_exact_boundary_passes():
    repository = FakeAssessmentRepository()
    repository.assessment["question_count"] = 5
    repository.settings["passing_score"] = 80
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    user = {"_id": ObjectId()}
    attempt = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)
    answers = {"answers": [{"question_id": question["id"], "selected_option_id": "a" if index < 4 else "b"} for index, question in enumerate(attempt["questions"])]}

    result = submit_attempt(repository, str(repository.assessment_id), attempt["id"], answers, progress, lessons, user)

    assert result["score"] == 80
    assert result["passed"] is True


def test_ensure_update_and_question_lifecycle_enforces_publish_requirements():
    repository = FakeAssessmentRepository()
    repository.assessment = None
    repository.assessment_id = ObjectId()
    repository.questions = []
    module_id = ObjectId()
    modules = Mock()
    lessons = Mock()
    modules.find_by_id.return_value = {"_id": module_id, "title": "Módulo"}
    lessons.find_by_id.return_value = None
    user = {"_id": ObjectId()}

    created = ensure_assessment(repository, "module", str(module_id), "Evaluación", user, modules, lessons)
    assert created["question_count"] == 5
    assert created["max_attempts"] == 3
    assert ensure_assessment(repository, "module", str(module_id), "Otra", user, modules, lessons) is created

    with pytest.raises(AssessmentUnavailableError):
        update_assessment(repository, str(created["_id"]), {"status": "published"})

    question_payload = {
        "prompt": "¿Qué demuestra comprensión?",
        "options": [{"id": value, "text": value} for value in ["a", "b", "c", "d"]],
        "correct_option_id": "a",
        "explanation": "La evidencia demuestra comprensión.",
        "competency": "Comprensión",
        "difficulty": "basic",
        "status": "approved",
    }
    for _ in range(5):
        create_question(repository, str(created["_id"]), question_payload, user)

    published = update_assessment(repository, str(created["_id"]), {"question_count": 3, "status": "published"})
    assert published["status"] == "published"
    assert published["question_count"] == 3

    question_id = str(repository.questions[0]["_id"])
    updated = update_question(repository, question_id, {"correct_option_id": "b"})
    assert updated["correct_option_id"] == "b"
    with pytest.raises(InvalidAssessmentAnswerError):
        update_question(repository, question_id, {"options": [{"id": "a", "text": "a"}]})


def test_get_student_assessment_and_attempt_summaries_are_private_to_the_student():
    repository = FakeAssessmentRepository()
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    user = {"_id": ObjectId()}
    payload = get_student_assessment(repository, "lesson", str(repository.assessment["target_id"]), progress, lessons, user)
    assert payload["questions"] == []
    assert "correct_option_id" not in payload

    attempt = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)
    submit_attempt(repository, str(repository.assessment_id), attempt["id"], {"answers": [{"question_id": question["id"], "selected_option_id": "a"} for question in attempt["questions"]]}, progress, lessons, user)
    repository.attempts.append({"_id": ObjectId(), "assessment_id": repository.assessment_id, "user_id": user["_id"], "status": "in_progress", "attempt_number": 2, "cycle": 1})

    summaries = list_attempt_summaries(repository, user)
    assert len(summaries) == 1
    assert "question_snapshots" not in summaries[0]


def test_identifier_and_unlock_helpers_cover_missing_and_legacy_states():
    identifier = ObjectId()
    assert oid(identifier) == identifier
    assert oid(str(identifier)) == identifier

    progress = FakeProgress()
    lessons = FakeLessons(ObjectId(), ObjectId(), [])
    assert _lesson_unlocked(identifier, progress, ObjectId()) == (True, None)
    progress.completed = [{"lesson_id": identifier, "completion_source": "quiz"}]
    assert _lesson_unlocked(identifier, progress, ObjectId()) == (True, None)
    assert _module_unlocked(lessons.lesson["module_id"], lessons, progress, ObjectId()) == (False, "El módulo todavía no tiene lecciones publicadas.")

    with pytest.raises(NotFoundError):
        ensure_assessment(FakeAssessmentRepository(), "lesson", "invalid", "Quiz", {"_id": ObjectId()}, Mock(), Mock())
    missing_lessons = Mock()
    missing_lessons.find_by_id.return_value = None
    with pytest.raises(NotFoundError):
        ensure_assessment(FakeAssessmentRepository(), "lesson", str(identifier), "Quiz", {"_id": ObjectId()}, Mock(), missing_lessons)


def test_service_rejects_missing_or_unready_resources_and_invalid_edits():
    repository = FakeAssessmentRepository()
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    user = {"_id": ObjectId()}

    repository.assessment["status"] = "draft"
    with pytest.raises(NotFoundError):
        start_attempt(repository, str(repository.assessment_id), progress, lessons, user)
    repository.assessment["status"] = "published"
    repository.assessment["question_count"] = 6
    with pytest.raises(AssessmentUnavailableError):
        start_attempt(repository, str(repository.assessment_id), progress, lessons, user)

    with pytest.raises(NotFoundError):
        get_student_assessment(repository, "lesson", "invalid", progress, lessons, user)
    repository.assessment["status"] = "draft"
    with pytest.raises(NotFoundError):
        get_student_assessment(repository, "lesson", str(repository.assessment["target_id"]), progress, lessons, user)
    repository.assessment["status"] = "published"
    with pytest.raises(NotFoundError):
        from app.services.assessment_service import get_admin_assessment
        get_admin_assessment(repository, str(ObjectId()))
    with pytest.raises(NotFoundError):
        update_assessment(repository, str(ObjectId()), {},)
    with pytest.raises(AssessmentUnavailableError):
        update_assessment(repository, str(repository.assessment_id), {"question_count": 2})
    with pytest.raises(NotFoundError):
        create_question(repository, str(ObjectId()), {}, user)
    with pytest.raises(NotFoundError):
        update_question(repository, str(ObjectId()), {})
    question = repository.questions[0]
    original_update_question = repository.update_question
    repository.update_question = lambda *_args, **_kwargs: None
    with pytest.raises(NotFoundError):
        update_question(repository, str(question["_id"]), {"competency": "Aplicación"})
    repository.update_question = original_update_question

    original_update = repository.update_assessment
    repository.update_assessment = lambda *_args, **_kwargs: None
    with pytest.raises(NotFoundError):
        update_assessment(repository, str(repository.assessment_id), {"title": "Nuevo título"})
    repository.update_assessment = original_update


def test_shuffle_fallback_changes_position_when_rng_repeats(monkeypatch):
    class RepeatingRandom:
        def shuffle(self, values):
            return None

    monkeypatch.setattr("app.services.assessment_service.secrets.SystemRandom", RepeatingRandom)
    shuffled = _shuffle_options([{"id": value, "text": value} for value in ["a", "b", "c", "d"]], "a", 0)
    assert next(index for index, option in enumerate(shuffled) if option["id"] == "a") == 1


def test_module_pass_marks_module_and_missing_lesson_does_not_fake_completion():
    repository = FakeAssessmentRepository()
    repository.assessment.update({"target_type": "module", "question_count": 3})
    repository.questions = repository.questions[:3]
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    progress.completed = [{"lesson_id": lessons.lesson["_id"], "module_id": repository.assessment["target_id"], "completion_source": "quiz"}]
    user = {"_id": ObjectId()}
    attempt = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)
    result = submit_attempt(repository, str(repository.assessment_id), attempt["id"], {"answers": [{"question_id": question["id"], "selected_option_id": "a"} for question in attempt["questions"]]}, progress, lessons, user)
    assert result["module_completed"] is True
    assert progress.completed_modules

    repository = FakeAssessmentRepository()
    repository.assessment["question_count"] = 3
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    lessons.find_by_id = lambda _id: None
    attempt = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)
    result = submit_attempt(repository, str(repository.assessment_id), attempt["id"], {"answers": [{"question_id": question["id"], "selected_option_id": "a"} for question in attempt["questions"]]}, progress, lessons, user)
    assert result["lesson_completed"] is False


def test_submission_rejects_attempt_when_assessment_was_removed_after_start():
    repository = FakeAssessmentRepository()
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    user = {"_id": ObjectId()}
    attempt = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)
    repository.find_assessment = lambda _assessment_id: None

    with pytest.raises(NotFoundError):
        submit_attempt(repository, str(repository.assessment_id), attempt["id"], {"answers": [{"question_id": question["id"], "selected_option_id": "a"} for question in attempt["questions"]]}, progress, lessons, user)


def test_submission_rejects_missing_answers():
    repository = FakeAssessmentRepository()
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])
    user = {"_id": ObjectId()}
    attempt = start_attempt(repository, str(repository.assessment_id), progress, lessons, user)

    with pytest.raises(InvalidAssessmentAnswerError):
        submit_attempt(repository, str(repository.assessment_id), attempt["id"], {"answers": []}, progress, lessons, user)
