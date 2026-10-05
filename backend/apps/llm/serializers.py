from rest_framework import serializers

from .models import LLMModelOption, LLMProviderConfig, LLMSettings, Provider


class ProviderConfigSerializer(serializers.ModelSerializer):
    """Never exposes the API key — only whether one is stored and its masked tail."""

    label = serializers.CharField(source="get_provider_display", read_only=True)
    has_api_key = serializers.BooleanField(read_only=True)
    api_key_masked = serializers.CharField(read_only=True)

    class Meta:
        model = LLMProviderConfig
        fields = [
            "provider",
            "label",
            "has_api_key",
            "api_key_masked",
            "base_url",
            "is_enabled",
            "last_verified_at",
            "last_verify_ok",
            "last_verify_error",
        ]
        read_only_fields = fields


class ProviderConfigUpdateSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    base_url = serializers.CharField(required=False, allow_blank=True, max_length=255)
    is_enabled = serializers.BooleanField(required=False)

    def validate_base_url(self, value):
        if value and not value.startswith(("http://", "https://")):
            raise serializers.ValidationError("http:// 또는 https:// 로 시작해야 합니다.")
        return value


class ModelOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMModelOption
        fields = [
            "id",
            "provider",
            "model_id",
            "display_name",
            "supports_pdf_input",
            "max_output_tokens",
            "is_default",
            "is_active",
            "order",
        ]


class LLMSettingsSerializer(serializers.ModelSerializer):
    active_model_id = serializers.PrimaryKeyRelatedField(
        source="active_model",
        queryset=LLMModelOption.objects.all(),
        allow_null=True,
        required=False,
    )
    active_provider = serializers.ChoiceField(choices=Provider.choices, required=False)
    temperature = serializers.FloatField(min_value=0, max_value=2, required=False)
    max_output_tokens = serializers.IntegerField(min_value=1, required=False)
    timeout_sec = serializers.IntegerField(min_value=5, max_value=3600, required=False)
    max_retries = serializers.IntegerField(min_value=0, max_value=10, required=False)

    class Meta:
        model = LLMSettings
        fields = [
            "active_provider",
            "active_model_id",
            "temperature",
            "max_output_tokens",
            "timeout_sec",
            "max_retries",
            "json_mode",
            "per_task_overrides",
        ]

    def validate_per_task_overrides(self, value):
        if not isinstance(value, dict) or not all(isinstance(v, dict) for v in value.values()):
            raise serializers.ValidationError(
                '{"작업키": {"temperature": 0.0, ...}} 형식의 JSON 객체여야 합니다.'
            )
        return value

    def validate(self, attrs):
        instance = self.instance
        provider = attrs.get("active_provider", instance.active_provider if instance else None)
        model = attrs.get("active_model", instance.active_model if instance else None)
        provider_changed = instance is not None and provider != instance.active_provider
        if provider_changed and "active_model" not in attrs:
            model = (
                LLMModelOption.objects.filter(provider=provider, is_active=True)
                .order_by("-is_default", "order")
                .first()
            )
            attrs["active_model"] = model
        if model is not None:
            if model.provider != provider:
                raise serializers.ValidationError(
                    {"active_model_id": ["선택한 모델이 활성 제공자의 모델이 아닙니다."]}
                )
            if not model.is_active:
                raise serializers.ValidationError(
                    {"active_model_id": ["비활성화된 모델은 선택할 수 없습니다."]}
                )
        return attrs
