from fastapi import Request

from app.config.database.mongodb_connection import get_database
from app.repositories.content_repository import LessonRepository, ModuleRepository, ProgressRepository


def get_module_repository(request: Request) -> ModuleRepository:
    return ModuleRepository(get_database(request))


def get_lesson_repository(request: Request) -> LessonRepository:
    return LessonRepository(get_database(request))


def get_progress_repository(request: Request) -> ProgressRepository:
    return ProgressRepository(get_database(request))
