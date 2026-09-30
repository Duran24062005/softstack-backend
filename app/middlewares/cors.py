from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.config import app_config


def add_cors_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config["CORS_ORIGINS"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
