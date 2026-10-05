"""Document pipeline: parse → classify → extract → map (specs/06 §1).

Each step can be re-run on its own via run_pipeline(from_step=...).
LLM classification/extraction is plugged in during Phase 4; until then only rules run.
"""

import logging
from collections.abc import Callable

from django.db import transaction

from apps.core.app_settings import get_setting

from .classify import classify
from .extractors import EXTRACTORS, MetaValue
from .models import Document, DocumentMetadata
from .parsers import ParseError, parse_file
from .parsers.base import normalize_text

logger = logging.getLogger(__name__)

STEPS = ["parse", "classify", "extract", "map"]

Report = Callable[[int, str], None]


def _noop(progress: int, message: str = "") -> None:
    pass


def _set_status(document: Document, status: str, error: str = "") -> None:
    document.status = status
    document.error_message = error
    document.save(update_fields=["status", "error_message", "updated_at"])


def parse_step(document: Document) -> bool:
    """Fill extracted_text/tables. Returns False when the pipeline should stop."""
    _set_status(document, Document.Status.PARSING)
    if not document.file:
        text = normalize_text(document.source_text)
        document.extracted_text, document.extracted_tables, document.page_count = text, [], None
        document.save(update_fields=["extracted_text", "extracted_tables", "page_count"])
        _set_status(document, Document.Status.PARSED)
        return True
    try:
        result = parse_file(
            document.file.path,
            document.file_format,
            min_chars_per_page=get_setting("extraction.min_text_chars_per_page"),
        )
    except ParseError as exc:
        _set_status(document, Document.Status.FAILED, str(exc))
        return False
    document.extracted_text = result.text
    document.extracted_tables = result.tables
    document.page_count = result.page_count
    document.save(update_fields=["extracted_text", "extracted_tables", "page_count"])
    if result.is_scanned:
        # LLM PDF transcription is added in Phase 4 (specs/06 §2.2).
        _set_status(
            document,
            Document.Status.NEEDS_OCR,
            "스캔 문서입니다. 텍스트를 직접 입력하거나 LLM 설정 후 다시 처리하세요.",
        )
        return False
    _set_status(document, Document.Status.PARSED)
    return True


def classify_step(document: Document, path_hint: str | None = None) -> None:
    if document.category_source == Document.CategorySource.MANUAL and document.category_id:
        return
    result = classify(
        filename=document.original_filename or document.title,
        text=document.extracted_text,
        owner_type=document.owner_type,
        path_hint=path_hint,
    )
    document.category = result.schema
    document.category_confidence = result.confidence
    document.category_source = Document.CategorySource.AUTO
    document.save(update_fields=["category", "category_confidence", "category_source"])


def save_metadata(document: Document, values: dict[str, MetaValue], source: str) -> int:
    """Upsert extracted values; locked rows are never touched (specs/06 §5.3)."""
    schema = document.category
    locked = set(document.metadata.filter(is_locked=True).values_list("key", flat=True))
    saved = 0
    with transaction.atomic():
        document.metadata.filter(source=source, is_locked=False).exclude(
            key__in=list(values)
        ).delete()
        for key, item in values.items():
            if key in locked:
                continue
            field = schema.field(key) if schema else None
            DocumentMetadata.objects.update_or_create(
                document=document,
                key=key,
                defaults={
                    "label": (field or {}).get("label", key),
                    "value": item.value,
                    "raw_value": item.raw or "",
                    "unit": item.unit or (field or {}).get("unit", ""),
                    "source": source,
                    "confidence": item.confidence,
                    "evidence_page": item.page,
                    "evidence_quote": (item.quote or "")[:300],
                },
            )
            saved += 1
    return saved


def extract_step(document: Document) -> None:
    if document.category is None:
        _set_status(
            document,
            Document.Status.PARSED,
            "문서 분류를 판별하지 못했습니다. 분류를 직접 지정한 뒤 다시 추출하세요.",
        )
        return
    _set_status(document, Document.Status.EXTRACTING)
    extractor = EXTRACTORS.get(document.category.code)
    if extractor is not None:
        values = extractor(document.extracted_text, document.extracted_tables)
        save_metadata(document, values, DocumentMetadata.Source.RULE)
    _set_status(document, Document.Status.EXTRACTED)


def map_step(document: Document) -> list[dict]:
    from apps.company.mapping import apply

    return [change.as_dict() for change in apply(document)]


def run_pipeline(
    document: Document,
    *,
    from_step: str = "parse",
    path_hint: str | None = None,
    apply: bool | None = None,
    report: Report = _noop,
) -> dict:
    """Run steps from `from_step`. Company documents are mapped when `apply` (or the
    extraction.auto_apply_company setting) is true."""
    if from_step not in STEPS:
        raise ValueError(f"unknown step: {from_step}")
    start = STEPS.index(from_step)
    result: dict = {"document_id": document.pk}

    if start <= 0:
        report(10, "텍스트 추출 중")
        if not parse_step(document):
            result["status"] = document.status
            return result
    if start <= 1:
        report(40, "문서 분류 중")
        classify_step(document, path_hint)
    if start <= 2:
        report(60, "메타데이터 추출 중")
        extract_step(document)

    should_map = apply if apply is not None else get_setting("extraction.auto_apply_company")
    if (
        start <= 3
        and should_map
        and document.owner_type == "COMPANY"
        and document.status == Document.Status.EXTRACTED
    ):
        report(85, "회사 자료에 반영 중")
        result["changes"] = map_step(document)
    document.refresh_from_db()
    result["status"] = document.status
    return result
