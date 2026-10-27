from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.telegram_bot import _build_keyboard, _build_video_keyboard, generate_and_send, send_video_for_review
from config.settings import Settings
from core import db
from core.llm.base import LLMProvider
from core.llm.router import LLMRouter


class FakeProvider(LLMProvider):
    def __init__(self, response_text: str):
        self.name = "fake"
        self._response_text = response_text

    def generate(self, prompt: str) -> str:
        return self._response_text


VALID_JSON = """{
  "title": "Test başlıq",
  "script": "Test ssenari mətni",
  "scenes": [{"description": "səhnə", "duration_sec": 5}]
}"""


def _settings(db_path: str) -> Settings:
    return Settings(
        telegram_bot_token="x",
        telegram_chat_id="1",
        gemini_api_key="",
        groq_api_key="",
        ollama_host="",
        daily_generation_hour=8,
        daily_variants_count=1,
        db_path=db_path,
        fal_api_key="",
        tts_voice="az-AZ-BabekNeural",
        video_worker_interval_minutes=2,
        videos_dir="data/videos",
        video_provider="pollinations",
    )


def test_build_keyboard_has_three_buttons():
    markup = _build_keyboard(idea_id=42)
    buttons = [btn for row in markup.inline_keyboard for btn in row]

    assert len(buttons) == 3
    assert buttons[0].callback_data == "approve:42"
    assert buttons[1].callback_data == "reject:42"
    assert buttons[2].callback_data == "regenerate:42"


@pytest.mark.asyncio
async def test_generate_and_send_creates_idea_and_sends_message(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    settings = _settings(db_path)
    router = LLMRouter([FakeProvider(VALID_JSON)])

    bot = MagicMock()
    sent_message = MagicMock()
    sent_message.message_id = 999
    bot.send_message = AsyncMock(return_value=sent_message)

    await generate_and_send(bot, chat_id=1, settings=settings, router=router, format_="shorts")

    bot.send_message.assert_awaited_once()
    call_args, call_kwargs = bot.send_message.call_args
    assert call_args[0] == 1
    assert "Test başlıq" in call_args[1]
    assert call_kwargs["reply_markup"] is not None

    idea = db.get_by_telegram_message_id(db_path, 999)
    assert idea is not None
    assert idea.title == "Test başlıq"
    assert idea.status == "pending"


@pytest.mark.asyncio
async def test_generate_and_send_sends_warning_on_failure(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    settings = _settings(db_path)
    router = LLMRouter([FakeProvider("bu JSON deyil, sadəcə mətn")])

    bot = MagicMock()
    bot.send_message = AsyncMock()

    await generate_and_send(bot, chat_id=1, settings=settings, router=router, format_="shorts")

    bot.send_message.assert_awaited_once()
    call_args, _ = bot.send_message.call_args
    assert "generasiya edilə bilmədi" in call_args[1]
    assert db.get_approved(db_path) == []


def test_build_video_keyboard_has_three_buttons():
    markup = _build_video_keyboard(idea_id=7)
    buttons = [btn for row in markup.inline_keyboard for btn in row]

    assert len(buttons) == 3
    assert buttons[0].callback_data == "video_approve:7"
    assert buttons[1].callback_data == "video_reject:7"
    assert buttons[2].callback_data == "video_regenerate:7"


@pytest.mark.asyncio
async def test_send_video_for_review_sends_video_and_stores_message_id(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    settings = _settings(db_path)
    idea_id = db.create_idea(db_path, "shorts", "Video başlıq", "S", [])

    video_path = tmp_path / "1.mp4"
    video_path.write_bytes(b"fake video bytes")

    bot = MagicMock()
    sent_message = MagicMock()
    sent_message.message_id = 555
    bot.send_video = AsyncMock(return_value=sent_message)

    await send_video_for_review(bot, chat_id=1, settings=settings, idea_id=idea_id, video_path=str(video_path), title="Video başlıq")

    bot.send_video.assert_awaited_once()
    call_args, call_kwargs = bot.send_video.call_args
    assert call_args[0] == 1
    assert "Video başlıq" in call_kwargs["caption"]
    assert call_kwargs["reply_markup"] is not None

    idea = db.get_by_video_telegram_message_id(db_path, 555)
    assert idea is not None
    assert idea.id == idea_id
