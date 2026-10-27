import edge_tts

DEFAULT_VOICE = "az-AZ-BanuNeural"


async def generate_narration(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
