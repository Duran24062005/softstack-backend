from datetime import datetime, timezone
from typing import Any

from pymongo import ReturnDocument

from app.config.config import database_config
from app.config.database.mongodb_connection import create_mongodb_client, initialize_indexes
from app.services.content_service import slugify


def _lesson(
    title: str,
    description: str,
    sections: list[tuple[str, list[str]]],
    estimated_minutes: int,
) -> dict[str, Any]:
    content: list[dict[str, Any]] = [
        {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": title}]},
        {"type": "paragraph", "content": [{"type": "text", "text": description}]},
    ]
    for heading, bullets in sections:
        content.append({"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": heading}]})
        content.append(
            {
                "type": "bulletList",
                "content": [
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": bullet}]}]}
                    for bullet in bullets
                ],
            }
        )
    return {
        "title": title,
        "description": description,
        "estimated_minutes": estimated_minutes,
        "content": {"type": "doc", "content": content},
    }


MODULES = [
    {
        "title": "Presencia Virtual y Etiqueta Profesional",
        "legacy_title": "Presencia profesional",
        "description": "Proyecta una imagen clara, confiable y profesional en cada conversación laboral.",
        "lessons": [
            _lesson(
                "Configuración del Entorno y Videollamadas",
                "Prepara una videollamada que comunique atención al detalle desde el primer minuto.",
                [
                    (
                        "Encuadre e iluminación",
                        [
                            "Ubica la cámara a la altura de los ojos y encuadra desde los hombros hacia arriba.",
                            "Usa iluminación frontal y evita que una ventana o lámpara quede detrás de ti.",
                        ],
                    ),
                    (
                        "Entorno físico vs. fondos virtuales",
                        [
                            "Mantén un espacio ordenado y evita aparecer recostado en sofás o camas.",
                            "Cuando uses Meet o Zoom, elige fondos virtuales neutros y que no distraigan.",
                        ],
                    ),
                    (
                        "Calidad de audio y etiqueta de micrófono",
                        [
                            "Prefiere auriculares y verifica el micrófono antes de entrar a la llamada.",
                            "Mantén el micrófono en silencio cuando no estés hablando y avisa si necesitas intervenir.",
                        ],
                    ),
                ],
                18,
            ),
            _lesson(
                "Código de Vestimenta e Higiene Visual (Tech & Corporate)",
                "Construye una imagen presentable y accesible sin depender de ropa costosa ni de un traje rígido.",
                [
                    (
                        "Imagen profesional accesible",
                        [
                            "Prioriza prendas limpias, cuidadas y coherentes con el contexto de la empresa.",
                            "Combina un estilo casual-elegante o tech con colores sobrios y pocas distracciones visuales.",
                        ],
                    ),
                    (
                        "Lenguaje corporal no verbal",
                        [
                            "Mantén una postura erguida y dirige la mirada a la cámara para comunicar presencia.",
                            "Usa gestos faciales naturales y regula tu energía para sostener una conversación cercana y profesional.",
                        ],
                    ),
                ],
                15,
            ),
        ],
    },
    {
        "title": "Ingeniería de CV de Alto Impacto y Filtros ATS",
        "legacy_title": "Ingeniería de CV",
        "description": "Convierte tu experiencia técnica en evidencia relevante, medible y legible para personas y sistemas ATS.",
        "lessons": [
            _lesson(
                "Estructura y Formato ATS (Applicant Tracking Systems)",
                "Diseña un CV limpio que pueda ser leído correctamente por un ATS y por un reclutador.",
                [
                    (
                        "Diseño limpio",
                        [
                            "Usa una sola columna con jerarquía tipográfica clara y secciones fáciles de escanear.",
                            "Elimina barras de nivel, íconos, gráficos y plantillas genéricas de portales de empleo.",
                        ],
                    ),
                    (
                        "Datos de contacto y atención al detalle",
                        [
                            "Incluye directamente enlaces funcionales a GitHub, LinkedIn y tu portafolio.",
                            "Revisa nombres, fechas, enlaces, ortografía y tipografía para evitar errores que resten credibilidad.",
                        ],
                    ),
                ],
                20,
            ),
            _lesson(
                "Redacción de Logros con la Fórmula Google (X-Y-Z)",
                "Transforma tareas genéricas en logros que conecten tu trabajo técnico con resultados de negocio.",
                [
                    (
                        "Enfoque en métricas de negocio",
                        [
                            "Escribe cada logro con la estructura: Logré X, medido por Y, haciendo Z.",
                            "Relaciona tus decisiones técnicas con rendimiento, latencia, conversión, calidad, costos o usuarios.",
                        ],
                    ),
                    (
                        "Estimación profesional de métricas",
                        [
                            "Calcula impactos reales usando mediciones antes y después, logs, analítica o reportes del proyecto.",
                            "Si debes proyectar una métrica, declara los supuestos y evita presentar estimaciones como datos verificados.",
                        ],
                    ),
                ],
                22,
            ),
            _lesson(
                "Curaduría y Relevancia del Contenido",
                "Selecciona la evidencia que mejor responde al rol objetivo y presenta cada experiencia con el contexto adecuado.",
                [
                    (
                        "Filtro de relevancia",
                        [
                            "Prioriza experiencias que demuestren las capacidades y tecnologías solicitadas en el rol.",
                            "Reduce o elimina trabajos no relacionados cuando ocupen espacio que podría mostrar impacto técnico.",
                        ],
                    ),
                    (
                        "Diferenciación de proyectos",
                        [
                            "Separa experiencia laboral formal de proyectos académicos, freelance o iniciativas personales.",
                            "Presenta cada proyecto con su problema, tu contribución, stack, resultado y nivel de responsabilidad.",
                        ],
                    ),
                ],
                16,
            ),
        ],
    },
    {
        "title": "Marca Personal, LinkedIn y Mercado Oculto",
        "legacy_title": "Marca personal y LinkedIn",
        "description": "Haz visible tu propuesta de valor y crea conversaciones con las personas correctas del mercado tech.",
        "lessons": [
            _lesson(
                "Optimización del Perfil de LinkedIn",
                "Convierte tu perfil en un elevator pitch escrito que explique qué sabes hacer y qué problemas resuelves.",
                [
                    (
                        "Titular y resumen (elevator pitch escrito)",
                        [
                            "Reemplaza frases vacías o poéticas por una propuesta de valor enfocada en tu stack y tus resultados.",
                            "Explica con claridad el tipo de problemas de negocio o producto que puedes ayudar a resolver.",
                        ],
                    ),
                    (
                        "Secciones clave",
                        [
                            "Organiza las habilidades por categorías como lenguajes, frameworks y bases de datos.",
                            "Optimiza experiencia y proyectos con contexto, contribución, tecnologías y resultados verificables.",
                        ],
                    ),
                ],
                20,
            ),
            _lesson(
                "Estrategia de Red de Contactos y Cold Messaging",
                "Construye relaciones profesionales que abran conversaciones antes de que aparezca una vacante pública.",
                [
                    (
                        "Abordaje al mercado oculto",
                        [
                            "Contacta directamente a reclutadores técnicos o Engineering Managers de equipos que te interesen.",
                            "Investiga el contexto de la persona y de la empresa antes de escribir para que el mensaje sea relevante.",
                        ],
                    ),
                    (
                        "Plantillas quirúrgicas de conexión",
                        [
                            "Redacta notas de conexión cortas, específicas y sin pedir trabajo de forma inmediata.",
                            "Usa mensajes directos orientados a generar una conversación o un café virtual de 15 minutos.",
                        ],
                    ),
                ],
                18,
            ),
            _lesson(
                "Portafolio Técnico y Presencia en GitHub",
                "Presenta proyectos que permitan evaluar rápidamente tu criterio técnico y tu capacidad de entregar.",
                [
                    (
                        "Documentación de proyectos",
                        [
                            "Crea README profesionales con problema, arquitectura, decisiones técnicas, instalación y demostración visual.",
                            "Incluye métricas de rendimiento como puntuaciones de Lighthouse cuando sean relevantes.",
                        ],
                    ),
                    (
                        "Despliegue en vivo",
                        [
                            "Mantén enlaces funcionales a proyectos desplegados para reducir la distancia entre explicar y demostrar.",
                            "Indica las limitaciones conocidas, datos de prueba y credenciales de demo cuando aplique.",
                        ],
                    ),
                ],
                17,
            ),
        ],
    },
    {
        "title": "Comunicación Estratégica en Entrevistas",
        "legacy_title": "Comunicación en entrevistas",
        "description": "Responde con estructura, contexto e impacto para que tus decisiones y tu forma de trabajar sean visibles.",
        "lessons": [
            _lesson(
                'La Respuesta a "Háblame de ti"',
                "Prepara un pitch personal breve que conecte tu trayectoria con el valor que puedes aportar al equipo.",
                [
                    (
                        "Estructura del pitch personal",
                        [
                            "Articula en 1 a 1.5 minutos quién eres, qué dominas tecnológicamente y qué impacto puedes generar.",
                            "Adapta el cierre al rol y evita repetir toda la historia de tu CV sin una idea central.",
                        ],
                    ),
                ],
                14,
            ),
            _lesson(
                "Entrevistas de Fit Cultural / Recursos Humanos (Método STAR)",
                "Responde preguntas conductuales con una historia concreta que permita entender tu criterio y tus resultados.",
                [
                    (
                        "Estructuración de respuestas conductuales",
                        [
                            "Organiza la respuesta con Situación, Tarea, Acción y Resultado.",
                            "Describe tu contribución específica, reconoce los retos y cierra con un resultado o aprendizaje observable.",
                        ],
                    ),
                ],
                20,
            ),
            _lesson(
                "El Cierre Estratégico de la Entrevista",
                "Termina la conversación demostrando preparación, interés genuino y criterio para evaluar el equipo.",
                [
                    (
                        "Preguntas al entrevistador",
                        [
                            "Pregunta por la cultura de ingeniería, los retos del equipo y las metodologías de trabajo.",
                            "Evita responder que no tienes preguntas; lleva un catálogo y elige las más útiles según la conversación.",
                        ],
                    ),
                    (
                        "Cierre de valor",
                        [
                            "Reafirma tu interés por la posición y conecta una fortaleza tuya con una necesidad que hayas escuchado.",
                            "Confirma los siguientes pasos y el canal adecuado para hacer seguimiento.",
                        ],
                    ),
                ],
                16,
            ),
        ],
    },
    {
        "title": "Negociación, Aspiración Salarial y Seguimiento",
        "legacy_title": "Negociación y seguimiento",
        "description": "Investiga el mercado, comunica tus expectativas y acompaña cada proceso con criterio y buena etiqueta.",
        "lessons": [
            _lesson(
                "Investigación de Mercado y Aspiración Salarial",
                "Define un rango defendible y responde preguntas salariales sin cerrar puertas ni subvalorar tu trabajo.",
                [
                    (
                        "Definición de rangos",
                        [
                            "Investiga bandas salariales según nivel de experiencia, tipo de rol y región meta.",
                            "Compara varias fuentes y considera modalidad, beneficios, moneda, seniority y alcance real del puesto.",
                        ],
                    ),
                    (
                        "Manejo de la pregunta salarial",
                        [
                            "Responde con un rango razonado y flexible, preguntando también por la banda presupuestada para el rol.",
                            "Evita dar una cifra aislada demasiado pronto o aceptar una referencia que no corresponda al alcance del trabajo.",
                        ],
                    ),
                ],
                18,
            ),
            _lesson(
                "Etiqueta Pos-Entrevista y Seguimiento",
                "Mantén activa la relación después de la entrevista sin convertir el seguimiento en presión innecesaria.",
                [
                    (
                        "Mensajes de agradecimiento",
                        [
                            "Envía un mensaje breve que agradezca el tiempo, retome un punto relevante y reafirme tu interés.",
                            "Personaliza el mensaje para cada entrevistador y evita convertirlo en una carta genérica.",
                        ],
                    ),
                    (
                        "Manejo de tiempos y bumps",
                        [
                            "Pregunta por los próximos pasos y el plazo estimado antes de terminar la entrevista.",
                            "Haz seguimiento cuando el plazo haya vencido, con un mensaje claro, amable y orientado a conocer el estado del proceso.",
                        ],
                    ),
                ],
                15,
            ),
        ],
    },
]


