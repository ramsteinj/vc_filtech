from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.llm.models import LLMSettings
from apps.llm.services import is_llm_configured


class SystemStatusView(APIView):
    """GET /api/system/status — public; drives the LLM-not-configured redirect (specs/03 §4)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        configured = is_llm_configured()
        return Response(
            {
                "llm_configured": configured,
                "active_provider": LLMSettings.load().active_provider if configured else None,
                "app_version": settings.APP_VERSION,
                "admin_must_change_password": User.objects.filter(
                    role=User.Role.ADMIN, is_active=True, must_change_password=True
                ).exists(),
            }
        )
