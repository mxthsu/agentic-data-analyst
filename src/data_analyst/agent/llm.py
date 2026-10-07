from __future__ import annotations

import httpx
from google.genai.errors import APIError
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from data_analyst.agent.provider_errors import (
    ModelAuthenticationError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUnavailableError,
)


def _translate_provider_error(exc: APIError) -> Exception:
    if exc.code == 429:
        return ModelRateLimitError(
            "Limite temporário da API Gemini atingido."
        )
    if exc.code in {401, 403}:
        return ModelAuthenticationError(
            "A credencial da API Gemini não foi aceita."
        )
    if exc.code in {408, 499}:
        return ModelTimeoutError(
            "A chamada à API Gemini não foi concluída no tempo esperado."
        )
    if exc.code >= 500:
        return ModelUnavailableError(
            "A API Gemini está temporariamente indisponível."
        )
    return ModelUnavailableError(
        "A API Gemini rejeitou a solicitação."
    )


def invoke_structured[StructuredModel: BaseModel](
    model: BaseChatModel,
    schema: type[StructuredModel],
    messages: list[BaseMessage],
) -> StructuredModel:
    try:
        result = model.with_structured_output(
            schema,
            method="json_schema",
        ).invoke(messages)
    except APIError as exc:
        raise _translate_provider_error(exc) from exc
    except (httpx.TimeoutException, TimeoutError) as exc:
        raise ModelTimeoutError(
            "A chamada à API Gemini excedeu o tempo limite."
        ) from exc

    return result if isinstance(result, schema) else schema.model_validate(result)
