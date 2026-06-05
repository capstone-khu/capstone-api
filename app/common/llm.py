import asyncio

from pydantic import BaseModel

from app.common.config import settings

MAX_CONCURRENCY = 4
TIMEOUT_S = 12.0
DEFAULT_MAX_TOKENS = 120

_client = None
_semaphore = asyncio.Semaphore(MAX_CONCURRENCY)


def _get_client():
    global _client
    if _client is None:
        from openai import AsyncOpenAI

        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def structured[T: BaseModel](
    messages: list[dict],
    schema: type[T],
    model: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> T | None:

    if not settings.OPENAI_API_KEY:
        return None
    try:
        async with _semaphore:
            completion = await asyncio.wait_for(
                _get_client().chat.completions.parse(
                    model=model or settings.OPENAI_MODEL,
                    messages=messages,
                    response_format=schema,
                    max_completion_tokens=max_tokens,
                ),
                timeout=TIMEOUT_S,
            )
        return completion.choices[0].message.parsed
    except Exception:
        return None
