import httpx
from google import genai
from google.genai import errors, types

from .base import VERIFY_MAX_TOKENS, VERIFY_PROMPT, LLMError, LLMProvider, status_error


class GeminiProvider(LLMProvider):
    def _client(self) -> genai.Client:
        options = {"timeout": self.timeout * 1000}
        if self.base_url:
            options["base_url"] = self.base_url
        return genai.Client(api_key=self.api_key, http_options=types.HttpOptions(**options))

    def verify(self, model: str) -> None:
        try:
            self._client().models.generate_content(
                model=model,
                contents=VERIFY_PROMPT,
                config=types.GenerateContentConfig(max_output_tokens=VERIFY_MAX_TOKENS),
            )
        except errors.APIError as exc:
            # Gemini reports an invalid key as HTTP 400 API_KEY_INVALID.
            if "API_KEY_INVALID" in str(exc) or "API key not valid" in str(exc):
                raise LLMError("API Key가 올바르지 않거나 권한이 없습니다.") from exc
            raise status_error(exc.code, model, str(exc.message or "")) from exc
        except httpx.TransportError as exc:
            raise LLMError("Gemini 서버에 연결할 수 없습니다.") from exc
