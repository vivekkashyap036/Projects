"""Provider-agnostic LLM interface.

Any provider only needs `generate(system, user) -> str`. The explanation agent never
depends on a specific vendor SDK, and always has a template fallback.
"""
from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

from vendorscore.config import load_config
from vendorscore.logging_setup import get_logger

log = get_logger(__name__)


class LLMUnavailable(RuntimeError):
    """Raised when no provider is configured or a call fails; the caller falls back to templates."""


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def generate(self, system: str, user: str) -> str: ...


class AnthropicProvider:
    """Claude via the official Anthropic SDK. Needs ANTHROPIC_API_KEY (or an `ant auth login` profile)."""

    name = "anthropic"

    def __init__(self, model: str, max_tokens: int, timeout_s: float) -> None:
        import anthropic  # optional dependency

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(timeout=timeout_s, max_retries=1)
        self.model = model
        self.max_tokens = max_tokens

    def generate(self, system: str, user: str) -> str:
        a = self._anthropic
        try:
            resp = self.client.beta.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"effort": "low"},          # short, simple rewrite task
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",                       # server-side fallback if the model declines
            )
        except (a.APIConnectionError, a.RateLimitError, a.APIStatusError) as exc:  # most specific first
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc
        if resp.stop_reason == "refusal":
            raise LLMUnavailable("model declined the request")
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        if not text.strip():
            raise LLMUnavailable("empty response")
        return text


class NoProvider:
    name = "none"

    def generate(self, system: str, user: str) -> str:
        raise LLMUnavailable("no LLM provider configured")


def get_provider() -> LLMProvider:
    cfg = load_config()["explanation"]
    choice = os.environ.get("LLM_PROVIDER", cfg["provider"]).lower()
    if choice == "none":
        return NoProvider()
    if choice in ("auto", "anthropic"):
        has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
        if choice == "auto" and not has_key:
            log.info("no ANTHROPIC_API_KEY: explanations will use templates")
            return NoProvider()
        try:
            return AnthropicProvider(os.environ.get("LLM_MODEL", cfg["model"]), int(cfg["max_tokens"]),
                                     float(cfg["timeout_s"]))
        except Exception as exc:  # SDK missing or misconfigured
            log.warning("anthropic provider unavailable (%s); using templates", exc)
            return NoProvider()
    log.warning("unknown LLM_PROVIDER %r; using templates", choice)
    return NoProvider()
