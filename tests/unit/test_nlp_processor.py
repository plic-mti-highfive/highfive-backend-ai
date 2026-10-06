import pytest

from src.core.nlp_processor import NLPManager


def test_clean_html_strips_tags_and_collapses_spaces():
    assert NLPManager.clean_html("<p>Bonjour\n\n  <b>le</b>   monde</p>") == "Bonjour le monde"


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_clean_html_empty(raw):
    assert NLPManager.clean_html(raw) == ""


def test_normalize_text_lemmatizes_and_drops_stop_words_and_punctuation():
    out = NLPManager.normalize_text("Les développeurs travaillent sur des projets passionnants !")
    tokens = out.split()
    assert "développeur" in tokens
    assert "projet" in tokens
    assert not {"les", "des", "sur", "!"} & set(tokens)


def test_normalize_text_lowercases_and_ignores_html():
    assert NLPManager.normalize_text("<h1>PYTHON</h1>") == "python"


@pytest.mark.parametrize("raw", ["", None])
def test_normalize_text_empty(raw):
    assert NLPManager.normalize_text(raw) == ""


def test_normalize_text_is_idempotent_on_its_output():
    once = NLPManager.normalize_text("Je développe des applications web modernes")
    assert NLPManager.normalize_text(once) == once


def test_build_text_from_schema_applies_templates_and_skips_empty_fields():
    schema = {"bio": "Bio : {}.", "skills": "Skills : {}.", "other": "X : {}."}
    text = NLPManager.build_text_from_schema({"bio": "", "skills": ["Python", "Docker"]}, schema)
    assert text == "Skills : python docker."


def test_build_text_from_schema_keeps_schema_order():
    schema = {"b": "B={}", "a": "A={}"}
    assert NLPManager.build_text_from_schema({"a": "python", "b": "docker"}, schema) == (
        "B=docker A=python"
    )


def test_build_text_from_schema_empty_payload():
    assert NLPManager.build_text_from_schema({}, {"a": "A={}"}) == ""


async def test_build_text_from_schema_async_matches_sync():
    schema = {"bio": "Bio : {}."}
    payload = {"bio": "Développeuse de jeux vidéo"}
    assert await NLPManager.build_text_from_schema_async(payload, schema) == (
        NLPManager.build_text_from_schema(payload, schema)
    )


def test_get_nlp_requires_initialisation(monkeypatch):
    monkeypatch.setattr(NLPManager, "_nlp", None)
    with pytest.raises(RuntimeError):
        NLPManager.get_nlp()
