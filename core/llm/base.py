from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return the raw text completion for the given prompt. Raise on failure."""
