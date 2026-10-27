from unittest.mock import AsyncMock, patch

import pytest

from core.tts import DEFAULT_VOICE, generate_narration


@pytest.mark.asyncio
async def test_generate_narration_calls_edge_tts_with_correct_args(tmp_path):
    output_path = str(tmp_path / "narration.mp3")

    with patch("core.tts.edge_tts.Communicate") as mock_communicate_cls:
        mock_instance = mock_communicate_cls.return_value
        mock_instance.save = AsyncMock()

        await generate_narration("Salam dünya", output_path, voice="az-AZ-BanuNeural")

        mock_communicate_cls.assert_called_once_with("Salam dünya", "az-AZ-BanuNeural")
        mock_instance.save.assert_awaited_once_with(output_path)


@pytest.mark.asyncio
async def test_generate_narration_uses_default_voice_when_not_specified(tmp_path):
    output_path = str(tmp_path / "narration.mp3")

    with patch("core.tts.edge_tts.Communicate") as mock_communicate_cls:
        mock_instance = mock_communicate_cls.return_value
        mock_instance.save = AsyncMock()

        await generate_narration("Salam", output_path)

        mock_communicate_cls.assert_called_once_with("Salam", DEFAULT_VOICE)
