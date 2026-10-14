"""LLM provider wrapper. Swap providers via LLM_PROVIDER in .env."""

import logging
import time
from functools import lru_cache

from app.core.config import settings

log = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class LLMError(Exception):
    """Raised when an LLM provider request fails.

    retryable=True marks transient failures (rate limits, timeouts, server errors,
    empty replies) that are worth one more attempt."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


def _is_retryable(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return status is None or status in RETRYABLE_STATUS


def model_name() -> str:
    if settings.llm_provider == "gemini":
        return settings.gemini_llm_model
    if settings.llm_provider == "anthropic":
        return settings.anthropic_llm_model
    return settings.openrouter_llm_model


@lru_cache
def _gemini():
    from google import genai

    return genai.Client(api_key=settings.gemini_api_key)


@lru_cache
def _anthropic():
    import anthropic

    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


@lru_cache
def _openrouter():
    from openai import OpenAI

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
        max_retries=0,
        timeout=20.0,
    )


def _normalize(messages: list[dict]) -> list[dict]:
    """Ensure messages alternate roles and start with a user message."""
    out: list[dict] = []

    for message in messages:
        role = "assistant" if message["role"] == "assistant" else "user"
        content = message["content"]

        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n\n" + content
        else:
            out.append({"role": role, "content": content})

    while out and out[0]["role"] != "user":
        out.pop(0)

    return out


def _call_gemini(
    system: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> str:
    from google.genai import types

    contents = [
        types.Content(
            role="user" if message["role"] == "user" else "model",
            parts=[types.Part(text=message["content"])],
        )
        for message in messages
    ]

    try:
        response = _gemini().models.generate_content(
            model=settings.gemini_llm_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                temperature=temperature,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
    except Exception as exc:
        raise LLMError(
            f"Gemini request failed: {str(exc)[:200]}",
            retryable=_is_retryable(exc),
        ) from exc

    return (response.text or "").strip()


def _call_anthropic(
    system: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> str:
    try:
        response = _anthropic().messages.create(
            model=settings.anthropic_llm_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
    except Exception as exc:
        raise LLMError(
            f"Anthropic request failed: {str(exc)[:200]}",
            retryable=_is_retryable(exc),
        ) from exc

    return "".join(
        block.text
        for block in response.content
        if getattr(block, "type", "") == "text"
    ).strip()


def _call_openrouter(
    system: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> str:
    """Call OpenRouter without automatic retries."""

    try:
        response = _openrouter().chat.completions.create(
            model=settings.openrouter_llm_model,
            messages=[
                {"role": "system", "content": system},
                *messages,
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

    except Exception as exc:
        # OpenAI SDK HTTP errors expose status_code and response details.
        status_code = getattr(exc, "status_code", None)

        if status_code == 429:
            raise LLMError(
                "OpenRouter rate limit reached (HTTP 429). "
                "Please wait before retrying, or check your model and "
                "account usage limits.",
                retryable=True,
            ) from exc

        if status_code in (401, 403):
            raise LLMError(
                "OpenRouter authentication or access failed. "
                "Check the API key and model access."
            ) from exc

        if status_code == 402:
            raise LLMError(
                "OpenRouter reports insufficient credits or account limits. "
                "Check your account usage and limits."
            ) from exc

        raise LLMError(
            f"OpenRouter request failed"
            + (f" (HTTP {status_code})" if status_code else "")
            + f": {str(exc)[:200]}",
            retryable=(status_code is None or status_code in RETRYABLE_STATUS),
        ) from exc

    if not response.choices:
        raise LLMError("OpenRouter returned no response choices.", retryable=True)

    content = response.choices[0].message.content

    if not content or not content.strip():
        raise LLMError("OpenRouter returned an empty response.", retryable=True)

    return content.strip()


def generate(
    system: str,
    messages: list[dict],
    max_tokens: int | None = None,
    temperature: float = 0.2,
) -> str:
    """Generate text using the configured LLM provider."""

    max_tokens = max_tokens or settings.llm_max_output_tokens
    messages = _normalize(messages)

    if not messages:
        raise LLMError("No user message to send.")

    providers = {
        "gemini": _call_gemini,
        "anthropic": _call_anthropic,
        "openrouter": _call_openrouter,
    }

    call = providers.get(settings.llm_provider)

    if call is None:
        raise LLMError(
            f"Unsupported LLM provider: {settings.llm_provider}"
        )

    last_error: LLMError | None = None

    for attempt in range(1, 3):  # one retry, only for transient failures
        try:
            return call(system, messages, max_tokens, temperature)
        except LLMError as exc:
            last_error = exc
            log.warning("LLM attempt %d/2 failed: %s", attempt, exc)
            if not exc.retryable or attempt == 2:
                break
            time.sleep(2)

    raise last_error