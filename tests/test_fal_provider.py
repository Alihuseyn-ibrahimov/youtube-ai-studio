from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from core.video.fal_provider import DEFAULT_MODEL_ID, FalAiVideoProvider, _map_duration


def test_map_duration_rounds_to_nearest_allowed_value():
    assert _map_duration(5) == "5"
    assert _map_duration(7) == "5"
    assert _map_duration(8) == "10"
    assert _map_duration(15) == "10"


class FakeResponse:
    def __init__(self, status=200, json_data=None, body=b""):
        self.status = status
        self._json_data = json_data
        self._body = body

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=None, history=(), status=self.status, message="error"
            )

    async def json(self):
        return self._json_data

    async def read(self):
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakeSession:
    """Routes post()/get() calls to canned responses keyed by URL, in call order per URL."""

    def __init__(self, responses_by_url: dict):
        self._responses_by_url = {url: list(responses) for url, responses in responses_by_url.items()}

    def post(self, url, **kwargs):
        return self._responses_by_url[url].pop(0)

    def get(self, url, **kwargs):
        return self._responses_by_url[url].pop(0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def _patch_session(responses_by_url: dict):
    return patch("core.video.fal_provider.aiohttp.ClientSession", return_value=FakeSession(responses_by_url))


@pytest.mark.asyncio
async def test_generate_clip_full_flow(monkeypatch):
    monkeypatch.setattr("core.video.fal_provider.asyncio.sleep", AsyncMock())
    submit_url = f"https://queue.fal.run/{DEFAULT_MODEL_ID}"
    status_url = f"https://queue.fal.run/{DEFAULT_MODEL_ID}/requests/abc123/status"
    response_url = f"https://queue.fal.run/{DEFAULT_MODEL_ID}/requests/abc123/response"
    video_url = "https://v3.fal.media/files/rabbit/video123.mp4"

    responses = {
        submit_url: [
            FakeResponse(json_data={"request_id": "abc123", "status_url": status_url, "response_url": response_url})
        ],
        status_url: [
            FakeResponse(json_data={"status": "IN_PROGRESS"}),
            FakeResponse(json_data={"status": "COMPLETED"}),
        ],
        response_url: [FakeResponse(json_data={"video": {"url": video_url}})],
        video_url: [FakeResponse(body=b"FAKEVIDEOBYTES")],
    }

    provider = FalAiVideoProvider(api_key="test-key")
    with _patch_session(responses):
        result = await provider.generate_clip("çoban çay dəmləyir", duration_sec=10, aspect_ratio="9:16")

    assert result == b"FAKEVIDEOBYTES"


@pytest.mark.asyncio
async def test_generate_clip_raises_timeout_when_never_completed(monkeypatch):
    monkeypatch.setattr("core.video.fal_provider.asyncio.sleep", AsyncMock())
    monkeypatch.setattr("core.video.fal_provider.MAX_POLL_ATTEMPTS", 2)
    submit_url = f"https://queue.fal.run/{DEFAULT_MODEL_ID}"
    status_url = f"https://queue.fal.run/{DEFAULT_MODEL_ID}/requests/abc123/status"
    response_url = f"https://queue.fal.run/{DEFAULT_MODEL_ID}/requests/abc123/response"

    responses = {
        submit_url: [
            FakeResponse(json_data={"request_id": "abc123", "status_url": status_url, "response_url": response_url})
        ],
        status_url: [
            FakeResponse(json_data={"status": "IN_PROGRESS"}),
            FakeResponse(json_data={"status": "IN_PROGRESS"}),
        ],
    }

    provider = FalAiVideoProvider(api_key="test-key")
    with _patch_session(responses):
        with pytest.raises(TimeoutError):
            await provider.generate_clip("prompt", duration_sec=5, aspect_ratio="16:9")


@pytest.mark.asyncio
async def test_generate_clip_raises_on_http_error():
    submit_url = f"https://queue.fal.run/{DEFAULT_MODEL_ID}"
    responses = {submit_url: [FakeResponse(status=401, json_data={"error": "unauthorized"})]}

    provider = FalAiVideoProvider(api_key="bad-key")
    with _patch_session(responses):
        with pytest.raises(aiohttp.ClientResponseError):
            await provider.generate_clip("prompt", duration_sec=5, aspect_ratio="16:9")
