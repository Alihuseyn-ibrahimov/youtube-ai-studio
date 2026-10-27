import logging
import os

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from bot.telegram_bot import send_video_for_review
from config.settings import Settings
from core import db
from core.video.base import VideoProvider
from core.video_pipeline import build_video

logger = logging.getLogger(__name__)

VIDEO_JOB_ID = "video_worker"


def build_video_worker(bot: Bot, settings: Settings, video_provider: VideoProvider) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    async def _tick() -> None:
        idea = db.get_next_idea_for_video(settings.db_path)
        if idea is None:
            return

        db.mark_video_processing(settings.db_path, idea.id)
        try:
            video_path = os.path.join(settings.videos_dir, f"{idea.id}.mp4")
            await build_video(idea, video_provider, video_path, settings.tts_voice)
            db.mark_video_ready(settings.db_path, idea.id, video_path)
            await send_video_for_review(
                bot, int(settings.telegram_chat_id), settings, idea.id, video_path, idea.title
            )
        except Exception as exc:
            logger.exception("Video generasiyası uğursuz oldu (idea_id=%s)", idea.id)
            db.mark_video_failed(settings.db_path, idea.id, str(exc))
            try:
                await bot.send_message(
                    int(settings.telegram_chat_id),
                    f"⚠️ Video generasiya edilə bilmədi (id={idea.id}): {exc}",
                )
            except Exception:
                logger.exception("Video xəta bildirişi Telegram-a göndərilə bilmədi")

    scheduler.add_job(
        _tick,
        trigger=IntervalTrigger(minutes=settings.video_worker_interval_minutes),
        id=VIDEO_JOB_ID,
        replace_existing=True,
        max_instances=1,
    )
    return scheduler
