import pytest

from bot import scheduler as scheduler_module
from bot.scheduler import DAILY_JOB_ID, build_scheduler
from config.settings import Settings


def _settings(**overrides) -> Settings:
    base = dict(
        telegram_bot_token="x",
        telegram_chat_id="123",
        gemini_api_key="",
        groq_api_key="",
        ollama_host="",
        daily_generation_hour=8,
        daily_variants_count=2,
        db_path=":memory:",
        fal_api_key="",
        tts_voice="az-AZ-BabekNeural",
        video_worker_interval_minutes=2,
        videos_dir="data/videos",
        video_provider="pollinations",
    )
    base.update(overrides)
    return Settings(**base)


def test_build_scheduler_registers_daily_job_at_configured_hour():
    settings = _settings(daily_generation_hour=9)

    sched = build_scheduler(bot=object(), settings=settings, router=object())

    job = sched.get_job(DAILY_JOB_ID)
    assert job is not None
    assert str(job.trigger.fields[job.trigger.FIELD_NAMES.index("hour")]) == "9"


@pytest.mark.asyncio
async def test_daily_job_calls_generate_and_send_for_each_variant(monkeypatch):
    settings = _settings(telegram_chat_id="123", daily_variants_count=2)
    calls = []

    async def fake_generate_and_send(bot, chat_id, settings_, router, format_):
        calls.append((chat_id, format_))

    monkeypatch.setattr(scheduler_module, "generate_and_send", fake_generate_and_send)

    sched = build_scheduler(bot=object(), settings=settings, router=object())
    job = sched.get_job(DAILY_JOB_ID)

    await job.func()

    assert len(calls) == 2
    assert all(chat_id == 123 for chat_id, _ in calls)
    assert all(format_ == "shorts" for _, format_ in calls)


@pytest.mark.asyncio
async def test_daily_job_logs_and_swallows_errors(monkeypatch, caplog):
    settings = _settings(telegram_chat_id="not-an-int")

    sched = build_scheduler(bot=object(), settings=settings, router=object())
    job = sched.get_job(DAILY_JOB_ID)

    with caplog.at_level("ERROR"):
        await job.func()

    assert "xəta ilə bitdi" in caplog.text
