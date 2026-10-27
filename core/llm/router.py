import logging
from typing import List

from core.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class AllProvidersFailedError(Exception):
    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(f"All LLM providers failed: {errors}")


class LLMRouter:
    def __init__(self, providers: List[LLMProvider]):
        if not providers:
            raise ValueError("At least one provider is required")
        self._providers = providers

    def generate(self, prompt: str) -> str:
        errors = {}
        for provider in self._providers:
            try:
                return provider.generate(prompt)
            except Exception as exc:
                logger.warning("LLM provider '%s' failed: %s", provider.name, exc)
                errors[provider.name] = str(exc)
        raise AllProvidersFailedError(errors)


def build_default_router(settings) -> LLMRouter:
    """Builds the Gemini -> Groq -> Ollama fallback chain, skipping providers
    whose credentials are not configured."""
    from core.llm.gemini_provider import GeminiProvider
    from core.llm.groq_provider import GroqProvider
    from core.llm.ollama_provider import OllamaProvider

    providers: List[LLMProvider] = []
    if settings.gemini_api_key:
        providers.append(GeminiProvider(settings.gemini_api_key))
    if settings.groq_api_key:
        providers.append(GroqProvider(settings.groq_api_key))
    if settings.ollama_host:
        providers.append(OllamaProvider(settings.ollama_host))
    return LLMRouter(providers)
