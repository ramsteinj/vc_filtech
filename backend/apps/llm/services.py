"""Single entry point for LLM operations (CLAUDE.md: views must not import SDKs).

Phase 2: configuration state and connection verification. `run_task` is added in Phase 4.
"""

from dataclasses import dataclass

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from .crypto import DecryptionError
from .models import LLMModelOption, LLMProviderConfig, LLMSettings
from .providers import LLMError, get_provider_class

VERIFY_TIMEOUT_SEC = 30


class LLMNotConfigured(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "LLM API Key가 설정되지 않았습니다. 관리자에게 문의하세요."
    default_code = "llm_not_configured"


@dataclass
class VerifyResult:
    ok: bool
    message: str
    model_id: str


def is_llm_configured() -> bool:
    """Active provider exists, is enabled and has an API key (specs/03 §4)."""
    active_provider = LLMSettings.load().active_provider
    config = LLMProviderConfig.objects.filter(provider=active_provider).first()
    return bool(config and config.is_enabled and config.has_api_key)


def ensure_llm_configured() -> None:
    """Call at the start of any endpoint that needs the LLM; raises 409 llm_not_configured."""
    if not is_llm_configured():
        raise LLMNotConfigured()


def resolve_model(provider: str) -> LLMModelOption | None:
    """Model used for `provider`: the active model if it belongs to it, else its default."""
    settings_row = LLMSettings.load()
    model = settings_row.active_model
    if model and model.provider == provider and model.is_active:
        return model
    options = LLMModelOption.objects.filter(provider=provider, is_active=True)
    return options.filter(is_default=True).first() or options.first()


def verify_provider(config: LLMProviderConfig, model_id: str | None = None) -> VerifyResult:
    """Send a minimal request with the stored key and record the outcome on `config`."""
    if not model_id:
        model = resolve_model(config.provider)
        model_id = model.model_id if model else ""
    if not config.has_api_key:
        result = VerifyResult(False, "API Key가 저장되어 있지 않습니다.", model_id)
    elif not model_id:
        result = VerifyResult(False, "사용 가능한 모델이 없습니다. 모델을 먼저 등록하세요.", "")
    else:
        try:
            provider = get_provider_class(config.provider)(
                api_key=config.get_api_key(),
                base_url=config.base_url,
                timeout=VERIFY_TIMEOUT_SEC,
            )
            provider.verify(model_id)
            result = VerifyResult(True, f"연결 성공 ({model_id})", model_id)
        except (LLMError, DecryptionError) as exc:
            result = VerifyResult(False, str(exc), model_id)

    config.last_verified_at = timezone.now()
    config.last_verify_ok = result.ok
    config.last_verify_error = "" if result.ok else result.message
    config.save(update_fields=["last_verified_at", "last_verify_ok", "last_verify_error"])
    return result
