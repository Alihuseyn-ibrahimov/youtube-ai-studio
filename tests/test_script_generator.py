import pytest

from config.prompts import build_prompt
from core.llm.router import LLMRouter
from core.llm.base import LLMProvider
from core.script_generator import ScriptParseError, ScriptQualityError, generate_script


class FakeProvider(LLMProvider):
    def __init__(self, response_text: str):
        self.name = "fake"
        self._response_text = response_text
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return self._response_text


class SequenceProvider(LLMProvider):
    """Returns a different canned response on each successive call — used to
    simulate a bad attempt followed by a good one (retry behaviour)."""

    def __init__(self, responses):
        self.name = "sequence"
        self._responses = list(responses)
        self.calls = 0

    def generate(self, prompt: str) -> str:
        response = self._responses[self.calls]
        self.calls += 1
        return response


VALID_JSON = """{
  "title": "Oğuldərədə səhər süfrəsi",
  "script": "Dan yeri ağaranda çoban çadırdan çıxır...",
  "scenes": [
    {"description": "Çoban çadırdan çıxır", "duration_sec": 10},
    {"description": "Ocaqda çay dəmlənir", "duration_sec": 8}
  ]
}"""

CONTAMINATED_JSON = """{
  "title": "Çobanın Sabahı",
  "script": "Çoban günün始ətini qarşılamağa hazırlaşır.",
  "scenes": [
    {"description": "Çoban su çəkir", "duration_sec": 10}
  ]
}"""


def test_generate_script_parses_valid_json():
    router = LLMRouter([FakeProvider(VALID_JSON)])

    result = generate_script(router, "shorts")

    assert result.title == "Oğuldərədə səhər süfrəsi"
    assert "çoban" in result.script_text
    assert len(result.scenes) == 2
    assert result.scenes[0]["duration_sec"] == 10


def test_generate_script_strips_markdown_code_fence():
    fenced = f"```json\n{VALID_JSON}\n```"
    router = LLMRouter([FakeProvider(fenced)])

    result = generate_script(router, "long")

    assert result.title == "Oğuldərədə səhər süfrəsi"


def test_generate_script_raises_on_invalid_json():
    router = LLMRouter([FakeProvider("bu JSON deyil, sadəcə mətn")])

    with pytest.raises(ScriptParseError):
        generate_script(router, "shorts")


def test_generate_script_raises_on_missing_field():
    incomplete = '{"title": "Başlıq", "script": "Mətn"}'
    router = LLMRouter([FakeProvider(incomplete)])

    with pytest.raises(ScriptParseError):
        generate_script(router, "shorts")


def test_generate_script_raises_on_foreign_script_contamination():
    provider = FakeProvider(CONTAMINATED_JSON)
    router = LLMRouter([provider])

    with pytest.raises(ScriptQualityError):
        generate_script(router, "shorts")

    assert provider.calls == 3  # retried MAX_ATTEMPTS times before giving up


def test_generate_script_retries_after_contaminated_attempt():
    provider = SequenceProvider([CONTAMINATED_JSON, VALID_JSON])
    router = LLMRouter([provider])

    result = generate_script(router, "shorts")

    assert result.title == "Oğuldərədə səhər süfrəsi"
    assert provider.calls == 2


def test_generate_script_detects_contamination_in_scene_description():
    contaminated_scene = """{
      "title": "Başlıq",
      "script": "Təmiz mətn.",
      "scenes": [{"description": "Çoban гуляет kənddə", "duration_sec": 10}]
    }"""
    router = LLMRouter([FakeProvider(contaminated_scene)])

    with pytest.raises(ScriptQualityError):
        generate_script(router, "shorts")


def test_build_prompt_rejects_unknown_format():
    with pytest.raises(ValueError):
        build_prompt("medium")


def test_build_prompt_includes_format_guidance():
    prompt = build_prompt("shorts")
    assert "Shorts" in prompt
    assert "Oğuldərə" in prompt
