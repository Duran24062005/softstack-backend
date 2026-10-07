from datetime import datetime, timezone

from bson import ObjectId

from app.repositories.assessment_repository import AssessmentRepository


class Cursor(list):
    def sort(self, key, direction=1):
        return Cursor(sorted(self, key=lambda item: item.get(key) or datetime.min.replace(tzinfo=timezone.utc), reverse=direction < 0))


class Collection:
    def __init__(self):
        self.documents = []

    def _matches(self, document, query):
        for key, expected in query.items():
            value = document.get(key)
            if isinstance(expected, dict) and "$in" in expected:
                if value not in expected["$in"]:
                    return False
            elif value != expected:
                return False
        return True

    def find_one(self, query):
        return next((document for document in self.documents if self._matches(document, query)), None)

    def find(self, query):
        return Cursor([document for document in self.documents if self._matches(document, query)])

    def insert_one(self, document):
        document = dict(document)
        document.setdefault("_id", ObjectId())
        self.documents.append(document)
        return type("Result", (), {"inserted_id": document["_id"]})()

    def update_one(self, query, update, upsert=False):
        document = self.find_one(query)
        if document is None and upsert:
            document = {key: value for key, value in query.items() if not isinstance(value, dict)}
            self.documents.append(document)
        if document is None:
            return type("Result", (), {})()
        for key, values in update.get("$setOnInsert", {}).items():
            if document.get(key) is None:
                document[key] = values
        document.update(update.get("$set", {}))
        return type("Result", (), {})()

    def update_many(self, query, update):
        for document in self.documents:
            if self._matches(document, query):
                document.update(update.get("$set", {}))
        return type("Result", (), {})()


class Database:
    def __init__(self):
        self.assessments = Collection()
        self.questions = Collection()
        self.attempts = Collection()
        self.assessment_states = Collection()
        self.assessment_resets = Collection()
        self.trainer_assignments = Collection()
        self.assessment_settings = Collection()


def test_repository_persists_assessments_questions_and_filters_status():
    database = Database()
    repository = AssessmentRepository(database)
    assessment = repository.create_assessment({"target_type": "lesson", "target_id": ObjectId(), "title": "Quiz"})
    question = repository.create_question({"assessment_id": assessment["_id"], "status": "suggested", "prompt": "Pregunta"})

    assert repository.find_assessment(assessment["_id"]) == assessment
    assert repository.find_by_target("lesson", assessment["target_id"]) == assessment
    assert repository.list_questions(assessment["_id"]) == [question]
    assert repository.list_questions(assessment["_id"], "suggested") == [question]
    assert repository.update_question(question["_id"], {"status": "approved"})["status"] == "approved"
    assert repository.update_assessment(assessment["_id"], {"status": "published"})["status"] == "published"


def test_repository_state_attempts_and_reset_preserve_history():
    database = Database()
    repository = AssessmentRepository(database)
    student_id, assessment_id, admin_id = ObjectId(), ObjectId(), ObjectId()
    state = repository.save_state(student_id, assessment_id, {"cycle": 1, "submitted_count": 1, "passed": False})
    active = repository.create_attempt({"user_id": student_id, "assessment_id": assessment_id, "status": "in_progress", "attempt_number": 2})
    submitted = repository.create_attempt({"user_id": student_id, "assessment_id": assessment_id, "status": "submitted", "attempt_number": 1, "submitted_at": datetime.now(timezone.utc)})

    assert state["submitted_count"] == 1
    assert repository.find_active_attempt(student_id, assessment_id) == active
    assert repository.find_attempt(ObjectId()) is None
    assert repository.list_attempts(user_id=student_id, assessment_id=assessment_id) == [submitted, active]
    assert repository.list_attempts(student_ids=[student_id]) == [submitted, active]
    assert repository.list_attempts(assessment_id=assessment_id) == [submitted, active]

    reset = repository.reset_state(student_id, assessment_id, admin_id, "Refuerzo solicitado")

    assert reset == {"user_id": student_id, "assessment_id": assessment_id, "cycle": 2, "submitted_count": 0, "passed": False, "active_attempt_id": None, "updated_at": reset["updated_at"], "created_at": reset["created_at"]}
    assert database.attempts.find_one({"_id": active["_id"]})["status"] == "cancelled"
    assert database.attempts.find_one({"_id": submitted["_id"]})["status"] == "submitted"
    assert database.assessment_resets.documents[0]["reason"] == "Refuerzo solicitado"
    assert database.assessment_resets.documents[0]["admin_id"] == admin_id

    updated = repository.update_attempt(submitted["_id"], {"score": 100})
    assert updated["score"] == 100
    assert repository.find_attempt(submitted["_id"])["score"] == 100

    empty_reset = AssessmentRepository(Database()).reset_state(ObjectId(), ObjectId(), admin_id, None)
    assert empty_reset["cycle"] == 2


def test_repository_assignments_and_settings_are_upserted():
    database = Database()
    repository = AssessmentRepository(database)
    student_id, trainer_id, admin_id = ObjectId(), ObjectId(), ObjectId()

    assignment = repository.assign_trainer(student_id, trainer_id, admin_id)
    replacement = repository.assign_trainer(student_id, ObjectId(), admin_id)
    defaults = {"passing_score": 80, "max_attempts": 3, "default_question_count": 5}

    assert assignment["student_id"] == student_id
    assert replacement["student_id"] == student_id
    assert len(repository.students_for_trainer(replacement["trainer_id"])) == 1
    assert repository.get_settings(defaults)["default_question_count"] == 5
    assert repository.update_settings({"passing_score": 90}, defaults)["passing_score"] == 90
