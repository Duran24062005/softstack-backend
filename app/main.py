from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app.routes.auth_routes import router as auth_router
from app.routes.content_routes import router as content_router
from app.routes.assessment_routes import router as assessment_router
from app.routes.content_media_routes import router as content_media_router
from app.routes.user_routes import router as user_router
from app.routes.content_suggestion_routes import router as content_suggestion_router
from app.core.exception import register_exception_handlers
from app.middlewares.auth_middleware import add_auth_middleware
from app.middlewares.cors import add_cors_middleware
from app.config.config import app_config, database_config
from app.config.database.mongodb_connection import create_mongodb_client, initialize_indexes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    client = create_mongodb_client()
    app.state.mongodb_client = client
    app.state.mongodb = client[database_config["MONGODB_DATABASE"]]
    try:
        initialize_indexes(app.state.mongodb)
    except PyMongoError:
        pass
    try:
        yield
    finally:
        client.close()


app = FastAPI(
    title=app_config["APP_NAME"], 
    description=app_config["DESCRIPTION"],
    version=app_config["VERSION"], 
    lifespan=lifespan,
    docs_url="/"
)
register_exception_handlers(app)
add_cors_middleware(app)
add_auth_middleware(app)
app.include_router(auth_router)
app.include_router(content_router)
app.include_router(assessment_router)
app.include_router(content_media_router)
app.include_router(user_router)
app.include_router(content_suggestion_router)


@app.get("/root")
def read_root() -> dict[str, str]:
    return {"message": "¡Servidor FastAPI funcionando!"}


@app.get("/health")
def health(request: Request) -> JSONResponse:
    response: dict[str, Any] = {"status": "ok", "database": "connected"}
    try:
        request.app.state.mongodb_client.admin.command("ping")
    except PyMongoError as error:
        response.update({"status": "degraded", "database": "unavailable", "detail": str(error)})
        return JSONResponse(status_code=503, content=response)
    return JSONResponse(status_code=200, content=response)
