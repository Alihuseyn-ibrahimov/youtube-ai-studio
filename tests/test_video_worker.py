from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.video_worker import VIDEO_JOB_ID, build_video_worker
from config.settings import Settings
from core import db


def _settings(db_path: str, videos_dir: str) -> Settings:
    return Settings(
        telegram_bot_token="x",
        telegram_chat_id="123",
        gemini_api_key="",
        groq_api_key="",
        ollama_host="",
        daily_generation_hour=8,
        daily_variants_count=1,
        db_path=db_path,
        fal_api_key="",
        tts_voice="az-AZ-BabekNeural",
        video_worker_interval_minutes=2,
        videos_dir=videos_dir,
        video_provider="pollinations",
    )


@pytest.mark.asyncio
async def test_tick_does_nothing_when_no_approved_idea(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    settings = _settings(db_path, str(tmp_path / "videos"))
    bot = MagicMock()
    bot.send_message = AsyncMock()

    with patch("bot.video_worker.build_video", new=AsyncMock()) as mock_build:
        scheduler = build_video_worker(bot, settings, video_provider=MagicMock())
        job = scheduler.get_job(VIDEO_JOB_ID)
        await job.func()

    mock_build.assert_not_called()
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_tick_processes_approved_idea_and_sends_video(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    idea_id = db.create_idea(db_path, "shorts", "Test", "Script", [{"description": "s", "duration_sec": 5}])
    db.update_status(db_path, idea_id, "approved")
    settings = _settings(db_path, str(tmp_path / "videos"))
    bot = MagicMock()

    with patch("bot.video_worker.build_video", new=AsyncMock()) as mock_build, \
         patch("bot.video_worker.send_video_for_review", new=AsyncMock()) as mock_send:
        scheduler = build_video_worker(bot, settings, video_provider=MagicMock())
        job = scheduler.get_job(VIDEO_JOB_ID)
        await job.func()

    mock_build.assert_awaited_once()
    mock_send.assert_awaited_once()
    idea = db.get_by_id(db_path, idea_id)
    assert idea.video_status == "ready"


@pytest.mark.asyncio
async def test_tick_skips_ideas_already_in_progress(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    idea_id = db.create_idea(db_path, "shorts", "Test", "Script", [])
    db.update_status(db_path, idea_id, "approved")
    db.mark_video_processing(db_path, idea_id)
    settings = _settings(db_path, str(tmp_path / "videos"))
    bot = MagicMock()

    with patch("bot.video_worker.build_video", new=AsyncMock()) as mock_build:
        scheduler = build_video_worker(bot, settings, video_provider=MagicMock())
        job = scheduler.get_job(VIDEO_JOB_ID)
        await job.func()

    mock_build.assert_not_called()


@pytest.mark.asyncio
async def test_tick_marks_failed_and_notifies_on_error(tmp_path):
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    idea_id = db.create_idea(db_path, "shorts", "Test", "Script", [{"description": "s", "duration_sec": 5}])
    db.update_status(db_path, idea_id, "approved")
    settings = _settings(db_path, str(tmp_path / "videos"))
    bot = MagicMock()
    bot.send_message = AsyncMock()

    with patch("bot.video_worker.build_video", new=AsyncMock(side_effect=RuntimeError("fal.ai down"))):
        scheduler = build_video_worker(bot, settings, video_provider=MagicMock())
        job = scheduler.get_job(VIDEO_JOB_ID)
        await job.func()

    idea = db.get_by_id(db_path, idea_id)
    assert idea.video_status == "failed"
    assert "fal.ai down" in idea.video_error
    bot.send_message.assert_awaited_once()
