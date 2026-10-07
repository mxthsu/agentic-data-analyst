from langchain_core.language_models import BaseChatModel
from langchain_openrouter import ChatOpenRouter

from data_analyst.config import Settings


def create_chat_model(settings: Settings) -> BaseChatModel:
    return ChatOpenRouter(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        temperature=0,
        max_retries=2,
    )
