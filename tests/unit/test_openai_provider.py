"""OpenAIProvider avec un client OpenAI factice (aucun réseau)."""

import json
from types import SimpleNamespace

import pytest

from src.core.constants import FALLBACK_THEME
from src.infrastructure.llm.openai_provider import OpenAIProvider


class FakeClient:
    def __init__(self, chat_content=None, chat_error=None, embed_error=None):
        self.embed_inputs = []
        self.chat_calls = 0
        self._chat_content = chat_content
        self._chat_error = chat_error
        self._embed_error = embed_error
        self.embeddings = SimpleNamespace(create=self._embed)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat))

    async def _embed(self, input, model, **kw):  # noqa: A002
        if self._embed_error:
            raise self._embed_error
        self.embed_inputs.append(list(input))
        # renvoie volontairement dans le désordre : le provider doit trier par index
        data = [
            SimpleNamespace(embedding=[float(len(t))] * 3, index=i) for i, t in enumerate(input)
        ]
        return SimpleNamespace(data=list(reversed(data)))

    async def _chat(self, **kw):
        self.chat_calls += 1
        self.chat_kwargs = kw
        if self._chat_error:
            raise self._chat_error
        msg = SimpleNamespace(content=self._chat_content)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def make(**kw):
    provider = OpenAIProvider()
    provider.client = FakeClient(**kw)
    return provider


@pytest.mark.parametrize("text", ["", "   ", "\n"])
async def test_generate_embedding_rejects_blank(text):
    with pytest.raises(ValueError):
        await make().generate_embedding(text)


async def test_embedding_is_cached_by_content():
    p = make()
    assert await p.generate_embedding("abc") == [3.0] * 3
    assert await p.generate_embedding("abc") == [3.0] * 3
    assert len(p.client.embed_inputs) == 1


async def test_embedding_provider_error_is_wrapped():
    p = make(embed_error=RuntimeError("quota"))
    with pytest.raises(Exception, match="OpenAI Error: quota"):
        await p.generate_embedding("abc")


async def test_generate_embeddings_returns_in_input_order_in_one_call():
    p = make()
    out = await p.generate_embeddings(["a", "bb", "ccc"])
    assert out == [[1.0] * 3, [2.0] * 3, [3.0] * 3]
    assert len(p.client.embed_inputs) == 1


async def test_extract_metadata_parses_json_uses_temperature_zero_and_caches():
    content = json.dumps({"theme": "Art", "sub_themes": ["Peinture"]})
    p = make(chat_content=content)
    assert await p.extract_metadata("texte") == {"theme": "Art", "sub_themes": ["Peinture"]}
    assert p.client.chat_kwargs["temperature"] == 0
    first = await p.extract_metadata("texte")
    first["theme"] = "mutation"  # une copie est renvoyée : le cache n'est pas altéré
    assert (await p.extract_metadata("texte"))["theme"] == "Art"
    assert p.client.chat_calls == 1


@pytest.mark.parametrize("content", ["pas du json", "[1, 2]", None])
async def test_extract_metadata_falls_back_on_bad_answer_and_does_not_cache(content):
    p = make(chat_content=content)
    assert await p.extract_metadata("texte") == {"theme": FALLBACK_THEME, "sub_themes": []}
    await p.extract_metadata("texte")
    assert p.client.chat_calls == 2


async def test_extract_metadata_falls_back_on_api_error_and_empty_text():
    p = make(chat_error=RuntimeError("down"))
    assert (await p.extract_metadata("x"))["theme"] == FALLBACK_THEME
    assert await p.extract_metadata("") == {"theme": FALLBACK_THEME, "sub_themes": []}
