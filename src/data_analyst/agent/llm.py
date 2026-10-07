from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import BaseModel


def invoke_structured[StructuredModel: BaseModel](
    model: BaseChatModel,
    schema: type[StructuredModel],
    messages: list[BaseMessage],
) -> StructuredModel:
    result = model.with_structured_output(schema).invoke(messages)
    return result if isinstance(result, schema) else schema.model_validate(result)
