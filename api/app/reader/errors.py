"""Provider result and error types (§2.7), shared by the question guard and the reader."""
from dataclasses import dataclass


@dataclass(frozen=True)
class StreamResult:
    tokens_in: int | None
    tokens_out: int | None
    stop_reason: str | None
    model: str
    refusal_category: str | None = None  # stop_details.category of a refusal ("bio", "general_harms", ...)


class ProviderError(Exception):
    """The call failed: network, API status, truncated or invalid JSON."""


class ProviderTimeout(ProviderError):
    """The SDK gave up waiting (anthropic.APITimeoutError)."""


class ProviderRefusal(ProviderError):
    """stop_reason == "refusal": an error for the reader (§5.1), a crisis for the question guard (§8.6)."""

    def __init__(self, result: StreamResult | None = None):
        super().__init__("refusal")
        self.result = result
