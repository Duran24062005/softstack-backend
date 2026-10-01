from datetime import datetime, timezone

from pymongo import ReturnDocument

from app.config.config import database_config
from app.config.database.mongodb_connection import create_mongodb_client, initialize_indexes


MODULES = [
    ("Presencia profesional", "Construye una presencia clara y confiable para cada conversación profesional."),
    ("Ingeniería de CV", "Convierte experiencia técnica en logros que se entienden y se recuerdan."),
    ("Marca personal y LinkedIn", "Haz visible tu propuesta de valor y amplía tu red con intención."),
    ("Comunicación en entrevistas", "Practica respuestas con estructura, contexto e impacto."),
    ("Negociación y seguimiento", "Cierra procesos con criterio, claridad y buen seguimiento."),
]


def seed() -> None:
    client = create_mongodb_client()
    database = client[database_config["MONGODB_DATABASE"]]
    initialize_indexes(database)
    now = datetime.now(timezone.utc)
    for index, (title, description) in enumerate(MODULES, start=1):
        slug = title.lower().replace(" ", "-").replace("ó", "o").replace("í", "i")
        module = database.modules.find_one_and_update(
            {"slug": slug},
            {"$setOnInsert": {"title": title, "slug": slug, "description": description, "order": index, "status": "published", "created_by": None, "created_at": now, "updated_at": now}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        module_id = module["_id"]
        lesson_title = f"Primer paso en {title}"
        database.lessons.update_one(
            {"module_id": module_id, "slug": f"primer-paso-{slug}"},
            {"$setOnInsert": {"module_id": module_id, "title": lesson_title, "slug": f"primer-paso-{slug}", "description": f"Una introducción práctica a {title.lower()}.", "content": {"type": "doc", "content": [{"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": lesson_title}]}, {"type": "paragraph", "content": [{"type": "text", "text": f"Empieza a trabajar tu {title.lower()} con una acción concreta y medible."}]}]}, "order": 1, "status": "published", "estimated_minutes": 12, "created_by": None, "updated_by": None, "created_at": now, "updated_at": now}},
            upsert=True,
        )
    client.close()


if __name__ == "__main__":
    seed()