def _upsert_module(database, module_data: dict[str, Any], now: datetime) -> dict[str, Any]:
    slug = slugify(module_data["title"])
    existing = database.modules.find_one({"slug": slug})
    if not existing and module_data.get("legacy_title"):
        existing = database.modules.find_one({"slug": slugify(module_data["legacy_title"])})

    fields = {
        "title": module_data["title"],
        "slug": slug,
        "description": module_data["description"],
        "order": module_data["order"],
        "status": "published",
        "updated_at": now,
    }
    if existing:
        database.modules.update_one({"_id": existing["_id"]}, {"$set": fields})
        return database.modules.find_one({"_id": existing["_id"]})

    return database.modules.find_one_and_update(
        {"slug": slug},
        {
            "$set": fields,
            "$setOnInsert": {"created_by": None, "created_at": now},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )


def _upsert_lesson(
    database,
    module_id,
    module_data: dict[str, Any],
    lesson_data: dict[str, Any],
    order: int,
    now: datetime,
) -> None:
    slug = slugify(lesson_data["title"])
    existing = database.lessons.find_one({"module_id": module_id, "slug": slug})
    if not existing and order == 1 and module_data.get("legacy_title"):
        existing = database.lessons.find_one(
            {"module_id": module_id, "slug": f"primer-paso-{slugify(module_data['legacy_title'])}"}
        )

    fields = {
        "module_id": module_id,
        "title": lesson_data["title"],
        "slug": slug,
        "description": lesson_data["description"],
        "content": lesson_data["content"],
        "order": order,
        "status": "published",
        "estimated_minutes": lesson_data["estimated_minutes"],
        "updated_by": None,
        "updated_at": now,
    }
    if existing:
        database.lessons.update_one({"_id": existing["_id"]}, {"$set": fields})
        return

    database.lessons.update_one(
        {"module_id": module_id, "slug": slug},
        {
            "$set": fields,
            "$setOnInsert": {"created_by": None, "created_at": now},
        },
        upsert=True,
    )


def seed() -> None:
    client = create_mongodb_client()
    database = client[database_config["MONGODB_DATABASE"]]
    initialize_indexes(database)
    now = datetime.now(timezone.utc)
    for index, module_data in enumerate(MODULES, start=1):
        module_data["order"] = index
        module = _upsert_module(database, module_data, now)
        for lesson_order, lesson_data in enumerate(module_data["lessons"], start=1):
            _upsert_lesson(database, module["_id"], module_data, lesson_data, lesson_order, now)
    client.close()


if __name__ == "__main__":
    seed()
