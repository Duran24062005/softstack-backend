from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.database import Database


class AssessmentRepository:
    def __init__(self, database: Database):
        self.database = database
        self.assessments = database.assessments
        self.questions = database.questions
        self.attempts = database.attempts
        self.states = database.assessment_states
        self.resets = database.assessment_resets
        self.assignments = database.trainer_assignments
        self.settings = database.assessment_settings

    def find_assessment(self, assessment_id: ObjectId) -> dict[str, Any] | None:
        return self.assessments.find_one({"_id": assessment_id})

    def find_by_target(self, target_type: str, target_id: ObjectId) -> dict[str, Any] | None:
        return self.assessments.find_one({"target_type": target_type, "target_id": target_id})

    def create_assessment(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.assessments.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update_assessment(self, assessment_id: ObjectId, changes: dict[str, Any]) -> dict[str, Any] | None:
        self.assessments.update_one(
            {"_id": assessment_id},
            {"$set": {**changes, "updated_at": datetime.now(timezone.utc)}},
        )
        return self.find_assessment(assessment_id)

    def list_questions(self, assessment_id: ObjectId, status: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"assessment_id": assessment_id}
        if status:
            query["status"] = status
        return list(self.questions.find(query).sort("created_at", 1))

    def find_question(self, question_id: ObjectId) -> dict[str, Any] | None:
        return self.questions.find_one({"_id": question_id})

    def create_question(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.questions.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update_question(self, question_id: ObjectId, changes: dict[str, Any]) -> dict[str, Any] | None:
        self.questions.update_one(
            {"_id": question_id},
            {"$set": {**changes, "updated_at": datetime.now(timezone.utc)}},
        )
        return self.find_question(question_id)

    def find_state(self, user_id: ObjectId, assessment_id: ObjectId) -> dict[str, Any] | None:
        return self.states.find_one({"user_id": user_id, "assessment_id": assessment_id})

    def save_state(self, user_id: ObjectId, assessment_id: ObjectId, changes: dict[str, Any]) -> dict[str, Any]:
        self.states.update_one(
            {"user_id": user_id, "assessment_id": assessment_id},
            {"$set": {**changes, "updated_at": datetime.now(timezone.utc)}, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        return self.find_state(user_id, assessment_id) or {}

    def find_attempt(self, attempt_id: ObjectId) -> dict[str, Any] | None:
        return self.attempts.find_one({"_id": attempt_id})

    def find_active_attempt(self, user_id: ObjectId, assessment_id: ObjectId) -> dict[str, Any] | None:
        return self.attempts.find_one({"user_id": user_id, "assessment_id": assessment_id, "status": "in_progress"})

    def create_attempt(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.attempts.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update_attempt(self, attempt_id: ObjectId, changes: dict[str, Any]) -> dict[str, Any] | None:
        self.attempts.update_one({"_id": attempt_id}, {"$set": changes})
        return self.find_attempt(attempt_id)

    def list_attempts(self, user_id: ObjectId | None = None, assessment_id: ObjectId | None = None, student_ids: list[ObjectId] | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if user_id:
            query["user_id"] = user_id
        if assessment_id:
            query["assessment_id"] = assessment_id
        if student_ids is not None:
            query["user_id"] = {"$in": student_ids}
        return list(self.attempts.find(query).sort("submitted_at", -1))

    def reset_state(self, user_id: ObjectId, assessment_id: ObjectId, admin_id: ObjectId, reason: str | None) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        state = self.find_state(user_id, assessment_id) or {"cycle": 1}
        next_cycle = int(state.get("cycle", 1)) + 1
        self.attempts.update_many(
            {"user_id": user_id, "assessment_id": assessment_id, "status": "in_progress"},
            {"$set": {"status": "cancelled", "cancelled_at": now, "cancelled_by": admin_id}},
        )
        self.save_state(user_id, assessment_id, {"cycle": next_cycle, "submitted_count": 0, "passed": False, "active_attempt_id": None})
        self.resets.insert_one({"user_id": user_id, "assessment_id": assessment_id, "admin_id": admin_id, "reason": reason or "", "cycle": next_cycle, "created_at": now})
        return self.find_state(user_id, assessment_id) or {}

    def assignment_for_student(self, student_id: ObjectId) -> dict[str, Any] | None:
        return self.assignments.find_one({"student_id": student_id})

    def assign_trainer(self, student_id: ObjectId, trainer_id: ObjectId, admin_id: ObjectId) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        self.assignments.update_one(
            {"student_id": student_id},
            {"$set": {"student_id": student_id, "trainer_id": trainer_id, "assigned_by": admin_id, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return self.assignment_for_student(student_id) or {}

    def students_for_trainer(self, trainer_id: ObjectId) -> list[ObjectId]:
        return [document["student_id"] for document in self.assignments.find({"trainer_id": trainer_id})]

    def get_settings(self, defaults: dict[str, Any]) -> dict[str, Any]:
        current = self.settings.find_one({"key": "default"})
        if current:
            return current
        document = {"key": "default", **defaults, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
        self.settings.update_one({"key": "default"}, {"$setOnInsert": document}, upsert=True)
        return self.settings.find_one({"key": "default"}) or document

    def update_settings(self, changes: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
        self.get_settings(defaults)
        self.settings.update_one({"key": "default"}, {"$set": {**changes, "updated_at": datetime.now(timezone.utc)}})
        return self.settings.find_one({"key": "default"}) or {}
