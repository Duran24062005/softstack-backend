"""Populate a safe, repeatable local fixture for the complete LMS flow.

The fixture is intentionally separate from ``seed_content`` so content can be
loaded in any environment without creating demo accounts or activity.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId

from app.config.config import assessment_config, database_config
from app.config.database.mongodb_connection import create_mongodb_client, initialize_indexes
from app.core.security import hash_password
from scripts.seed_content import seed_database


DEMO_NAMESPACE = "softstack.demo.v1"
DEMO_EMAIL_DOMAIN = "softstack.test"


DEMO_USERS = [
    {
        "key": "admin",
        "email": f"admin@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Mariana Torres",
        "role": "admin",
        "account_status": "active",
        "academic_profile": None,
        "created_days_ago": 120,
    },
    {
        "key": "trainer",
        "email": f"trainer@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Santiago Rojas",
        "role": "trainer",
        "account_status": "active",
        "academic_profile": None,
        "created_days_ago": 105,
    },
    {
        "key": "ana",
        "email": f"ana.martinez@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Ana Martínez",
        "role": "user",
        "account_status": "active",
        "academic_profile": {
            "start_year": 2025,
            "group_name": "Cohorte 2025 - Producto Digital",
            "campus_name": "Bucaramanga",
            "linkedin_url": "https://www.linkedin.com/in/ana-martinez-softstack",
            "github_url": "https://github.com/ana-martinez-softstack",
        },
        "created_days_ago": 92,
    },
    {
        "key": "bruno",
        "email": f"bruno.gomez@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Bruno Gómez",
        "role": "user",
        "account_status": "active",
        "academic_profile": {
            "start_year": 2025,
            "group_name": "Cohorte 2025 - Desarrollo Web",
            "campus_name": "Medellín",
            "linkedin_url": "https://www.linkedin.com/in/bruno-gomez-softstack",
            "github_url": "https://github.com/bruno-gomez-softstack",
        },
        "created_days_ago": 74,
    },
    {
        "key": "camila",
        "email": f"camila.ortiz@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Camila Ortiz",
        "role": "user",
        "account_status": "active",
        "academic_profile": {
            "start_year": 2024,
            "group_name": "Cohorte 2024 - Ingeniería de Software",
            "campus_name": "Bogotá",
            "linkedin_url": "https://www.linkedin.com/in/camila-ortiz-softstack",
            "github_url": "https://github.com/camila-ortiz-softstack",
        },
        "created_days_ago": 140,
    },
    {
        "key": "diego",
        "email": f"diego.silva@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Diego Silva",
        "role": "user",
        "account_status": "pending",
        "academic_profile": {
            "start_year": 2026,
            "group_name": "Cohorte 2026 - Base Técnica",
            "campus_name": "Cartagena",
            "linkedin_url": None,
            "github_url": "https://github.com/diego-silva-softstack",
        },
        "created_days_ago": 6,
    },
]


def _assert_demo_owned(document: dict[str, Any] | None, expected_key: str, resource: str) -> None:
    if document and document.get("demo_seed_key") != expected_key:
        raise RuntimeError(f"Refusing to overwrite non-demo {resource}: {expected_key}")


def _preflight_user_collisions(database: Any) -> None:
    for definition in DEMO_USERS:
        existing = database.users.find_one({"email": definition["email"].lower()})
        _assert_demo_owned(existing, f"{DEMO_NAMESPACE}:user:{definition['key']}", "user")


def _upsert_user(database: Any, definition: dict[str, Any], password_hash: str, now: datetime, admin_id: ObjectId | None) -> dict[str, Any]:
    email = definition["email"].lower()
    existing = database.users.find_one({"email": email})
    seed_key = f"{DEMO_NAMESPACE}:user:{definition['key']}"
    _assert_demo_owned(existing, seed_key, "user")
    created_at = now - timedelta(days=definition["created_days_ago"])
    status_changed_by = None if definition["key"] == "admin" else admin_id
    fields = {
        "demo_seed_key": seed_key,
        "full_name": definition["full_name"],
        "email": email,
        "password_hash": password_hash,
        "role": definition["role"],
        "is_active": definition["account_status"] == "active",
        "account_status": definition["account_status"],
        "status_changed_at": created_at if definition["key"] != "admin" else None,
        "status_changed_by": status_changed_by,
        "email_verified": definition["account_status"] == "active",
        "academic_profile": definition["academic_profile"],
        "updated_at": now,
    }
    if existing:
        database.users.update_one({"_id": existing["_id"]}, {"$set": fields})
        return database.users.find_one({"_id": existing["_id"]})

    document = {**fields, "created_at": created_at, "profile_photo": None}
    result = database.users.insert_one(document)
    document["_id"] = result.inserted_id
    return document


def _assessment_settings(database: Any, now: datetime) -> dict[str, Any]:
    current = database.assessment_settings.find_one({"key": "default"})
    if current:
        return current
    question_count = min(max(int(assessment_config["DEFAULT_QUESTION_COUNT"]), 3), 5)
    document = {
        "key": "default",
        "passing_score": assessment_config["DEFAULT_PASSING_SCORE"],
        "max_attempts": assessment_config["MAX_ATTEMPTS"],
        "default_question_count": question_count,
        "demo_seed_key": DEMO_NAMESPACE,
        "created_at": now,
        "updated_at": now,
    }
    database.assessment_settings.insert_one(document)
    return database.assessment_settings.find_one({"key": "default"}) or document


def _question_templates(title: str, description: str) -> list[dict[str, Any]]:
    return [
        {
            "prompt": f"¿Cuál es el propósito principal de trabajar {title.lower()}?",
            "options": [
                {"id": "a", "text": f"Convertir el aprendizaje en una decisión o evidencia aplicable: {description.lower()}"},
                {"id": "b", "text": "Memorizar una lista de términos sin relacionarlos con un contexto"},
                {"id": "c", "text": "Reemplazar la experiencia práctica por una plantilla universal"},
                {"id": "d", "text": "Evitar recibir retroalimentación hasta terminar toda la ruta"},
            ],
            "correct_option_id": "a",
            "explanation": "La ruta busca producir señales profesionales observables y conectadas con una situación real.",
            "competency": "Transferencia al contexto profesional",
            "difficulty": "basic",
        },
        {
            "prompt": f"En una situación profesional, ¿qué acción demuestra mejor dominio de {title.lower()}?",
            "options": [
                {"id": "a", "text": "Copiar una respuesta genérica sin revisar el contexto"},
                {"id": "b", "text": f"Explicar la decisión, mostrar evidencia y ajustarla al contexto de {title.lower()}"},
                {"id": "c", "text": "Presentar muchas herramientas aunque ninguna resuelva el problema"},
                {"id": "d", "text": "Esperar que otra persona traduzca la experiencia"},
            ],
            "correct_option_id": "b",
            "explanation": "El dominio se demuestra al conectar criterio, evidencia y contexto, no al repetir una fórmula.",
            "competency": "Aplicación práctica",
            "difficulty": "intermediate",
        },
        {
            "prompt": f"¿Qué señal debería revisarse antes de dar por terminada una actividad sobre {title.lower()}?",
            "options": [
                {"id": "a", "text": "La cantidad de palabras utilizadas"},
                {"id": "b", "text": "El número de herramientas mencionadas"},
                {"id": "c", "text": "La claridad, relevancia y posibilidad de verificar la evidencia"},
                {"id": "d", "text": "Si la respuesta usa exactamente la misma estructura que otra persona"},
            ],
            "correct_option_id": "c",
            "explanation": "Una evidencia útil debe ser entendible, relevante para el objetivo y comprobable.",
            "competency": "Criterio y calidad de evidencia",
            "difficulty": "intermediate",
        },
        {
            "prompt": f"¿Cuál de estas prácticas debilita una respuesta relacionada con {title.lower()}?",
            "options": [
                {"id": "a", "text": "Explicar qué problema se atendió"},
                {"id": "b", "text": "Distinguir hechos, decisiones y resultados"},
                {"id": "c", "text": "Reconocer límites y supuestos de la experiencia"},
                {"id": "d", "text": "Usar afirmaciones amplias sin ejemplos ni resultado verificable"},
            ],
            "correct_option_id": "d",
            "explanation": "Las afirmaciones sin contexto ni evidencia hacen difícil evaluar el aporte real.",
            "competency": "Comunicación precisa",
            "difficulty": "advanced",
        },
        {
            "prompt": f"Después de practicar {title.lower()}, ¿cuál es el siguiente paso más útil?",
            "options": [
                {"id": "a", "text": "Guardar una versión concreta, pedir retroalimentación y mejorarla con evidencia"},
                {"id": "b", "text": "Eliminar la práctica si no quedó perfecta en el primer intento"},
                {"id": "c", "text": "Cambiar de tema sin conservar ningún resultado"},
                {"id": "d", "text": "Publicar la primera versión sin revisar datos sensibles"},
            ],
            "correct_option_id": "a",
            "explanation": "La iteración convierte una práctica aislada en una señal profesional más sólida.",
            "competency": "Iteración y mejora",
            "difficulty": "intermediate",
        },
    ]


def _upsert_assessment(database: Any, target_type: str, target: dict[str, Any], admin_id: ObjectId, settings: dict[str, Any], now: datetime) -> dict[str, Any]:
    target_id = target["_id"]
    target_title = target["title"]
    assessment_key = f"{DEMO_NAMESPACE}:assessment:{target_type}:{target_id}"
    document = {
        "target_type": target_type,
        "target_id": target_id,
        "title": f"Evaluación: {target_title}",
        "status": "published",
        "question_count": settings.get("default_question_count", 5),
        "passing_score": settings.get("passing_score", 80),
        "max_attempts": settings.get("max_attempts", 3),
        "created_by": admin_id,
        "demo_seed_key": assessment_key,
        "updated_at": now,
    }
    existing = database.assessments.find_one({"target_type": target_type, "target_id": target_id})
    _assert_demo_owned(existing, assessment_key, "assessment")
    if existing:
        database.assessments.update_one({"_id": existing["_id"]}, {"$set": document})
        assessment = database.assessments.find_one({"_id": existing["_id"]})
    else:
        result = database.assessments.insert_one({**document, "created_at": now})
        assessment = database.assessments.find_one({"_id": result.inserted_id})
    if not assessment:
        raise RuntimeError(f"Could not seed assessment for {target_type}:{target_id}")

    for index, question in enumerate(_question_templates(target_title, target.get("description", "")), start=1):
        question_key = f"{assessment_key}:question:{index}"
        question_document = {
            "assessment_id": assessment["_id"],
            **question,
            "status": "approved",
            "created_by": admin_id,
            "source_provider": "seed",
            "source_model": None,
            "demo_seed_key": question_key,
            "updated_at": now,
        }
        existing_question = database.questions.find_one({"demo_seed_key": question_key})
        if existing_question:
            database.questions.update_one({"_id": existing_question["_id"]}, {"$set": question_document})
        else:
            database.questions.insert_one({**question_document, "created_at": now})
    return assessment


def _question_snapshot(question: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": str(question["_id"]),
        "prompt": question["prompt"],
        "options": question["options"],
        "correct_option_id": question["correct_option_id"],
        "explanation": question.get("explanation", ""),
        "competency": question.get("competency", "Comprensión del tema"),
        "difficulty": question.get("difficulty", "intermediate"),
    }


def _seed_attempt(
    database: Any,
    student_id: ObjectId,
    assessment: dict[str, Any],
    questions: list[dict[str, Any]],
    attempt_number: int,
    score: float,
    days_ago: int,
    now: datetime,
) -> None:
    selected_questions = questions[: assessment.get("question_count", 5)]
    correct_count = max(0, min(len(selected_questions), round(score / 100 * len(selected_questions))))
    snapshots = [_question_snapshot(question) for question in selected_questions]
    answers = []
    for index, snapshot in enumerate(snapshots):
        is_correct = index < correct_count
        selected_option_id = snapshot["correct_option_id"]
        if not is_correct:
            option_ids = [option["id"] for option in snapshot["options"]]
            selected_option_id = next(option_id for option_id in option_ids if option_id != snapshot["correct_option_id"])
        answers.append({
            "question_id": snapshot["question_id"],
            "selected_option_id": selected_option_id,
            "correct_option_id": snapshot["correct_option_id"],
            "is_correct": is_correct,
            "explanation": snapshot["explanation"],
            "competency": snapshot["competency"],
        })
    submitted_at = now - timedelta(days=days_ago)
    attempt_key = f"{DEMO_NAMESPACE}:attempt:{student_id}:{assessment['_id']}:{attempt_number}"
    document = {
        "assessment_id": assessment["_id"],
        "user_id": student_id,
        "cycle": 1,
        "attempt_number": attempt_number,
        "status": "submitted",
        "question_snapshots": snapshots,
        "answers": answers,
        "score": round(score, 1),
        "passed": score >= assessment.get("passing_score", 80),
        "max_attempts": assessment.get("max_attempts", 3),
        "started_at": submitted_at - timedelta(minutes=18),
        "submitted_at": submitted_at,
        "demo_seed_key": attempt_key,
    }
    existing = database.attempts.find_one({"demo_seed_key": attempt_key})
    if existing:
        database.attempts.update_one({"_id": existing["_id"]}, {"$set": document})
    else:
        database.attempts.insert_one(document)


def _save_assessment_state(database: Any, student_id: ObjectId, assessment_id: ObjectId, submitted_count: int, passed: bool, now: datetime) -> None:
    state_key = f"{DEMO_NAMESPACE}:state:{student_id}:{assessment_id}"
    existing = database.assessment_states.find_one({"user_id": student_id, "assessment_id": assessment_id})
    _assert_demo_owned(existing, state_key, "assessment state")
    database.assessment_states.update_one(
        {"user_id": student_id, "assessment_id": assessment_id},
        {
            "$set": {"cycle": 1, "submitted_count": submitted_count, "passed": passed, "active_attempt_id": None, "updated_at": now, "demo_seed_key": state_key},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


def _save_demo_reset(database: Any, student_id: ObjectId, assessment_id: ObjectId, admin_id: ObjectId, now: datetime) -> None:
    reset_key = f"{DEMO_NAMESPACE}:reset:{student_id}:{assessment_id}:2"
    state_key = f"{DEMO_NAMESPACE}:state:{student_id}:{assessment_id}"
    existing_state = database.assessment_states.find_one({"user_id": student_id, "assessment_id": assessment_id})
    _assert_demo_owned(existing_state, state_key, "assessment state")
    database.assessment_resets.update_one(
        {"demo_seed_key": reset_key},
        {
            "$set": {
                "user_id": student_id,
                "assessment_id": assessment_id,
                "admin_id": admin_id,
                "reason": "Reinicio de demostración para practicar nuevamente la competencia.",
                "cycle": 2,
                "created_at": now - timedelta(days=8),
                "demo_seed_key": reset_key,
            }
        },
        upsert=True,
    )
    database.assessment_states.update_one(
        {"user_id": student_id, "assessment_id": assessment_id},
        {
            "$set": {"cycle": 2, "submitted_count": 0, "passed": False, "active_attempt_id": None, "updated_at": now, "demo_seed_key": state_key},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


def _save_lesson_progress(database: Any, student_id: ObjectId, lesson: dict[str, Any], completed_at: datetime) -> None:
    progress_key = f"{DEMO_NAMESPACE}:progress:{student_id}:{lesson['_id']}"
    existing = database.progress.find_one({"user_id": student_id, "lesson_id": lesson["_id"]})
    _assert_demo_owned(existing, progress_key, "lesson progress")
    database.progress.update_one(
        {"user_id": student_id, "lesson_id": lesson["_id"]},
        {
            "$set": {"module_id": lesson["module_id"], "completion_source": "quiz", "completed_at": completed_at, "demo_seed_key": progress_key},
            "$setOnInsert": {"user_id": student_id, "lesson_id": lesson["_id"]},
        },
        upsert=True,
    )


def _save_module_progress(database: Any, student_id: ObjectId, module: dict[str, Any], completed_at: datetime) -> None:
    progress_key = f"{DEMO_NAMESPACE}:module-progress:{student_id}:{module['_id']}"
    existing = database.module_progress.find_one({"user_id": student_id, "module_id": module["_id"]})
    _assert_demo_owned(existing, progress_key, "module progress")
    database.module_progress.update_one(
        {"user_id": student_id, "module_id": module["_id"]},
        {
            "$set": {"completed_at": completed_at, "demo_seed_key": progress_key},
            "$setOnInsert": {"user_id": student_id, "module_id": module["_id"]},
        },
        upsert=True,
    )


def seed_demo(database: Any, password: str, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    _preflight_user_collisions(database)
    initialize_indexes(database)
    modules = seed_database(database, now)
    modules = [module for module in modules if module]
    lessons_by_module = {
        module["_id"]: list(database.lessons.find({"module_id": module["_id"], "status": "published"}).sort("order", 1))
        for module in modules
    }
    admin = _upsert_user(database, DEMO_USERS[0], hash_password(password), now, None)
    users = {admin["demo_seed_key"].split(":")[-1]: admin}
    password_hash = hash_password(password)
    for definition in DEMO_USERS[1:]:
        user = _upsert_user(database, definition, password_hash, now, admin["_id"])
        users[definition["key"]] = user

    settings = _assessment_settings(database, now)
    assessments: dict[tuple[str, ObjectId], dict[str, Any]] = {}
    for module in modules:
        assessments[("module", module["_id"])] = _upsert_assessment(database, "module", module, admin["_id"], settings, now)
        for lesson in lessons_by_module[module["_id"]]:
            assessments[("lesson", lesson["_id"])] = _upsert_assessment(database, "lesson", lesson, admin["_id"], settings, now)

    for student_key, trainer_key in (("ana", "trainer"), ("bruno", "trainer"), ("camila", "trainer")):
        assignment_key = f"{DEMO_NAMESPACE}:assignment:{users[student_key]['_id']}"
        existing_assignment = database.trainer_assignments.find_one({"student_id": users[student_key]["_id"]})
        _assert_demo_owned(existing_assignment, assignment_key, "trainer assignment")
        database.trainer_assignments.update_one(
            {"student_id": users[student_key]["_id"]},
            {
                "$set": {"trainer_id": users[trainer_key]["_id"], "assigned_by": admin["_id"], "updated_at": now, "demo_seed_key": assignment_key},
                "$setOnInsert": {"student_id": users[student_key]["_id"], "created_at": now},
            },
            upsert=True,
        )

    flat_lessons = [lesson for module in modules for lesson in lessons_by_module[module["_id"]]]
    scenarios = {
        "ana": [(0, 100, 1, 25), (1, 80, 1, 23), (2, 60, 1, 20), (2, 100, 2, 17)],
        "bruno": [(0, 80, 1, 18), (1, 60, 1, 12)],
        "camila": [(0, 100, 1, 27), (1, 100, 1, 25), (2, 80, 1, 23), (3, 80, 1, 21), (4, 100, 1, 19), (5, 70, 1, 15), (5, 100, 2, 11)],
    }
    for student_key, events in scenarios.items():
        student_id = users[student_key]["_id"]
        state_by_assessment: dict[ObjectId, tuple[int, bool]] = {}
        for index, score, attempt_number, days_ago in events:
            lesson = flat_lessons[index]
            assessment = assessments[("lesson", lesson["_id"])]
            questions = list(database.questions.find({"assessment_id": assessment["_id"], "status": "approved"}).sort("created_at", 1))
            _seed_attempt(database, student_id, assessment, questions, attempt_number, score, days_ago, now)
            passed = score >= assessment.get("passing_score", 80)
            previous = state_by_assessment.get(assessment["_id"], (0, False))
            state_by_assessment[assessment["_id"]] = (max(previous[0], attempt_number), previous[1] or passed)
            if passed:
                _save_lesson_progress(database, student_id, lesson, now - timedelta(days=days_ago))

        for assessment_id, (submitted_count, passed) in state_by_assessment.items():
            _save_assessment_state(database, student_id, assessment_id, submitted_count, passed, now)

    _save_demo_reset(
        database,
        users["bruno"]["_id"],
        assessments[("lesson", flat_lessons[1]["_id"])]["_id"],
        admin["_id"],
        now,
    )

    completed_modules = {
        "ana": [0],
        "camila": [0, 1],
    }
    for student_key, module_indexes in completed_modules.items():
        student_id = users[student_key]["_id"]
        for module_index in module_indexes:
            module = modules[module_index]
            assessment = assessments[("module", module["_id"])]
            questions = list(database.questions.find({"assessment_id": assessment["_id"], "status": "approved"}).sort("created_at", 1))
            attempt_number = 1
            _seed_attempt(database, student_id, assessment, questions, attempt_number, 100, 14 - module_index * 2, now)
            _save_assessment_state(database, student_id, assessment["_id"], attempt_number, True, now)
            _save_module_progress(database, student_id, module, now - timedelta(days=14 - module_index * 2))

    return {
        "users": len(DEMO_USERS),
        "modules": len(modules),
        "lessons": len(flat_lessons),
        "assessments": len(assessments),
        "questions": database.questions.count_documents({"demo_seed_key": {"$regex": f"^{DEMO_NAMESPACE}:"}}),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the local SoftStack demo fixture.")
    parser.add_argument("--confirm", action="store_true", help="Confirm that demo data may be written to the configured database.")
    parser.add_argument("--password", default=os.getenv("SEED_DEMO_PASSWORD"), help="Password for all demo accounts; prefer SEED_DEMO_PASSWORD.")
    args = parser.parse_args()
    if not args.confirm:
        parser.error("Refusing to write demo data without --confirm")
    if not args.password or len(args.password) < 8:
        parser.error("Provide SEED_DEMO_PASSWORD or --password with at least 8 characters")
    return args


def main() -> None:
    args = _parse_args()
    client = create_mongodb_client()
    try:
        summary = seed_demo(client[database_config["MONGODB_DATABASE"]], args.password)
        print("Seed demo completado: " + ", ".join(f"{key}={value}" for key, value in summary.items()))
    finally:
        client.close()


if __name__ == "__main__":
    main()
