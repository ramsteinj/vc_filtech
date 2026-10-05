from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import LLMSettingsView, ModelOptionViewSet, ProviderConfigView, ProviderVerifyView

router = SimpleRouter(trailing_slash=False)
router.register("settings/llm/models", ModelOptionViewSet, basename="llm-model")

urlpatterns = [
    path("settings/llm", LLMSettingsView.as_view(), name="llm-settings"),
    path(
        "settings/llm/providers/<str:provider>",
        ProviderConfigView.as_view(),
        name="llm-provider",
    ),
    path(
        "settings/llm/providers/<str:provider>/verify",
        ProviderVerifyView.as_view(),
        name="llm-provider-verify",
    ),
    *router.urls,
]
