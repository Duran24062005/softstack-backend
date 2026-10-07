import pytest
from pydantic import ValidationError

from app.models.auth import UserRole
from app.schemas.assessment import (
    AssessmentResponse,
    AssessmentSettingsResponse,
    AssessmentSettingsUpdate,
    AttemptSubmitRequest,
    GenerateSuggestionsRequest,
    QuestionCreateRequest,
    QuestionOption,
    RoleUpdateRequest,
)


def valid_question(**changes):
    value = {
        "prompt": "¿Qué demuestra mejor comprensión del tema?",
        "options": [
            {"id": "a", "text": "Aplicar el concepto"},
            {"id": "b", "text": "Repetir una palabra"},
            {"id": "c", "text": "Ignorar el contexto"},
            {"id": "d", "text": "Evitar la práctica"},
        ],
        "correct_option_id": "a",
    }
    value.update(changes)
    return value


def test_question_contract_requires_four_unique_options_and_correct_answer():
    question = QuestionCreateRequest.model_validate(valid_question())
    assert len(question.options) == 4
    assert question.correct_option_id == "a"

    with pytest.raises(ValidationError):
        QuestionCreateRequest.model_validate(valid_question(options=[QuestionOption(id="a", text="Solo una")]))

    with pytest.raises(ValidationError):
        QuestionCreateRequest.model_validate(valid_question(options=[
            {"id": "a", "text": "Uno"},
            {"id": "a", "text": "Dos"},
            {"id": "c", "text": "Tres"},
            {"id": "d", "text": "Cuatro"},
        ]))

    with pytest.raises(ValidationError):
        QuestionCreateRequest.model_validate(valid_question(correct_option_id="z"))


@pytest.mark.parametrize("passing_score", [0, 101])
def test_settings_reject_scores_outside_one_to_one_hundred(passing_score):
    with pytest.raises(ValidationError):
        AssessmentSettingsUpdate(passing_score=passing_score)


@pytest.mark.parametrize("question_count", [2, 6])
def test_settings_reject_question_counts_outside_three_to_five(question_count):
    with pytest.raises(ValidationError):
        AssessmentSettingsUpdate(default_question_count=question_count)


def test_attempt_limit_is_a_non_editable_contract_of_exactly_three():
    assert AssessmentSettingsResponse(passing_score=80, default_question_count=5).max_attempts == 3
    assert AssessmentResponse(
        id="assessment",
        target_type="lesson",
        target_id="lesson",
        title="Quiz",
        status="published",
        question_count=5,
        passing_score=80,
        approved_question_count=5,
    ).max_attempts == 3

    with pytest.raises(ValidationError):
        AssessmentSettingsResponse(passing_score=80, default_question_count=5, max_attempts=2)


def test_request_contracts_bound_generation_and_submission_sizes():
    assert GenerateSuggestionsRequest(count=3).count == 3
    assert GenerateSuggestionsRequest(count=10).count == 10
    with pytest.raises(ValidationError):
        GenerateSuggestionsRequest(count=2)
    with pytest.raises(ValidationError):
        GenerateSuggestionsRequest(count=11)

    with pytest.raises(ValidationError):
        AttemptSubmitRequest(answers=[])


def test_public_registration_role_is_not_a_trainer_or_admin_contract():
    assert UserRole.USER.value == "user"
    assert UserRole.TRAINER.value == "trainer"
    assert UserRole.ADMIN.value == "admin"
    assert RoleUpdateRequest(role="trainer").role == "trainer"
    with pytest.raises(ValidationError):
        RoleUpdateRequest(role="admin")
