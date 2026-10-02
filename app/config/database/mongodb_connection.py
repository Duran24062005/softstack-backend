from collections.abc import Generator

from fastapi import Request
from pymongo import ASCENDING, MongoClient
from pymongo.database import Database

from app.config.config import database_config


def create_mongodb_client() -> MongoClient:
    return MongoClient(
        database_config["MONGODB_URI"],
        serverSelectionTimeoutMS=database_config["MONGODB_SERVER_SELECTION_TIMEOUT_MS"],
        maxPoolSize=database_config["MONGODB_MAX_POOL_SIZE"],
        minPoolSize=database_config["MONGODB_MIN_POOL_SIZE"],
    )


def get_database(request: Request) -> Database:
    return request.app.state.mongodb


def initialize_indexes(database: Database) -> None:
    database.users.create_index("email", unique=True)
    database.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
    database.refresh_tokens.create_index([("user_id", ASCENDING), ("revoked_at", ASCENDING)])
    database.email_action_tokens.create_index("token_hash", unique=True)
    database.email_action_tokens.create_index("expires_at", expireAfterSeconds=0)
    database.email_action_tokens.create_index([
        ("user_id", ASCENDING),
        ("purpose", ASCENDING),
        ("consumed_at", ASCENDING),
    ])
    database.modules.create_index("slug", unique=True)
    database.modules.create_index("media_assets.pathname")
    database.lessons.create_index([("module_id", ASCENDING), ("slug", ASCENDING)], unique=True)
    database.lessons.create_index("media_assets.pathname")
    database.progress.create_index([("user_id", ASCENDING), ("lesson_id", ASCENDING)], unique=True)
    database.progress.create_index([("user_id", ASCENDING), ("completed_at", ASCENDING)])


def close_mongodb_client(request: Request) -> None:
    request.app.state.mongodb_client.close()
