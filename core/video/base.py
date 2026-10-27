from abc import ABC, abstractmethod


class VideoProvider(ABC):
    name: str

    @abstractmethod
    async def generate_clip(self, prompt: str, duration_sec: int, aspect_ratio: str) -> bytes:
        """Return the raw video bytes for a single clip. Raise on failure."""
