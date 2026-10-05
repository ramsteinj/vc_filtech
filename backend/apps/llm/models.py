from django.db import models, transaction

from apps.core.models import TimeStampedModel

from . import crypto


class Provider(models.TextChoices):
    OPENAI = "OPENAI", "ChatGPT (OpenAI)"
    ANTHROPIC = "ANTHROPIC", "Claude (Anthropic)"
    GEMINI = "GEMINI", "Gemini (Google)"


class LLMProviderConfig(TimeStampedModel):
    """Per-provider API key (Fernet-encrypted) and connection status (specs/02 §8)."""

    provider = models.CharField(max_length=20, choices=Provider.choices, unique=True)
    api_key_encrypted = models.TextField(blank=True)
    api_key_last4 = models.CharField(max_length=4, blank=True)
    base_url = models.CharField(max_length=255, blank=True)
    is_enabled = models.BooleanField(default=False)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    last_verify_ok = models.BooleanField(null=True)
    last_verify_error = models.TextField(blank=True)

    class Meta:
        ordering = ["provider"]

    def __str__(self):
        return self.get_provider_display()

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key_encrypted)

    @property
    def api_key_masked(self) -> str:
        return f"••••{self.api_key_last4}" if self.has_api_key else ""

    def set_api_key(self, raw_key: str) -> None:
        raw_key = raw_key.strip()
        self.api_key_encrypted = crypto.encrypt(raw_key)
        self.api_key_last4 = raw_key[-4:]

    def get_api_key(self) -> str:
        return crypto.decrypt(self.api_key_encrypted) if self.has_api_key else ""


class LLMModelOption(TimeStampedModel):
    provider = models.CharField(max_length=20, choices=Provider.choices)
    model_id = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    supports_pdf_input = models.BooleanField(default=False)
    max_output_tokens = models.PositiveIntegerField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["provider", "order", "model_id"]
        constraints = [
            models.UniqueConstraint(fields=["provider", "model_id"], name="uniq_provider_model")
        ]

    def __str__(self):
        return f"{self.provider}:{self.model_id}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_default:
                LLMModelOption.objects.filter(provider=self.provider, is_default=True).exclude(
                    pk=self.pk
                ).update(is_default=False)
            super().save(*args, **kwargs)


def default_task_overrides():
    return {
        "evaluation.judge": {"temperature": 0.0},
        "bid.extract": {"temperature": 0.0},
        "draft.*": {"temperature": 0.3},
    }


class LLMSettings(TimeStampedModel):
    """Singleton (pk=1) holding the active provider/model and generation parameters."""

    active_provider = models.CharField(
        max_length=20, choices=Provider.choices, default=Provider.ANTHROPIC
    )
    active_model = models.ForeignKey(
        LLMModelOption, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    temperature = models.FloatField(default=0.2)
    max_output_tokens = models.PositiveIntegerField(default=8192)
    timeout_sec = models.PositiveIntegerField(default=180)
    max_retries = models.PositiveIntegerField(default=2)
    json_mode = models.BooleanField(default=True)
    per_task_overrides = models.JSONField(default=default_task_overrides, blank=True)

    class Meta:
        verbose_name = "LLM settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "LLMSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
