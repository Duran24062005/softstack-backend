import pytest

from app.config.config import _env_int, _parse_cors_origins, _parse_csv, ai_config, assessment_config


def test_assessment_defaults_keep_the_public_contract():
    assert assessment_config["DEFAULT_PASSING_SCORE"] == 80
    assert assessment_config["MAX_ATTEMPTS"] == 3
    assert ai_config["PROVIDER"] == "deepseek"
    assert ai_config["DEEPSEEK_BASE_URL"].startswith("https://")


def test_environment_parsers_normalize_editable_values(monkeypatch):
    monkeypatch.setenv("TEST_ASSESSMENT_INT", "7")
    monkeypatch.setenv("TEST_ASSESSMENT_CSV", " Admin@Example.com, trainer@example.com ")
    monkeypatch.setenv("CORS_ORIGINS", " https://one.test/,https://two.test ")

    assert _env_int("TEST_ASSESSMENT_INT", 3) == 7
    assert _parse_csv("TEST_ASSESSMENT_CSV") == ["admin@example.com", "trainer@example.com"]
    assert _parse_cors_origins() == ["https://one.test", "https://two.test"]


def test_environment_integer_parser_fails_fast_for_invalid_configuration(monkeypatch):
    monkeypatch.setenv("TEST_ASSESSMENT_INT", "not-an-int")
    with pytest.raises(ValueError):
        _env_int("TEST_ASSESSMENT_INT", 3)
