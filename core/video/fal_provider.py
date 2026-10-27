import asyncio

import aiohttp

from core.video.base import VideoProvider

BASE_URL = "https://queue.fal.run"
DEFAULT_MODEL_ID = "fal-ai/kling-video/v1.6/standard/text-to-video"
POLL_INTERVAL_SEC = 5
MAX_POLL_ATTEMPTS = 60  # ~5 minutes


def _map_duration(duration_sec: int) -> str:
    """Kling only accepts 5 or 10 second clips — round our scene duration to the nearest option."""
    return "5" if duration_sec <= 7 else "10"


class FalAiVideoProvider(VideoProvider):
    name = "fal.ai"

    def __init__(self, api_key: str, model_id: str = DEFAULT_MODEL_ID):
        self._api_key = api_key
        self._model_id = model_id

    def _headers(self) -> dict:
        return {"Authorization": f"Key {self._api_key}", "Content-Type": "application/json"}

    async def generate_clip(self, prompt: str, duration_sec: int, aspect_ratio: str) -> bytes:
        payload = {
            "prompt": prompt,
            "duration": _map_duration(duration_sec),
            "aspect_ratio": aspect_ratio,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BASE_URL}/{self._model_id}", json=payload, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                submit_data = await resp.json()

            status_url = submit_data["status_url"]
            response_url = submit_data["response_url"]

            for _ in range(MAX_POLL_ATTEMPTS):
                await asyncio.sleep(POLL_INTERVAL_SEC)
                async with session.get(status_url, headers=self._headers()) as resp:
                    resp.raise_for_status()
                    status_data = await resp.json()
                if status_data["status"] == "COMPLETED":
                    break
            else:
                raise TimeoutError(
                    f"fal.ai clip generation timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SEC}s"
                )

            async with session.get(response_url, headers=self._headers()) as resp:
                resp.raise_for_status()
                result_data = await resp.json()

            video_url = result_data["video"]["url"]
            async with session.get(video_url) as resp:
                resp.raise_for_status()
                return await resp.read()
