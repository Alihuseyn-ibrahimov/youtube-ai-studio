from config.settings import Settings
from core.video.base import VideoProvider
from core.video.fal_provider import FalAiVideoProvider
from core.video.pollinations_provider import PollinationsVideoProvider


def build_video_provider(settings: Settings) -> VideoProvider:
    provider = settings.video_provider.lower()
    if provider == "pollinations":
        return PollinationsVideoProvider()
    if provider == "fal":
        return FalAiVideoProvider(settings.fal_api_key)
    raise ValueError(f"Unknown VIDEO_PROVIDER: {settings.video_provider}")
