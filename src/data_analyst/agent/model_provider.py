from langchain_core.language_models import BaseChatModel
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI

from data_analyst.config import Settings


def create_chat_model(settings: Settings) -> BaseChatModel:
    requests_per_second = settings.gemini_requests_per_minute / 60

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=settings.google_api_key,
        temperature=0,
        max_tokens=settings.gemini_max_output_tokens,
        request_timeout=settings.gemini_request_timeout_seconds,
        retries=1,
        rate_limiter=InMemoryRateLimiter(
            requests_per_second=requests_per_second,
            check_every_n_seconds=0.1,
            max_bucket_size=1,
        ),
    )
