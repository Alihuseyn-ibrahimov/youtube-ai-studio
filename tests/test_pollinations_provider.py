from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from core.video.pollinations_provider import (
    DEFAULT_RESOLUTION,
    RESOLUTION_BY_ASPECT_RATIO,
    PollinationsError,
    PollinationsVideoProvider,
)


class FakeResponse:
    def __init__(self, status=200, body=b""):
        self.status = status
        self._body = body

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=None, history=(), status=self.status, message="error"
            )

    async def read(self):
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakeSession:
    def __init__(self, response):
        self._response = response
        self.requested_url = None

    def get(self, url, **kwargs):
        self.requested_url = url
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def test_resolution_mapping():
    assert RESOLUTION_BY_ASPECT_RATIO["9:16"] == (1080, 1920)
    assert RESOLUTION_BY_ASPECT_RATIO["16:9"] == (1920, 1080)


@pytest.mark.asyncio
async def test_generate_clip_fetches_image_and_runs_ken_burns(tmp_path):
    provider = PollinationsVideoProvider()
    fake_session = FakeSession(FakeResponse(body=b"FAKEIMAGE"))

    def fake_ken_burns(image_path, clip_path, width, height, duration, motion=0):
        with open(clip_path, "wb") as f:
            f.write(b"FAKECLIP")

    with patch("core.video.pollinations_provider.aiohttp.ClientSession", return_value=fake_session), \
         patch.object(provider, "_ken_burns", side_effect=fake_ken_burns):
        result = await provider.generate_clip("çoban çay dəmləyir", duration_sec=8, aspect_ratio="9:16")

    assert result == b"FAKECLIP"
    assert "image.pollinations.ai" in fake_session.requested_url
    assert "width=1080" in fake_session.requested_url
    assert "height=1920" in fake_session.requested_url


@pytest.mark.asyncio
async def test_generate_clip_uses_default_resolution_for_unknown_aspect(tmp_path):
    provider = PollinationsVideoProvider()
    fake_session = FakeSession(FakeResponse(body=b"IMG"))
    captured = {}

    def fake_ken_burns(image_path, clip_path, width, height, duration, motion=0):
        captured["width"] = width
        captured["height"] = height
        captured["duration"] = duration
        open(clip_path, "wb").write(b"C")

    with patch("core.video.pollinations_provider.aiohttp.ClientSession", return_value=fake_session), \
         patch.object(provider, "_ken_burns", side_effect=fake_ken_burns):
        await provider.generate_clip("prompt", duration_sec=2, aspect_ratio="weird")

    assert (captured["width"], captured["height"]) == DEFAULT_RESOLUTION
    # duration clamped up to the minimum
    assert captured["duration"] == 3


@pytest.mark.asyncio
async def test_generate_clip_raises_on_image_http_error():
    provider = PollinationsVideoProvider()
    fake_session = FakeSession(FakeResponse(status=500))

    with patch("core.video.pollinations_provider.aiohttp.ClientSession", return_value=fake_session):
        with pytest.raises(aiohttp.ClientResponseError):
            await provider.generate_clip("prompt", duration_sec=5, aspect_ratio="16:9")


def test_ken_burns_raises_on_ffmpeg_failure(tmp_path):
    import subprocess

    failed = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="bad image")
    with patch("core.video.pollinations_provider.subprocess.run", return_value=failed):
        with pytest.raises(PollinationsError):
            PollinationsVideoProvider._ken_burns("in.jpg", "out.mp4", 1080, 1920, 5)
