"""LLM provider adapters. Both return the same ProviderResult so the agent,
guards, server and sim page do not care which model answered.

Select with NAMI_PROVIDER=openai|anthropic (default: openai when OPENAI_API_KEY
is set and ANTHROPIC_API_KEY is not, otherwise anthropic).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .prompt import RESPONSE_SCHEMA


@dataclass
class ProviderResult:
    text: str  # JSON string following RESPONSE_SCHEMA
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    stop_reason: Optional[str] = None
    fallback_used: bool = False
    refusal: Optional[str] = None
    assistant_message: Any = None  # what to append to history for this provider


class Provider:
    name = "base"
    model: str

    def complete(self, stable_system: str, runtime_system: str, history: list[dict[str, Any]], user_text: str) -> ProviderResult:
        raise NotImplementedError


# --------------------------------------------------------------------- OpenAI
class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, model: str, effort: str = "low", timeout: float = 60.0, client: Any = None) -> None:
        import openai

        self.model = model
        self.effort = effort
        self.client = client or openai.OpenAI(timeout=timeout, max_retries=2)
        self._reasoning_model = bool(re.match(r"^(gpt-5|o\d)", model))

    def complete(self, stable_system, runtime_system, history, user_text) -> ProviderResult:
        messages = [
            {"role": "system", "content": stable_system},
            {"role": "system", "content": runtime_system},
            *history,
            {"role": "user", "content": user_text},
        ]
        kwargs: dict[str, Any] = dict(
            model=self.model,
            messages=messages,
            max_completion_tokens=2048,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "nami_reply", "schema": RESPONSE_SCHEMA, "strict": True},
            },
        )
        if self._reasoning_model:
            # gpt-5 / o-series: reasoning effort instead of temperature; "minimal" keeps chat latency low
            kwargs["reasoning_effort"] = {"low": "minimal", "medium": "low", "high": "medium", "xhigh": "high", "max": "high"}.get(self.effort, "minimal")
        else:
            kwargs["temperature"] = 0.7  # some variety in phrasing on non-reasoning models

        resp = self.client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        refusal = getattr(msg, "refusal", None)
        text = msg.content or ""
        u = resp.usage
        usage = {
            "input_tokens": getattr(u, "prompt_tokens", None),
            "output_tokens": getattr(u, "completion_tokens", None),
            "cache_read_input_tokens": getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", None),
            "cache_creation_input_tokens": None,
        }
        return ProviderResult(
            text=text,
            model=resp.model or self.model,
            usage=usage,
            stop_reason=choice.finish_reason,
            refusal=refusal,
            assistant_message={"role": "assistant", "content": text},
        )


# ------------------------------------------------------------------ Anthropic
class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, model: str, effort: str = "low", timeout: float = 60.0, client: Any = None, use_fallbacks: bool = True) -> None:
        import anthropic

        self.model = model
        self.effort = effort
        self.use_fallbacks = use_fallbacks
        self.client = client or anthropic.Anthropic(timeout=timeout, max_retries=2)

    def complete(self, stable_system, runtime_system, history, user_text) -> ProviderResult:
        system = [
            {"type": "text", "text": stable_system, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": runtime_system},
        ]
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=2048,
            system=system,
            messages=[*history, {"role": "user", "content": user_text}],
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": RESPONSE_SCHEMA}},
        )
        if self.use_fallbacks:
            # Server-side refusal fallback: a declined request is re-run on Anthropic's recommended substitute.
            resp = self.client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
        else:
            resp = self.client.messages.create(**kwargs)

        refusal = None
        if resp.stop_reason == "refusal":
            details = getattr(resp, "stop_details", None)
            refusal = str(getattr(details, "category", None) or "refusal")
        text = next((b.text for b in resp.content if b.type == "text"), "")
        u = getattr(resp, "usage", None)
        usage = {
            "input_tokens": getattr(u, "input_tokens", None),
            "output_tokens": getattr(u, "output_tokens", None),
            "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", None),
            "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", None),
        }
        iterations = getattr(u, "iterations", None) or []
        fallback_used = any(getattr(it, "type", None) == "fallback_message" for it in iterations) or any(
            getattr(b, "type", None) == "fallback" for b in resp.content
        )
        return ProviderResult(
            text=text,
            model=getattr(resp, "model", self.model),
            usage=usage,
            stop_reason=resp.stop_reason,
            fallback_used=fallback_used,
            refusal=refusal,
            assistant_message={"role": "assistant", "content": resp.content},
        )


# ------------------------------------------------------------------- factory
DEFAULT_MODELS = {"openai": "gpt-4.1", "anthropic": "claude-opus-5-5"}


def resolve_provider_name() -> str:
    name = os.environ.get("NAMI_PROVIDER", "").strip().lower()
    if name in ("openai", "anthropic"):
        return name
    if os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        return "openai"
    return "anthropic"


def make_provider(name: Optional[str] = None, model: Optional[str] = None, effort: Optional[str] = None, timeout: float = 60.0) -> Provider:
    name = (name or resolve_provider_name()).lower()
    effort = effort or os.environ.get("NAMI_EFFORT", "low")
    model = model or os.environ.get("NAMI_MODEL") or DEFAULT_MODELS[name]

    if os.environ.get("NAMI_MOCK") == "1":
        from .mock import mock_client  # offline canned replies; Anthropic wire format

        prov = AnthropicProvider(model=model, effort=effort, client=mock_client())
        prov.name = "mock"
        return prov
    if name == "openai":
        return OpenAIProvider(model=model, effort=effort, timeout=timeout)
    return AnthropicProvider(model=model, effort=effort, timeout=timeout)
