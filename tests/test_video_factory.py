import pytest

from config.settings import Settings
from core.video.factory import build_video_provider
from core.video.fal_provider import FalAiVideoProvider
from core.video.pollinations_provider import PollinationsVideoProvider


def _settings(video_provider: str) -> Settings:
    return Settings(
        telegram_bot_token="x",
        telegram_chat_id="1",
        gemini_api_key="",
        groq_api_key="",
        ollama_host="",
        daily_generation_hour=8,
        daily_variants_count=1,
        db_path=":memory:",
        fal_api_key="k",
        tts_voice="az-AZ-BabekNeural",
        video_worker_interval_minutes=2,
        videos_dir="data/videos",
        video_provider=video_provider,
    )


def test_factory_builds_pollinations():
    provider = build_video_provider(_settings("pollinations"))
    assert isinstance(provider, PollinationsVideoProvider)


def test_factory_builds_fal():
    provider = build_video_provider(_settings("fal"))
    assert isinstance(provider, FalAiVideoProvider)


def test_factory_is_case_insensitive():
    assert isinstance(build_video_provider(_settings("Pollinations")), PollinationsVideoProvider)


def test_factory_raises_on_unknown_provider():
    with pytest.raises(ValueError):
        build_video_provider(_settings("midjourney"))
