import httpx
import pytest
from google.genai.errors import ClientError, ServerError

from data_analyst.agent.llm import invoke_structured
from data_analyst.agent.models import QuestionIntent
from data_analyst.agent.provider_errors import (
    ModelAuthenticationError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUnavailableError,
)


class RaisingRunnable:
    def __init__(self, error: Exception):
        self.error = error

    def invoke(self, _messages):
        raise self.error


class RaisingModel:
    def __init__(self, error: Exception):
        self.error = error

    def with_structured_output(self, _schema, **_kwargs):
        return RaisingRunnable(self.error)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            ClientError(429, {"error": {"message": "quota"}}),
            ModelRateLimitError,
        ),
        (
            ClientError(403, {"error": {"message": "forbidden"}}),
            ModelAuthenticationError,
        ),
        (
            ServerError(503, {"error": {"message": "unavailable"}}),
            ModelUnavailableError,
        ),
        (
            httpx.ReadTimeout("timeout"),
            ModelTimeoutError,
        ),
    ],
)
def test_traduz_erros_do_provider(error: Exception, expected: type[Exception]) -> None:
    with pytest.raises(expected):
        invoke_structured(
            RaisingModel(error),
            QuestionIntent,
            [],
        )
