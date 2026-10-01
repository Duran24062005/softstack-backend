from fastapi import APIRouter, Depends, status

from app.middlewares.role_middleware import require_roles
from app.repositories.content_repository import LessonRepository, ModuleRepository, ProgressRepository
from app.routes.content_dependencies import get_lesson_repository, get_module_repository, get_progress_repository
from app.routes.dependencies import current_user
from app.schemas.content import (LessonCreateRequest, LessonResponse, LessonUpdateRequest, ModuleCreateRequest, ModuleResponse, ModuleUpdateRequest, ProgressSummaryResponse)
from app.services.content_service import (complete_lesson, create_lesson, create_module, get_admin_module, get_lesson, get_module, get_progress, list_admin_module_lessons, list_admin_modules, list_module_lessons, list_modules, update_lesson, update_module)

router = APIRouter(tags=["learning"])
admin = require_roles("admin")


@router.get("/modules", response_model=list[ModuleResponse])
def modules(repository: ModuleRepository = Depends(get_module_repository)):
    return list_modules(repository)


@router.get("/modules/{module_id}", response_model=ModuleResponse)
def module(module_id: str, repository: ModuleRepository = Depends(get_module_repository)):
    return get_module(repository, module_id)


@router.get("/admin/modules", response_model=list[ModuleResponse])
def admin_modules(_: dict = Depends(admin), repository: ModuleRepository = Depends(get_module_repository)):
    return list_admin_modules(repository)


@router.get("/admin/modules/{module_id}", response_model=ModuleResponse)
def admin_module(module_id: str, _: dict = Depends(admin), repository: ModuleRepository = Depends(get_module_repository)):
    return get_admin_module(repository, module_id)


@router.get("/admin/modules/{module_id}/lessons", response_model=list[LessonResponse])
def admin_module_lessons(module_id: str, _: dict = Depends(admin), modules_repository: ModuleRepository = Depends(get_module_repository), lessons_repository: LessonRepository = Depends(get_lesson_repository)):
    return list_admin_module_lessons(modules_repository, lessons_repository, module_id)


@router.get("/modules/{module_id}/lessons", response_model=list[LessonResponse])
def module_lessons(module_id: str, modules_repository: ModuleRepository = Depends(get_module_repository), lessons_repository: LessonRepository = Depends(get_lesson_repository)):
    return list_module_lessons(modules_repository, lessons_repository, module_id)


@router.get("/lessons/{lesson_id}", response_model=LessonResponse)
def lesson(lesson_id: str, repository: LessonRepository = Depends(get_lesson_repository)):
    return get_lesson(repository, lesson_id)


@router.post("/admin/modules", response_model=ModuleResponse, status_code=status.HTTP_201_CREATED)
def create_admin_module(payload: ModuleCreateRequest, user=Depends(admin), repository: ModuleRepository = Depends(get_module_repository)):
    return create_module(repository, payload, user)


@router.patch("/admin/modules/{module_id}", response_model=ModuleResponse)
def update_admin_module(module_id: str, payload: ModuleUpdateRequest, _: dict = Depends(admin), repository: ModuleRepository = Depends(get_module_repository)):
    return update_module(repository, module_id, payload)


@router.post("/admin/modules/{module_id}/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
def create_admin_lesson(module_id: str, payload: LessonCreateRequest, user=Depends(admin), modules_repository: ModuleRepository = Depends(get_module_repository), lessons_repository: LessonRepository = Depends(get_lesson_repository)):
    return create_lesson(modules_repository, lessons_repository, module_id, payload, user)


@router.patch("/admin/lessons/{lesson_id}", response_model=LessonResponse)
def update_admin_lesson(lesson_id: str, payload: LessonUpdateRequest, user=Depends(admin), repository: LessonRepository = Depends(get_lesson_repository)):
    return update_lesson(repository, lesson_id, payload, user)


@router.get("/admin/lessons/{lesson_id}", response_model=LessonResponse)
def get_admin_lesson(lesson_id: str, _: dict = Depends(admin), repository: LessonRepository = Depends(get_lesson_repository)):
    return get_lesson(repository, lesson_id, include_drafts=True)


@router.get("/me/progress", response_model=ProgressSummaryResponse)
def progress(user=Depends(current_user), progress_repository: ProgressRepository = Depends(get_progress_repository), lessons_repository: LessonRepository = Depends(get_lesson_repository)):
    return get_progress(progress_repository, lessons_repository, user)


@router.post("/lessons/{lesson_id}/complete", response_model=ProgressSummaryResponse)
def complete(lesson_id: str, user=Depends(current_user), progress_repository: ProgressRepository = Depends(get_progress_repository), lessons_repository: LessonRepository = Depends(get_lesson_repository)):
    return complete_lesson(lessons_repository, progress_repository, lesson_id, user)
