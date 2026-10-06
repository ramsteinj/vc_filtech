"""Evaluation context: reference date and company data loaded once per bid (specs/08 §4–5)."""

from dataclasses import dataclass, field
from datetime import date

from django.utils import timezone

from apps.company.models import Certificate, Company, DeliveryRecord, Product, TestReport
from apps.core.app_settings import get_setting


def reference_date(bid, mode: str | None = None) -> tuple[date, bool]:
    """Return (date, is_simulation) per evaluation.reference_date_mode.

    AUTO: bid close date if it is still ahead, otherwise today (a past notice is evaluated
    as a re-bid today — is_simulation=True).
    """
    mode = mode or get_setting("evaluation.reference_date_mode")
    today = timezone.localdate()
    close = timezone.localdate(bid.bid_close_at) if bid.bid_close_at else None
    if mode == "TODAY" or close is None:
        return today, bool(close and close < today)
    if mode == "BID_CLOSE":
        return close, False
    return (close, False) if close >= today else (today, True)


@dataclass
class EvaluationContext:
    reference_date: date
    is_simulation: bool
    company: Company
    certificates: list = field(default_factory=list)
    delivery_records: list = field(default_factory=list)
    products: list = field(default_factory=list)
    test_reports: list = field(default_factory=list)
    expiring_days: int = 90

    @classmethod
    def for_bid(cls, bid, mode: str | None = None) -> "EvaluationContext":
        ref, simulation = reference_date(bid, mode)
        return cls(
            reference_date=ref,
            is_simulation=simulation,
            company=Company.load(),
            certificates=list(Certificate.objects.all()),
            delivery_records=list(DeliveryRecord.objects.prefetch_related("products")),
            products=list(Product.objects.filter(is_active=True)),
            test_reports=list(TestReport.objects.select_related("product")),
            expiring_days=get_setting("evaluation.cert_expiring_days"),
        )
