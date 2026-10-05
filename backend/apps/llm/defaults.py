"""Seed data for LLM model options (specs/07-llm-integration.md §3).

Model IDs live only here as seed data; admins can add/edit them in the UI.
"""

from .models import LLMModelOption, LLMProviderConfig, LLMSettings, Provider

MODEL_OPTION_DEFAULTS = [
    # provider, model_id, display_name, supports_pdf_input, is_default
    (Provider.ANTHROPIC, "claude-opus-5-5", "Claude Opus 5.5", True, True),
    (Provider.ANTHROPIC, "claude-fable-5-1", "Claude Fable 5.1", True, False),
    (Provider.ANTHROPIC, "claude-sonnet-5-5", "Claude Sonnet 5.5", True, False),
    (Provider.ANTHROPIC, "claude-haiku-4-5-20251001", "Claude Haiku 4.5", True, False),
    (Provider.OPENAI, "gpt-6-astra", "GPT-6 Astra", False, True),
    (Provider.OPENAI, "gpt-6.1-sol", "GPT-6.1 Sol", False, False),
    (Provider.OPENAI, "gpt-6-luna", "GPT-6 Luna", False, False),
    (Provider.GEMINI, "gemini-3.8-flash", "Gemini 3.8 Flash", True, True),
    (Provider.GEMINI, "gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite", True, False),
]


def seed_llm_defaults() -> None:
    """Create missing providers, model options and the settings row. Never overwrites."""
    for provider in Provider.values:
        LLMProviderConfig.objects.get_or_create(provider=provider)

    has_default = set(
        LLMModelOption.objects.filter(is_default=True).values_list("provider", flat=True)
    )
    for order, (provider, model_id, name, pdf, is_default) in enumerate(MODEL_OPTION_DEFAULTS):
        if LLMModelOption.objects.filter(provider=provider, model_id=model_id).exists():
            continue
        LLMModelOption.objects.create(
            provider=provider,
            model_id=model_id,
            display_name=name,
            supports_pdf_input=pdf,
            is_default=is_default and provider not in has_default,
            order=order,
        )

    settings_row = LLMSettings.load()
    if settings_row.active_model is None:
        settings_row.active_model = LLMModelOption.objects.filter(
            provider=settings_row.active_provider, is_default=True
        ).first()
        settings_row.save()
