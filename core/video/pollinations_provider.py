import asyncio
import os
import subprocess
import tempfile
import urllib.parse

import aiohttp

from core.video.base import VideoProvider

IMAGE_BASE_URL = "https://image.pollinations.ai/prompt/"
FPS = 30
MIN_DURATION_SEC = 3

# Cinematic quality modifiers appended to every scene prompt — the single biggest
# lever on Pollinations/flux output quality for short scene descriptions.
STYLE_SUFFIX = (
    "cinematic photography, photorealistic, natural golden-hour lighting, "
    "shallow depth of field, highly detailed, sharp focus, 8k, film grain, "
    "authentic rustic atmosphere, documentary style"
)
NEGATIVE_HINT = "no text, no watermark, no logo, no distortion, no cartoon"

RESOLUTION_BY_ASPECT_RATIO = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
}
DEFAULT_RESOLUTION = (1920, 1080)

# Number of distinct camera-motion presets in _ken_burns; scenes rotate through them
# so a multi-scene video does not feel monotonous.
MOTION_PRESETS = 4


class PollinationsError(Exception):
    pass


class PollinationsVideoProvider(VideoProvider):
    """Free, key-less video clips: a high-quality AI still image from Pollinations,
    animated with a varied ffmpeg Ken Burns (zoom + pan) effect. Fits the same
    VideoProvider contract as fal.ai."""

    name = "pollinations"

    def __init__(self, model: str = "sana"):
        self._model = model
        self._seed = 0

    async def generate_clip(self, prompt: str, duration_sec: int, aspect_ratio: str) -> bytes:
        width, height = RESOLUTION_BY_ASPECT_RATIO.get(aspect_ratio, DEFAULT_RESOLUTION)
        duration = max(duration_sec, MIN_DURATION_SEC)
        motion = self._seed % MOTION_PRESETS
        image_bytes = await self._fetch_image(prompt, width, height)

        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = os.path.join(tmp_dir, "frame.jpg")
            clip_path = os.path.join(tmp_dir, "clip.mp4")
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            await asyncio.to_thread(self._ken_burns, image_path, clip_path, width, height, duration, motion)
            with open(clip_path, "rb") as f:
                return f.read()

    async def _fetch_image(self, prompt: str, width: int, height: int) -> bytes:
        self._seed += 1
        full_prompt = f"{prompt}. {STYLE_SUFFIX}. {NEGATIVE_HINT}"
        query = urllib.parse.urlencode(
            {
                "width": width,
                "height": height,
                "nologo": "true",
                "model": self._model,
                "seed": self._seed,
            }
        )
        url = f"{IMAGE_BASE_URL}{urllib.parse.quote(full_prompt)}?{query}"
        headers = {"User-Agent": "youtube-ai-studio/1.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.read()

    @classmethod
    def _ken_burns(cls, image_path: str, clip_path: str, width: int, height: int, duration: int, motion: int = 0) -> None:
        frames = duration * FPS
        cx = "iw/2-(iw/zoom/2)"
        cy = "ih/2-(ih/zoom/2)"
        zoom_in = "min(zoom+0.0015,1.18)"
        progress = f"on/{max(frames - 1, 1)}"
        if motion == 1:  # zoom in + pan right
            x, y = f"(iw-iw/zoom)*({progress})", cy
        elif motion == 2:  # zoom in + pan left
            x, y = f"(iw-iw/zoom)*(1-{progress})", cy
        elif motion == 3:  # zoom in + pan up
            x, y = cx, f"(ih-ih/zoom)*(1-{progress})"
        else:  # slow zoom in, centered
            x, y = cx, cy
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            f"zoompan=z='{zoom_in}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={FPS}"
        )
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-loop", "1", "-i", image_path,
                "-vf", vf, "-t", str(duration),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", clip_path,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise PollinationsError(f"ffmpeg Ken Burns failed: {result.stderr[-2000:]}")
