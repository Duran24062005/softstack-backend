from scripts.seed_content import MODULES


def test_seed_contains_the_five_employability_modules_in_order():
    assert [module["title"] for module in MODULES] == [
        "Presencia Virtual y Etiqueta Profesional",
        "Ingeniería de CV de Alto Impacto y Filtros ATS",
        "Marca Personal, LinkedIn y Mercado Oculto",
        "Comunicación Estratégica en Entrevistas",
        "Negociación, Aspiración Salarial y Seguimiento",
    ]


def test_seed_contains_thirteen_published_lessons_with_tiptap_content():
    lessons = [lesson for module in MODULES for lesson in module["lessons"]]

    assert len(lessons) == 13
    assert len({lesson["title"] for lesson in lessons}) == len(lessons)
    assert all(lesson["content"]["type"] == "doc" for lesson in lessons)
    assert all(lesson["content"]["content"] for lesson in lessons)


def test_seed_covers_the_requested_topics():
    lesson_titles = {lesson["title"] for module in MODULES for lesson in module["lessons"]}

    assert {
        "Configuración del Entorno y Videollamadas",
        "Código de Vestimenta e Higiene Visual (Tech & Corporate)",
        "Estructura y Formato ATS (Applicant Tracking Systems)",
        "Redacción de Logros con la Fórmula Google (X-Y-Z)",
        "Curaduría y Relevancia del Contenido",
        "Optimización del Perfil de LinkedIn",
        "Estrategia de Red de Contactos y Cold Messaging",
        "Portafolio Técnico y Presencia en GitHub",
        'La Respuesta a "Háblame de ti"',
        "Entrevistas de Fit Cultural / Recursos Humanos (Método STAR)",
        "El Cierre Estratégico de la Entrevista",
        "Investigación de Mercado y Aspiración Salarial",
        "Etiqueta Pos-Entrevista y Seguimiento",
    } <= lesson_titles
