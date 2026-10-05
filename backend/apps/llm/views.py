from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminRole

from .models import LLMModelOption, LLMProviderConfig, LLMSettings, Provider
from .serializers import (
    LLMSettingsSerializer,
    ModelOptionSerializer,
    ProviderConfigSerializer,
    ProviderConfigUpdateSerializer,
)
from .services import is_llm_configured, verify_provider


def _settings_payload() -> dict:
    return {
        "llm_configured": is_llm_configured(),
        "settings": LLMSettingsSerializer(LLMSettings.load()).data,
        "providers": ProviderConfigSerializer(LLMProviderConfig.objects.all(), many=True).data,
        "models": ModelOptionSerializer(LLMModelOption.objects.all(), many=True).data,
    }


def _get_config(provider: str) -> LLMProviderConfig:
    if provider not in Provider.values:
        raise ValidationError({"provider": [f"알 수 없는 제공자입니다: {provider}"]})
    config, _ = LLMProviderConfig.objects.get_or_create(provider=provider)
    return config


class LLMSettingsView(APIView):
    """GET/PUT /api/settings/llm"""

    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(_settings_payload())

    def put(self, request):
        serializer = LLMSettingsSerializer(LLMSettings.load(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(_settings_payload())


class ProviderConfigView(APIView):
    """PUT /api/settings/llm/providers/{provider} — saving a new key also runs a connection test.

    The key is stored even if the test fails (specs/04 §4).
    """

    permission_classes = [IsAdminRole]

    def put(self, request, provider):
        config = _get_config(provider)
        serializer = ProviderConfigUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_key = data.get("api_key") or ""
        if new_key:
            config.set_api_key(new_key)
            if "is_enabled" not in data:
                config.is_enabled = True
        if "base_url" in data:
            config.base_url = data["base_url"]
        if "is_enabled" in data:
            config.is_enabled = data["is_enabled"]
        config.save()

        verify = None
        if new_key:
            result = verify_provider(config)
            verify = {"ok": result.ok, "message": result.message, "model_id": result.model_id}
            config.refresh_from_db()

        return Response(
            {
                "provider": ProviderConfigSerializer(config).data,
                "verify": verify,
                "llm_configured": is_llm_configured(),
            }
        )


class ProviderVerifyView(APIView):
    """POST /api/settings/llm/providers/{provider}/verify {model_id?}"""

    permission_classes = [IsAdminRole]

    def post(self, request, provider):
        config = _get_config(provider)
        result = verify_provider(config, request.data.get("model_id") or None)
        config.refresh_from_db()
        return Response(
            {
                "ok": result.ok,
                "message": result.message,
                "model_id": result.model_id,
                "provider": ProviderConfigSerializer(config).data,
            }
        )


class ModelOptionViewSet(viewsets.ModelViewSet):
    """CRUD /api/settings/llm/models"""

    permission_classes = [IsAdminRole]
    serializer_class = ModelOptionSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        qs = LLMModelOption.objects.all()
        provider = self.request.query_params.get("provider")
        return qs.filter(provider=provider) if provider else qs

    def perform_update(self, serializer):
        model = serializer.instance
        if serializer.validated_data.get("is_active") is False and self._is_active_model(model):
            raise ValidationError({"is_active": ["현재 사용 중인 모델은 비활성화할 수 없습니다."]})
        serializer.save()

    def perform_destroy(self, instance):
        if self._is_active_model(instance):
            raise ValidationError({"detail": ["현재 사용 중인 모델은 삭제할 수 없습니다."]})
        instance.delete()

    @staticmethod
    def _is_active_model(model: LLMModelOption) -> bool:
        return LLMSettings.load().active_model_id == model.pk
