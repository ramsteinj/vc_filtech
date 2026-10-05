"""In-memory provider for tests (specs/07 §2). Queue responses on the class, then call."""

import json

from .base import LLMError, LLMProvider, LLMRequest, LLMResponse


class FakeProvider(LLMProvider):
    responses: list = []  # str | dict | Exception, consumed in order
    requests: list[LLMRequest] = []

    @classmethod
    def reset(cls, *responses) -> type["FakeProvider"]:
        cls.responses = list(responses)
        cls.requests = []
        return cls

    def verify(self, model: str) -> None:
        return None

    def generate(self, request: LLMRequest) -> LLMResponse:
        type(self).requests.append(request)
        if not type(self).responses:
            raise LLMError("FakeProvider: 준비된 응답이 없습니다.")
        item = type(self).responses.pop(0)
        if isinstance(item, Exception):
            raise item
        text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
        return LLMResponse(text=text, input_tokens=len(request.user), output_tokens=len(text))
