from django.conf import settings
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.llm.models import LLMSettings
from apps.llm.services import is_llm_configured

from .jobs import cancel, retry
from .models import Job
from .permissions import IsAdminRole, ReadAnyWriteAdmin
from .serializers import JobSerializer


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


class JobViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """/api/jobs — users may poll their own jobs; admins see all (specs/10)."""

    serializer_class = JobSerializer

    def get_permissions(self):
        if self.action == "retrieve":
            return [ReadAnyWriteAdmin()]
        return [IsAdminRole()]

    def get_queryset(self):
        qs = Job.objects.all()
        user = self.request.user
        if self.action == "retrieve" and not user.is_admin_role:
            qs = qs.filter(created_by=user)
        params = self.request.query_params
        for field in ("status", "type"):
            if params.get(field):
                qs = qs.filter(**{field: params[field]})
        return qs

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        job = self.get_object()
        if job.status not in ("FAILED", "CANCELLED"):
            raise ValidationError({"detail": ["실패하거나 취소된 작업만 다시 실행할 수 있습니다."]})
        return Response(JobSerializer(retry(job)).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        job = self.get_object()
        if not cancel(job):
            raise ValidationError({"detail": ["대기 중인 작업만 취소할 수 있습니다."]})
        job.refresh_from_db()
        return Response(JobSerializer(job).data)
