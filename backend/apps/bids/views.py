from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.jobs import enqueue
from apps.core.permissions import IsAdminRole, ReadAnyWriteAdmin
from apps.core.serializers import JobSerializer
from apps.documents.models import MetadataSchema
from apps.documents.validators import UploadRejected, validate_upload
from apps.llm.services import ensure_llm_configured

from .models import BidAttachment, BidItem, BidNotice, BidRequirement
from .serializers import (
    AttachmentSerializer,
    BidDetailSerializer,
    BidItemSerializer,
    BidListSerializer,
    BidRequirementSerializer,
    BidUpdateSerializer,
)
from .services import add_attachment, ensure_primary, set_primary

ORDERING = {
    "created": "-created_at",
    "-created": "created_at",
    "fit": "-fit_score",
    "closing": "bid_close_at",
    "-closing": "-bid_close_at",
}


def _attach_files(bid, request) -> list[dict]:
    """Attach uploaded files; returns skipped files with reasons."""
    skipped = []
    for uploaded in request.FILES.getlist("files"):
        try:
            validate_upload(uploaded, "BID")
        except UploadRejected as exc:
            skipped.append({"filename": uploaded.name, "reason": str(exc)})
            continue
        add_attachment(bid, file=uploaded, filename=uploaded.name, user=request.user)
    return skipped


def _default_title(source_text: str, files) -> str:
    """Until extraction fills it: first line of the pasted notice, else the first file name."""
    first_line = next((line.strip() for line in source_text.splitlines() if line.strip()), "")
    if first_line:
        return first_line
    return files[0].name.rsplit(".", 1)[0] if files else "새 입찰 공고"


def _delete_documents(documents) -> None:
    for document in documents:
        if document.file:
            document.file.delete(save=False)
        document.delete()


class BidViewSet(viewsets.ModelViewSet):
    """/api/bids — read for all users, write for admins (specs/10)."""

    permission_classes = [ReadAnyWriteAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_class(self):
        if self.action == "list":
            return BidListSerializer
        if self.action == "partial_update":
            return BidUpdateSerializer
        return BidDetailSerializer

    def get_queryset(self):
        qs = BidNotice.objects.annotate(
            item_count=Count("items", distinct=True),
            requirement_count=Count("requirements", distinct=True),
            attachment_count=Count("attachments", distinct=True),
        ).prefetch_related("items__matched_product")
        params = self.request.query_params
        for name in ("review_status", "outcome", "processing_status"):
            if params.get(name):
                qs = qs.filter(**{name: params[name]})
        if params.get("is_power_plant") in ("true", "false"):
            qs = qs.filter(is_power_plant=params["is_power_plant"] == "true")
        if params.get("fit_min"):
            qs = qs.filter(fit_score__gte=int(params["fit_min"]))
        now = timezone.now()
        if params.get("closing") == "open":
            qs = qs.filter(Q(bid_close_at__gte=now) | Q(bid_close_at__isnull=True))
        elif params.get("closing") == "closed":
            qs = qs.filter(bid_close_at__lt=now)
        if params.get("q"):
            q = params["q"]
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(notice_no__icontains=q)
                | Q(buyer_org__icontains=q)
                | Q(source_ref__icontains=q)
            )
        return qs.order_by(ORDERING.get(params.get("ordering", ""), "-created_at"), "-id")

    def create(self, request):
        source_text = (request.data.get("source_text") or "").strip()
        files = request.FILES.getlist("files")
        if not files and not source_text:
            raise ValidationError({"files": ["공고 파일을 올리거나 공고 본문을 입력하세요."]})
        title = (request.data.get("title") or "").strip()
        with transaction.atomic():
            bid = BidNotice.objects.create(
                title=(title or _default_title(source_text, files))[:300],
                source_text=source_text,
                created_by=request.user,
            )
            if source_text:
                add_attachment(bid, text=source_text, title=title or "공고 본문", user=request.user)
            skipped = _attach_files(bid, request)
            if not bid.attachments.exists():
                transaction.set_rollback(True)
                return Response(
                    {"detail": "업로드된 파일이 없습니다.", "code": "invalid", "skipped": skipped},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        bid = self.get_queryset().get(pk=bid.pk)
        return Response(
            {**BidDetailSerializer(bid).data, "skipped": skipped}, status=status.HTTP_201_CREATED
        )

    def partial_update(self, request, pk=None):
        bid = self.get_object()
        serializer = BidUpdateSerializer(bid, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(BidDetailSerializer(self.get_queryset().get(pk=bid.pk)).data)

    def perform_destroy(self, bid):
        documents = [a.document for a in bid.attachments.select_related("document")]
        bid.delete()
        _delete_documents(documents)

    @action(detail=True, methods=["post"], url_path="attachments", permission_classes=[IsAdminRole])
    def add_attachments(self, request, pk=None):
        bid = self.get_object()
        if not request.FILES.getlist("files"):
            raise ValidationError({"files": ["추가할 파일을 선택하세요."]})
        skipped = _attach_files(bid, request)
        attachments = AttachmentSerializer(
            bid.attachments.select_related("document"), many=True
        ).data
        return Response(
            {"attachments": attachments, "skipped": skipped}, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAdminRole])
    def extract(self, request, pk=None):
        bid = self.get_object()
        ensure_llm_configured()
        if bid.processing_status == BidNotice.ProcessingStatus.EXTRACTING:
            raise ValidationError({"detail": ["이미 추출 중입니다."]})
        job = enqueue("EXTRACT_BID", target=bid, user=request.user)
        return Response(
            {"job_id": job.pk, "job": JobSerializer(job).data}, status=status.HTTP_202_ACCEPTED
        )


class BidChildMixin:
    def get_bid(self) -> BidNotice:
        bid = BidNotice.objects.filter(pk=self.kwargs["bid_pk"]).first()
        if bid is None:
            raise NotFound("입찰 공고를 찾을 수 없습니다.")
        return bid

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "bid": self.get_bid()}


