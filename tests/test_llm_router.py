import pytest

from core.llm.base import LLMProvider
from core.llm.router import AllProvidersFailedError, LLMRouter


class FakeProvider(LLMProvider):
    def __init__(self, name: str, result: str = None, error: Exception = None):
        self.name = name
        self._result = result
        self._error = error
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._result


def test_router_returns_first_successful_provider():
    failing = FakeProvider("gemini", error=RuntimeError("rate limited"))
    working = FakeProvider("groq", result="salam dunya")
    router = LLMRouter([failing, working])

    result = router.generate("prompt")

    assert result == "salam dunya"
    assert failing.calls == 1
    assert working.calls == 1


def test_router_stops_at_first_success_without_calling_later_providers():
    working = FakeProvider("gemini", result="ilk cavab")
    unused = FakeProvider("groq", result="ikinci cavab")
    router = LLMRouter([working, unused])

    result = router.generate("prompt")

    assert result == "ilk cavab"
    assert unused.calls == 0


def test_router_raises_when_all_providers_fail():
    a = FakeProvider("gemini", error=RuntimeError("a failed"))
    b = FakeProvider("groq", error=RuntimeError("b failed"))
    router = LLMRouter([a, b])

    with pytest.raises(AllProvidersFailedError) as exc_info:
        router.generate("prompt")

    assert exc_info.value.errors == {"gemini": "a failed", "groq": "b failed"}


def test_router_requires_at_least_one_provider():
    with pytest.raises(ValueError):
        LLMRouter([])
