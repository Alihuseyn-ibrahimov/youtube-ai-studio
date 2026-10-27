import os
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import core.video_pipeline as video_pipeline
from core.db import ContentIdea
from core.video_pipeline import (
    VideoPipelineError,
    _concat_clips,
    _mux_audio,
    _probe_duration,
    _run_ffmpeg,
    build_video,
)


def _make_idea(format_="shorts", scenes=None):
    return ContentIdea(
        id=1,
        created_at="2026-01-01",
        format=format_,
        title="Test başlıq",
        script_text="Salam dünya",
        scenes=scenes if scenes is not None else [{"description": "səhnə 1", "duration_sec": 5}],
        status="approved",
        telegram_message_id=None,
        video_status=None,
        video_path=None,
        video_telegram_message_id=None,
        video_error=None,
    )


def _fake_completed_process(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_run_ffmpeg_raises_on_nonzero_exit():
    with patch("core.video_pipeline.subprocess.run", return_value=_fake_completed_process(1, stderr="bad input")):
        with pytest.raises(VideoPipelineError):
            _run_ffmpeg(["-y", "-i", "in.mp4", "out.mp4"])


def test_probe_duration_parses_ffprobe_output():
    with patch("core.video_pipeline.subprocess.run", return_value=_fake_completed_process(0, stdout="12.5\n")):
        assert _probe_duration("some.mp4") == 12.5


def test_probe_duration_raises_on_ffprobe_failure():
    with patch("core.video_pipeline.subprocess.run", return_value=_fake_completed_process(1, stderr="no such file")):
        with pytest.raises(VideoPipelineError):
            _probe_duration("missing.mp4")


def test_mux_audio_freezes_last_frame_when_audio_longer(tmp_path):
    with patch("core.video_pipeline._probe_duration", side_effect=[5.0, 8.0]), \
         patch("core.video_pipeline._run_ffmpeg") as mock_run:
        _mux_audio("video.mp4", "audio.mp3", str(tmp_path / "out.mp4"))

    args = mock_run.call_args[0][0]
    assert any("tpad" in arg for arg in args)


def test_mux_audio_simple_copy_when_video_longer_or_equal(tmp_path):
    with patch("core.video_pipeline._probe_duration", side_effect=[10.0, 8.0]), \
         patch("core.video_pipeline._run_ffmpeg") as mock_run:
        _mux_audio("video.mp4", "audio.mp3", str(tmp_path / "out.mp4"))

    args = mock_run.call_args[0][0]
    assert not any("tpad" in arg for arg in args)
    assert "copy" in args


def test_concat_clips_single_clip_copies_directly(tmp_path):
    with patch("core.video_pipeline._run_ffmpeg") as mock_run:
        result = _concat_clips(["clip0.mp4"], str(tmp_path))

    args = mock_run.call_args[0][0]
    assert "-f" not in args
    assert result == os.path.join(str(tmp_path), "concat.mp4")


def test_concat_clips_multiple_uses_concat_demuxer(tmp_path):
    with patch("core.video_pipeline._run_ffmpeg") as mock_run:
        _concat_clips(["clip0.mp4", "clip1.mp4"], str(tmp_path))

    args = mock_run.call_args[0][0]
    assert "-f" in args and "concat" in args
    list_file = tmp_path / "concat_list.txt"
    assert list_file.exists()
    content = list_file.read_text(encoding="utf-8")
    assert "clip0.mp4" in content and "clip1.mp4" in content


@pytest.mark.asyncio
async def test_build_video_orchestrates_narration_clips_concat_mux(tmp_path):
    idea = _make_idea(scenes=[{"description": "s1", "duration_sec": 5}, {"description": "s2", "duration_sec": 10}])
    video_provider = MagicMock()
    video_provider.generate_clip = AsyncMock(return_value=b"FAKECLIP")
    output_path = str(tmp_path / "final.mp4")

    with patch.object(video_pipeline.tts, "generate_narration", new=AsyncMock()) as mock_tts, \
         patch("core.video_pipeline._concat_clips", return_value="concat.mp4") as mock_concat, \
         patch("core.video_pipeline._mux_audio") as mock_mux:
        result = await build_video(idea, video_provider, output_path, tts_voice="az-AZ-BabekNeural")

    assert result == output_path
    mock_tts.assert_awaited_once()
    assert video_provider.generate_clip.await_count == 2
    mock_concat.assert_called_once()
    mock_mux.assert_called_once()
    mux_args = mock_mux.call_args[0]
    assert mux_args[0] == "concat.mp4"
    assert mux_args[1].endswith("narration.mp3")
    assert mux_args[2] == output_path


@pytest.mark.asyncio
async def test_build_video_raises_when_no_scenes(tmp_path):
    idea = _make_idea(scenes=[])
    video_provider = MagicMock()
    video_provider.generate_clip = AsyncMock(return_value=b"FAKECLIP")

    with patch.object(video_pipeline.tts, "generate_narration", new=AsyncMock()):
        with pytest.raises(VideoPipelineError):
            await build_video(idea, video_provider, str(tmp_path / "out.mp4"), tts_voice="az-AZ-BabekNeural")


@pytest.mark.asyncio
async def test_build_video_propagates_video_provider_failure(tmp_path):
    idea = _make_idea()
    video_provider = MagicMock()
    video_provider.generate_clip = AsyncMock(side_effect=RuntimeError("fal.ai quota exceeded"))

    with patch.object(video_pipeline.tts, "generate_narration", new=AsyncMock()):
        with pytest.raises(RuntimeError):
            await build_video(idea, video_provider, str(tmp_path / "out.mp4"), tts_voice="az-AZ-BabekNeural")
