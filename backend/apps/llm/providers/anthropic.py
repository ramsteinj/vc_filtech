import anthropic

from .base import VERIFY_MAX_TOKENS, VERIFY_PROMPT, LLMError, LLMProvider, status_error


class AnthropicProvider(LLMProvider):
    def _client(self) -> anthropic.Anthropic:
        return anthropic.Anthropic(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout, max_retries=0
        )

    def verify(self, model: str) -> None:
        try:
            self._client().messages.create(
                model=model,
                max_tokens=VERIFY_MAX_TOKENS,
                messages=[{"role": "user", "content": VERIFY_PROMPT}],
            )
        except anthropic.APIStatusError as exc:
            raise status_error(exc.status_code, model, str(exc.message)) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("Anthropic 서버에 연결할 수 없습니다.") from exc
