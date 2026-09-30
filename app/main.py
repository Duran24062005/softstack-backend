from contextlib import asynccontextmanager
import os
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.errors import PyMongoError

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "softstack")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2_000)
    app.state.mongodb_client = client
    app.state.mongodb = client[MONGODB_DATABASE]
    try:
        yield
    finally:
        client.close()


app = FastAPI(title="SoftStack Backend API", version="0.1.0", lifespan=lifespan)


@app.get("/")
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
