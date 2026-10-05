import openai

from .base import VERIFY_MAX_TOKENS, VERIFY_PROMPT, LLMError, LLMProvider, status_error


class OpenAIProvider(LLMProvider):
    def _client(self) -> openai.OpenAI:
        return openai.OpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout, max_retries=0
        )

    def verify(self, model: str) -> None:
        try:
            self._client().responses.create(
                model=model, input=VERIFY_PROMPT, max_output_tokens=VERIFY_MAX_TOKENS
            )
        except openai.APIStatusError as exc:
            raise status_error(exc.status_code, model, str(exc.message)) from exc
        except openai.APIConnectionError as exc:
            raise LLMError("OpenAI 서버에 연결할 수 없습니다.") from exc
