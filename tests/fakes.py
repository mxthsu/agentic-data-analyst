from __future__ import annotations

from collections import defaultdict, deque

from pydantic import BaseModel


class _ScriptedRunnable:
    def __init__(self, owner: ScriptedModel, schema: type[BaseModel]):
        self.owner = owner
        self.schema = schema

    def invoke(self, _messages):
        queue = self.owner.responses[self.schema]
        if not queue:
            raise AssertionError(f"Sem resposta simulada para {self.schema.__name__}")
        value = queue.popleft()
        self.owner.calls.append(self.schema)
        return value


class ScriptedModel:
    def __init__(self, *responses: BaseModel):
        self.responses = defaultdict(deque)
        self.calls: list[type[BaseModel]] = []
        for response in responses:
            self.responses[type(response)].append(response)

    def with_structured_output(self, schema: type[BaseModel], **_kwargs):
        return _ScriptedRunnable(self, schema)
