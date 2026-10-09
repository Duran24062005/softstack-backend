from fastapi import Request

from app.config.database.mongodb_connection import get_database
from app.repositories.content_repository import LessonRepository, ModuleRepository, ProgressRepository
from app.repositories.assessment_repository import AssessmentRepository
from app.repositories.content_media_repository import ContentMediaRepository
from app.repositories.content_revision_repository import ContentRevisionRepository


def get_module_repository(request: Request) -> ModuleRepository:
    return ModuleRepository(get_database(request))


def get_lesson_repository(request: Request) -> LessonRepository:
    return LessonRepository(get_database(request))


def get_progress_repository(request: Request) -> ProgressRepository:
    return ProgressRepository(get_database(request))


def get_content_media_repository(request: Request) -> ContentMediaRepository:
    return ContentMediaRepository(get_database(request))


def get_content_revision_repository(request: Request) -> ContentRevisionRepository:
    return ContentRevisionRepository(get_database(request))


def get_assessment_repository(request: Request) -> AssessmentRepository:
    return AssessmentRepository(get_database(request))
