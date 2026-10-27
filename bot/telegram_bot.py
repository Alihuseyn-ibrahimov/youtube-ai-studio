import logging
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.settings import Settings
from core import db
from core.llm.router import AllProvidersFailedError, LLMRouter
from core.script_generator import ScriptParseError, ScriptQualityError, generate_script

logger = logging.getLogger(__name__)

DEFAULT_FORMAT = "shorts"


def build_dispatcher(settings: Settings, router: LLMRouter) -> Dispatcher:
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def handle_start(message: Message) -> None:
        await message.answer(
            "Salam! Mən Oğuldərə kənd/çoban kanalı üçün mövzu və ssenari "
            "generasiya edən botam.\n\n/generate — yeni mövzu təklifi al"
        )

    @dp.message(Command("generate"))
    async def handle_generate(message: Message) -> None:
        await generate_and_send(message.bot, message.chat.id, settings, router, format_=DEFAULT_FORMAT)

    @dp.callback_query(F.data.startswith("approve:"))
    async def handle_approve(callback: CallbackQuery) -> None:
        idea_id = int(callback.data.split(":", 1)[1])
        db.update_status(settings.db_path, idea_id, "approved")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply("✅ Təsdiqləndi.")
        await callback.answer()

    @dp.callback_query(F.data.startswith("reject:"))
    async def handle_reject(callback: CallbackQuery) -> None:
        idea_id = int(callback.data.split(":", 1)[1])
        db.update_status(settings.db_path, idea_id, "rejected")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply("❌ Rədd edildi.")
        await callback.answer()

    @dp.callback_query(F.data.startswith("regenerate:"))
    async def handle_regenerate(callback: CallbackQuery) -> None:
        idea_id = int(callback.data.split(":", 1)[1])
        idea = db.get_by_id(settings.db_path, idea_id)
        db.update_status(settings.db_path, idea_id, "rejected")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("Yenidən generasiya olunur...")
        format_ = idea.format if idea else DEFAULT_FORMAT
        await generate_and_send(callback.message.bot, callback.message.chat.id, settings, router, format_=format_)

    @dp.callback_query(F.data.startswith("video_approve:"))
    async def handle_video_approve(callback: CallbackQuery) -> None:
        idea_id = int(callback.data.split(":", 1)[1])
        db.update_video_status(settings.db_path, idea_id, "approved")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply("✅ Video təsdiqləndi.")
        await callback.answer()

    @dp.callback_query(F.data.startswith("video_reject:"))
    async def handle_video_reject(callback: CallbackQuery) -> None:
        idea_id = int(callback.data.split(":", 1)[1])
        db.update_video_status(settings.db_path, idea_id, "rejected")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply("❌ Video rədd edildi.")
        await callback.answer()

    @dp.callback_query(F.data.startswith("video_regenerate:"))
    async def handle_video_regenerate(callback: CallbackQuery) -> None:
        idea_id = int(callback.data.split(":", 1)[1])
        db.reset_video_status(settings.db_path, idea_id)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("Video yenidən növbəyə qoyuldu, bir neçə dəqiqəyə hazırlanacaq.")

    return dp


def _build_keyboard(idea_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Təsdiqlə", callback_data=f"approve:{idea_id}")
    builder.button(text="❌ Rədd et", callback_data=f"reject:{idea_id}")
    builder.button(text="🔄 Yenidən", callback_data=f"regenerate:{idea_id}")
    builder.adjust(3)
    return builder.as_markup()


def _build_video_keyboard(idea_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Təsdiqlə", callback_data=f"video_approve:{idea_id}")
    builder.button(text="❌ Rədd et", callback_data=f"video_reject:{idea_id}")
    builder.button(text="🔄 Yenidən", callback_data=f"video_regenerate:{idea_id}")
    builder.adjust(3)
    return builder.as_markup()


async def send_video_for_review(
    bot: Bot, chat_id: int, settings: Settings, idea_id: int, video_path: str, title: str
) -> None:
    video_file = FSInputFile(video_path)
    message = await bot.send_video(
        chat_id,
        video_file,
        caption=f"🎬 {escape(title)}\n\nVideo hazırdır, təsdiqləyin:",
        reply_markup=_build_video_keyboard(idea_id),
    )
    db.set_video_telegram_message_id(settings.db_path, idea_id, message.message_id)


async def generate_and_send(bot: Bot, chat_id: int, settings: Settings, router: LLMRouter, format_: str) -> None:
    try:
        result = generate_script(router, format_)
    except (AllProvidersFailedError, ScriptParseError, ScriptQualityError) as exc:
        logger.error("Ssenari generasiyası uğursuz oldu: %s", exc)
        await bot.send_message(chat_id, f"⚠️ Mövzu generasiya edilə bilmədi: {exc}")
        return

    idea_id = db.create_idea(settings.db_path, format_, result.title, result.script_text, result.scenes)
    text = f"🎬 <b>{escape(result.title)}</b>\n\n{escape(result.script_text)}"
    message = await bot.send_message(
        chat_id, text, reply_markup=_build_keyboard(idea_id), parse_mode="HTML"
    )
    db.set_telegram_message_id(settings.db_path, idea_id, message.message_id)