class AttachmentViewSet(
    BidChildMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """PATCH {category, is_primary, order} / DELETE /api/bids/{id}/attachments/{aid}"""

    permission_classes = [IsAdminRole]
    serializer_class = AttachmentSerializer
    http_method_names = ["patch", "delete"]

    def get_queryset(self):
        return BidAttachment.objects.filter(bid_id=self.kwargs["bid_pk"]).select_related("document")

    def partial_update(self, request, *args, **kwargs):
        attachment = self.get_object()
        data = request.data
        if "category" in data:
            schema = MetadataSchema.objects.filter(code=data["category"], owner_type="BID").first()
            if schema is None:
                raise ValidationError({"category": ["입찰 첨부 분류가 아닙니다."]})
            document = attachment.document
            document.category = schema
            document.category_source = document.CategorySource.MANUAL
            document.status = document.Status.PARSED  # metadata is re-extracted on the next run
            document.save(update_fields=["category", "category_source", "status"])
            attachment.role = schema.code
        if "order" in data:
            attachment.order = int(data["order"])
        attachment.save()
        if data.get("is_primary") is True:
            set_primary(attachment)
        attachment.refresh_from_db()
        return Response(AttachmentSerializer(attachment).data)

    def perform_destroy(self, attachment):
        bid = attachment.bid
        _delete_documents([attachment.document])
        ensure_primary(bid)


class BidItemViewSet(BidChildMixin, viewsets.ModelViewSet):
    """Items of a bid. Bid managers may only change `matched_product` (specs/10)."""

    serializer_class = BidItemSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        return (
            [ReadAnyWriteAdmin()] if self.action != "partial_update" else [_ItemPatchPermission()]
        )

    def get_queryset(self):
        return (
            BidItem.objects.filter(bid_id=self.kwargs["bid_pk"])
            .select_related("matched_product")
            .prefetch_related("product_matches__product")
        )

    def perform_create(self, serializer):
        serializer.save(bid=self.get_bid())


class _ItemPatchPermission(ReadAnyWriteAdmin):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        if request.user.is_admin_role:
            return True
        if set(request.data) - {"matched_product"}:
            raise PermissionDenied("입찰담당자는 매칭 제품만 변경할 수 있습니다.")
        return True


class BidRequirementViewSet(BidChildMixin, viewsets.ModelViewSet):
    """Key requirements. Admin edits lock the row against re-extraction (specs/04 §3.3)."""

    permission_classes = [ReadAnyWriteAdmin]
    serializer_class = BidRequirementSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        qs = BidRequirement.objects.filter(bid_id=self.kwargs["bid_pk"]).select_related(
            "item", "source_attachment__document"
        )
        category = self.request.query_params.get("category")
        return qs.filter(category=category) if category else qs

    def perform_create(self, serializer):
        bid = self.get_bid()
        serializer.save(
            bid=bid,
            source=BidRequirement.Source.MANUAL,
            is_locked=True,
            order=serializer.validated_data.get("order", bid.requirements.count()),
        )

    def perform_update(self, serializer):
        unlock = serializer.validated_data.get("is_locked") is False
        content_changed = any(k != "is_locked" for k in serializer.validated_data)
        extra = {}
        if content_changed:
            extra["source"] = BidRequirement.Source.MANUAL
        if not unlock:
            extra["is_locked"] = True
        serializer.save(**extra)
