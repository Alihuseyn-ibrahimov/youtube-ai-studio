import json
import re
from dataclasses import dataclass
from typing import List

from config.prompts import build_prompt
from core.llm.router import LLMRouter

MAX_ATTEMPTS = 3

# Unicode ranges for scripts that should never legitimately appear in Azerbaijani
# Latin-script text. LLMs (especially smaller/multilingual ones like Groq's Llama)
# occasionally leak a stray character or word from another script into otherwise
# correct output — this catches that contamination so we can retry instead of
# shipping a broken script to the video pipeline / TTS.
FOREIGN_SCRIPT_RANGES = [
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs (Chinese)
    (0x3400, 0x4DBF),  # CJK Extension A
    (0x3040, 0x309F),  # Hiragana
    (0x30A0, 0x30FF),  # Katakana
    (0xAC00, 0xD7AF),  # Hangul (Korean)
    (0x0400, 0x04FF),  # Cyrillic
    (0x0600, 0x06FF),  # Arabic
    (0x0590, 0x05FF),  # Hebrew
    (0x0E00, 0x0E7F),  # Thai
    (0x0900, 0x097F),  # Devanagari
]


class ScriptParseError(Exception):
    pass


class ScriptQualityError(Exception):
    pass


@dataclass(frozen=True)
class ScriptResult:
    title: str
    script_text: str
    scenes: List[dict]


def _extract_json(raw_text: str) -> str:
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def _parse_response(raw_text: str) -> ScriptResult:
    json_text = _extract_json(raw_text)
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ScriptParseError(
            f"LLM cavabı JSON kimi parse edilə bilmədi: {exc}\nRaw: {raw_text[:500]}"
        ) from exc

    for field in ("title", "script", "scenes"):
        if field not in data:
            raise ScriptParseError(f"LLM cavabında '{field}' sahəsi yoxdur. Raw: {raw_text[:500]}")

    return ScriptResult(title=data["title"], script_text=data["script"], scenes=data["scenes"])


def _find_foreign_characters(text: str) -> list:
    found = []
    for ch in text:
        code = ord(ch)
        if any(start <= code <= end for start, end in FOREIGN_SCRIPT_RANGES):
            found.append(ch)
    return found


def _validate_quality(result: ScriptResult) -> None:
    texts_to_check = [result.title, result.script_text] + [
        scene.get("description", "") for scene in result.scenes if isinstance(scene, dict)
    ]
    offending = []
    for text in texts_to_check:
        offending.extend(_find_foreign_characters(text))
    if offending:
        raise ScriptQualityError(
            f"Ssenari mətnində yad əlifba simvolları aşkarlandı: {offending}"
        )


def generate_script(router: LLMRouter, format: str) -> ScriptResult:
    prompt = build_prompt(format)
    last_error: Exception = ScriptParseError("generate_script called with MAX_ATTEMPTS <= 0")

    for _ in range(MAX_ATTEMPTS):
        raw_text = router.generate(prompt)
        try:
            result = _parse_response(raw_text)
            _validate_quality(result)
            return result
        except (ScriptParseError, ScriptQualityError) as exc:
            last_error = exc

    raise last_error
