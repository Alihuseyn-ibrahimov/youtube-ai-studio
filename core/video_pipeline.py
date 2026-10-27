import os
import subprocess
import tempfile

from core import tts
from core.db import ContentIdea
from core.video.base import VideoProvider

ASPECT_RATIO_BY_FORMAT = {
    "shorts": "9:16",
    "long": "16:9",
}
DEFAULT_ASPECT_RATIO = "16:9"


class VideoPipelineError(Exception):
    pass


async def build_video(
    idea: ContentIdea, video_provider: VideoProvider, output_path: str, tts_voice: str
) -> str:
    """Builds a narrated video for an approved content idea. Returns output_path on success."""
    aspect_ratio = ASPECT_RATIO_BY_FORMAT.get(idea.format, DEFAULT_ASPECT_RATIO)

    with tempfile.TemporaryDirectory() as tmp_dir:
        narration_path = await _generate_narration_audio(idea, tmp_dir, tts_voice)
        clip_paths = await _generate_scene_clips(idea, video_provider, aspect_ratio, tmp_dir)
        concat_path = _concat_clips(clip_paths, tmp_dir)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        _mux_audio(concat_path, narration_path, output_path)

    return output_path


async def _generate_narration_audio(idea: ContentIdea, tmp_dir: str, tts_voice: str) -> str:
    narration_path = os.path.join(tmp_dir, "narration.mp3")
    await tts.generate_narration(idea.script_text, narration_path, voice=tts_voice)
    return narration_path


async def _generate_scene_clips(
    idea: ContentIdea, video_provider: VideoProvider, aspect_ratio: str, tmp_dir: str
) -> list:
    if not idea.scenes:
        raise VideoPipelineError("Content idea has no scenes to generate clips for")

    clip_paths = []
    for i, scene in enumerate(idea.scenes):
        clip_bytes = await video_provider.generate_clip(
            scene["description"], scene.get("duration_sec", 8), aspect_ratio
        )
        clip_path = os.path.join(tmp_dir, f"clip_{i:03d}.mp4")
        with open(clip_path, "wb") as f:
            f.write(clip_bytes)
        clip_paths.append(clip_path)
    return clip_paths


def _concat_clips(clip_paths: list, tmp_dir: str) -> str:
    output_path = os.path.join(tmp_dir, "concat.mp4")
    if len(clip_paths) == 1:
        _run_ffmpeg(["-y", "-i", clip_paths[0], "-c", "copy", output_path])
        return output_path

    list_file = os.path.join(tmp_dir, "concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for path in clip_paths:
            escaped = path.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
    _run_ffmpeg(["-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path])
    return output_path


def _mux_audio(video_path: str, audio_path: str, output_path: str) -> None:
    video_duration = _probe_duration(video_path)
    audio_duration = _probe_duration(audio_path)

    if audio_duration > video_duration:
        pad_sec = audio_duration - video_duration
        _run_ffmpeg(
            [
                "-y", "-i", video_path, "-i", audio_path,
                "-filter_complex", f"[0:v]tpad=stop_mode=clone:stop_duration={pad_sec}[v]",
                "-map", "[v]", "-map", "1:a",
                "-c:v", "libx264", "-c:a", "aac", "-shortest", output_path,
            ]
        )
    else:
        _run_ffmpeg(
            [
                "-y", "-i", video_path, "-i", audio_path,
                "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-shortest", output_path,
            ]
        )


def _probe_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise VideoPipelineError(f"ffprobe failed for {path}: {result.stderr[-2000:]}")
    return float(result.stdout.strip())


def _run_ffmpeg(args: list) -> None:
    result = subprocess.run(["ffmpeg", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise VideoPipelineError(f"ffmpeg failed: {result.stderr[-2000:]}")
