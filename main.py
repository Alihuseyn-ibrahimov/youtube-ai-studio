import asyncio
import logging
import sys

from aiogram import Bot

from bot.scheduler import build_scheduler
from bot.telegram_bot import build_dispatcher
from bot.video_worker import build_video_worker
from config.settings import load_settings
from core.db import init_db
from core.llm.router import build_default_router
from core.video.factory import build_video_provider

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main() -> None:
    _configure_logging()
    settings = load_settings()

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN qurulmayıb — .env faylını yoxlayın")

    init_db(settings.db_path)
    router = build_default_router(settings)

    bot = Bot(token=settings.telegram_bot_token)
    dp = build_dispatcher(settings, router)

    scheduler = build_scheduler(bot, settings, router)
    scheduler.start()
    logger.info(
        "Scheduler başladıldı: hər gün saat %02d:00-da %d mövzu variantı generasiya olunacaq",
        settings.daily_generation_hour,
        settings.daily_variants_count,
    )

    video_provider = build_video_provider(settings)
    video_worker = build_video_worker(bot, settings, video_provider)
    video_worker.start()
    logger.info(
        "Video worker başladıldı (%s): hər %d dəqiqədə təsdiqlənmiş ssenarilər yoxlanılacaq",
        video_provider.name,
        settings.video_worker_interval_minutes,
    )

    try:
        logger.info("Bot polling rejimində başladılır...")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        video_worker.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
