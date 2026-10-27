import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.telegram_bot import DEFAULT_FORMAT, generate_and_send
from config.settings import Settings
from core.llm.router import LLMRouter

logger = logging.getLogger(__name__)

DAILY_JOB_ID = "daily_script_generation"


def build_scheduler(bot: Bot, settings: Settings, router: LLMRouter) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    async def _daily_job() -> None:
        try:
            chat_id = int(settings.telegram_chat_id)
            for _ in range(settings.daily_variants_count):
                await generate_and_send(bot, chat_id, settings, router, format_=DEFAULT_FORMAT)
        except Exception:
            logger.exception("Gündəlik generasiya job-u xəta ilə bitdi")

    scheduler.add_job(
        _daily_job,
        trigger=CronTrigger(hour=settings.daily_generation_hour, minute=0),
        id=DAILY_JOB_ID,
        replace_existing=True,
    )
    return scheduler
