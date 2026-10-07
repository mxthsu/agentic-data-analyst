import time

from langchain_core.language_models import BaseChatModel
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI

from data_analyst.config import Settings


def _create_rate_limiter(settings: Settings) -> InMemoryRateLimiter:
    requests_per_second = settings.gemini_requests_per_minute / 60
    limiter = InMemoryRateLimiter(
        requests_per_second=requests_per_second,
        check_every_n_seconds=0.1,
        max_bucket_size=settings.gemini_max_burst_requests,
    )

    # Uma pergunta pode exigir várias etapas LLM sequenciais. O pequeno burst
    # representa crédito acumulado para uma única investigação, enquanto a taxa
    # sustentada continua limitada por GEMINI_REQUESTS_PER_MINUTE.
    limiter.available_tokens = float(settings.gemini_max_burst_requests)
    limiter.last = time.monotonic()
    return limiter


def create_chat_model(settings: Settings) -> BaseChatModel:
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=settings.google_api_key,
        max_tokens=settings.gemini_max_output_tokens,
        request_timeout=settings.gemini_request_timeout_seconds,
        retries=1,
        rate_limiter=_create_rate_limiter(settings),
    )
