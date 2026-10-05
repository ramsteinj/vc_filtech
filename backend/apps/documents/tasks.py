"""Background job handlers for documents (registered in DocumentsConfig.ready)."""

from apps.core.jobs import JobError, job_handler

from .loader import load_company
from .models import Document
from .pipeline import run_pipeline


@job_handler("EXTRACT_DOCUMENT")
def extract_document(job, report):
    document = Document.objects.filter(pk=job.target_id).first()
    if document is None:
        raise JobError("문서를 찾을 수 없습니다.")
    payload = job.payload or {}
    return run_pipeline(
        document,
        from_step=payload.get("from_step", "parse"),
        apply=payload.get("apply"),
        report=report,
    )


@job_handler("LOAD_INITIAL_DATA")
def load_initial_data(job, report):
    payload = job.payload or {}
    if payload.get("only") == "bids":
        raise JobError("입찰 공고 적재는 Phase 5에서 지원됩니다.")
    try:
        return {"company": load_company(mode=payload.get("mode", "skip"), report=report)}
    except FileNotFoundError as exc:
        raise JobError(str(exc)) from exc
