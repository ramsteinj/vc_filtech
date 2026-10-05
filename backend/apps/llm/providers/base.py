"""Provider abstraction (specs/07 §2). Phase 2 implements connection verification only;
structured generation (`generate`) is added in Phase 4."""

from abc import ABC, abstractmethod

from apps.core.logging import mask_secrets

VERIFY_PROMPT = "Reply with exactly: OK"
VERIFY_MAX_TOKENS = 64


class LLMError(Exception):
    """Error with a user-facing Korean message (secrets masked)."""

    def __init__(self, message: str):
        super().__init__(mask_secrets(message))
        self.user_message = mask_secrets(message)


class LLMProvider(ABC):
    def __init__(self, api_key: str, base_url: str | None = None, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url or None
        self.timeout = timeout

    @abstractmethod
    def verify(self, model: str) -> None:
        """Send a minimal request. Raise LLMError on failure."""


def status_error(status_code: int | None, model: str, detail: str = "") -> LLMError:
    if status_code in (401, 403):
        return LLMError("API Key가 올바르지 않거나 권한이 없습니다.")
    if status_code == 404:
        return LLMError(f"모델을 찾을 수 없습니다: {model}")
    if status_code == 429:
        return LLMError("요청 한도를 초과했습니다. 잠시 후 다시 시도하세요.")
    suffix = f" — {detail[:200]}" if detail else ""
    return LLMError(f"LLM 호출 오류 (HTTP {status_code}){suffix}")
