import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    gemini_api_key: str
    groq_api_key: str
    ollama_host: str
    daily_generation_hour: int
    daily_variants_count: int
    db_path: str
    fal_api_key: str
    tts_voice: str
    video_worker_interval_minutes: int
    videos_dir: str
    video_provider: str


def load_settings() -> Settings:
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        daily_generation_hour=int(os.getenv("DAILY_GENERATION_HOUR", "8")),
        daily_variants_count=int(os.getenv("DAILY_VARIANTS_COUNT", "2")),
        db_path=os.getenv("DB_PATH", "data/youtube_studio.db"),
        fal_api_key=os.getenv("FAL_API_KEY", ""),
        tts_voice=os.getenv("TTS_VOICE", "az-AZ-BanuNeural"),
        video_worker_interval_minutes=int(os.getenv("VIDEO_WORKER_INTERVAL_MINUTES", "2")),
        videos_dir=os.getenv("VIDEOS_DIR", "data/videos"),
        video_provider=os.getenv("VIDEO_PROVIDER", "pollinations"),
    )
