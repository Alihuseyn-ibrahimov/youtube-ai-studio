import ollama

from core.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, host: str, model: str = "llama3.1"):
        self._client = ollama.Client(host=host)
        self._model = model

    def generate(self, prompt: str) -> str:
        response = self._client.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"]
