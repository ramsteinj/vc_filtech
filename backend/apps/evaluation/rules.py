"""Deterministic rule engine (specs/08 §5). A rule returns a RuleResult, or None to defer to
the LLM. Phase 5 implements the qualification rules used by the fit score (CERTIFICATION,
TRACK_RECORD); the remaining categories follow in Phase 6.
"""

from dataclasses import dataclass, field
from datetime import date

from .context import EvaluationContext
from .grades import meets, product_grades, required_grade

MET = "MET"
NEEDS_SUPPLEMENT = "NEEDS_SUPPLEMENT"
NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"


@dataclass
class RuleResult:
    verdict: str
    risk_level: str
    rationale: str
    company_value: str = ""
    action_items: list[str] = field(default_factory=list)
    evidences: list[dict] = field(default_factory=list)
    trace: dict = field(default_factory=dict)


def _cert_evidence(cert) -> dict:
    return {
        "type": "certificate",
        "id": cert.pk,
        "label": f"{cert.name or cert.cert_type} ({cert.cert_no})",
        "page": 1,
        "quote": f"유효 기간 {cert.valid_from} ~ {cert.valid_until}",
    }


def code_matches(cert_code: str, required: str) -> bool:
    """Hierarchical item codes: '40161505' matches '4016150501'; 'x' is a wildcard digit."""
    cert_code, required = str(cert_code).lower().strip(), str(required).strip()
    if not cert_code or not required:
        return False
    return all(c == "x" or c == r for c, r in zip(cert_code, required, strict=False))


def evaluate_certification(requirement, ctx: EvaluationContext) -> RuleResult | None:
    norm = requirement.normalized or {}
    cert_type = (norm.get("cert_type") or "").upper()
    mandatory = requirement.is_mandatory
    ref = ctx.reference_date

    if cert_type == "SME":
        company = ctx.company
        if company.is_sme is None:
            return RuleResult(
                NEEDS_CONFIRMATION,
                "HIGH" if mandatory else "MEDIUM",
                "회사 정보에 중소기업 여부가 입력되어 있지 않습니다.",
                action_items=["회사 정보에 중소기업 여부와 확인서 유효기간 입력"],
            )
        if not company.is_sme:
            return RuleResult(NEEDS_SUPPLEMENT, "HIGH", "회사 정보상 중소기업이 아닙니다.")
        if company.sme_cert_valid_until and company.sme_cert_valid_until < ref:
            return RuleResult(
                NEEDS_SUPPLEMENT,
                "HIGH",
                f"중소기업확인서 유효기간({company.sme_cert_valid_until})이 기준일({ref})보다 이전입니다.",
                action_items=["중소기업확인서 갱신"],
            )
        return RuleResult(MET, "LOW", "회사 정보상 중소기업이며 확인서가 유효합니다.", "중소기업")

    if cert_type == "G2B_ITEM":
        code = str(norm.get("product_code") or "")
        items = ctx.company.g2b_registered_items or []
        hit = next(
            (
                i
                for i in items
                if code
                and (code_matches(i.get("code", ""), code) or code_matches(code, i.get("code", "")))
            ),
            None,
        )
        if hit:
            return RuleResult(
                MET,
                "LOW",
                f"나라장터 등록 물품 {hit.get('code')}이(가) 요구 분류와 일치합니다.",
                str(hit.get("code")),
            )
        return RuleResult(
            NEEDS_CONFIRMATION,
            "HIGH" if mandatory else "MEDIUM",
            f"회사 정보에 요구 물품분류번호({code or '미상'})의 나라장터 등록 내역이 없습니다.",
            action_items=["나라장터 제조물품 등록 여부 확인"],
        )

    if not cert_type or cert_type == "OTHER":
        return None
    certs = [c for c in ctx.certificates if c.cert_type == cert_type]
    if not certs:
        return RuleResult(
            NEEDS_SUPPLEMENT,
            "HIGH" if mandatory else "MEDIUM",
            f"요구 인증({cert_type})을 보유하고 있지 않습니다.",
            action_items=[f"{cert_type} 인증 취득 또는 대체 서류 확인"],
        )
    cert = max(certs, key=lambda c: c.valid_until or date.min)
    status = cert.status_on(ref, ctx.expiring_days)
    evidence = [_cert_evidence(cert)]
    trace = {"reference_date": str(ref), "valid_until": str(cert.valid_until), "status": status}
    if status == "EXPIRED":
        return RuleResult(
            NEEDS_SUPPLEMENT,
            "HIGH" if mandatory else "MEDIUM",
            f"{cert.name or cert_type}({cert.cert_no})의 유효기간({cert.valid_until})이 기준일({ref})에 만료되었습니다.",
            f"{cert.cert_no} (만료 {cert.valid_until})",
            action_items=["인증 갱신(사후·갱신심사) 후 갱신 인증서 제출"],
            evidences=evidence,
            trace=trace,
        )
    if status == "UNKNOWN":
        return RuleResult(
            NEEDS_CONFIRMATION,
            "MEDIUM",
            "인증서 유효기간 정보가 없습니다.",
            cert.cert_no,
            evidences=evidence,
        )

    required_code = str(norm.get("product_code") or "")
    if required_code:
        codes = cert.product_codes or []
        if not any(code_matches(code, required_code) for code in codes):
            return RuleResult(
                NEEDS_CONFIRMATION,
                "HIGH" if mandatory else "MEDIUM",
                f"요구 세부품명번호 {required_code}와 보유 인증서({cert.cert_no})의 품목번호 {', '.join(codes) or '(없음)'}가 일치하는지 확인이 필요합니다.",
                f"{cert.cert_no} 품목번호 {', '.join(codes) or '-'}",
                action_items=["직접생산확인 품목(세부품명번호) 일치 여부 확인, 필요 시 추가 신청"],
                evidences=evidence,
                trace={**trace, "required_code": required_code, "cert_codes": codes},
            )
    required_note = norm.get("required_note")
    if required_note and required_note not in (cert.scope or ""):
        return RuleResult(
            NEEDS_CONFIRMATION,
            "HIGH" if mandatory else "MEDIUM",
            f"인증서 범위에 요구 특이사항 '{required_note}'이(가) 기재되어 있는지 확인이 필요합니다.",
            cert.scope,
            action_items=["인증서 필수특이사항 기재 여부 확인"],
            evidences=evidence,
            trace=trace,
        )
    risk = "MEDIUM" if status == "EXPIRING" else "LOW"
    note = " (만료 임박)" if status == "EXPIRING" else ""
    return RuleResult(
        MET,
        risk,
        f"{cert.name or cert_type}({cert.cert_no})이(가) 기준일({ref})에 유효합니다{note}.",
        f"{cert.cert_no} (~{cert.valid_until})",
        evidences=evidence,
        trace=trace,
    )


def _months_before(ref: date, years: int) -> str:
    return f"{ref.year - years:04d}-{ref.month:02d}"


def evaluate_track_record(requirement, ctx: EvaluationContext) -> RuleResult | None:
    norm = requirement.normalized or {}
    years = norm.get("period_years")
    product_types = [t for t in norm.get("product_types") or [] if t]
    grade = required_grade(norm.get("grade") or {})
    if not (years or product_types or grade):
        return None  # unstructured requirement → LLM

    cutoff = _months_before(ctx.reference_date, int(years)) if years else "0000-00"
    records = [r for r in ctx.delivery_records if r.delivered_ym >= cutoff]
    if norm.get("power_plant_only"):
        records = [r for r in records if r.is_power_plant]

    qualifying = []
    for record in records:
        products = list(record.products.all())
        if product_types:
            products = [p for p in products if p.filter_type in product_types]
        if grade:
            products = [p for p in products if any(meets(g, grade) for g in product_grades(p))]
        if products:
            qualifying.append((record, products))

    condition = norm.get("spec_condition") or ", ".join(
        filter(
            None,
            [
                f"최근 {years}년" if years else "",
                "/".join(product_types),
                str(grade) if grade else "",
            ],
        )
    )
    trace = {
        "reference_date": str(ctx.reference_date),
        "cutoff": cutoff,
        "candidates": len(records),
        "qualifying": [r.delivered_ym for r, _ in qualifying],
    }
    evidences = [
        {
            "type": "delivery_record",
            "id": record.pk,
            "label": f"{record.delivered_ym} {record.client} {record.project_name}",
            "page": 1,
            "quote": ", ".join(p.model_no for p in products),
        }
        for record, products in qualifying
    ]
    if not qualifying:
        return RuleResult(
            NEEDS_SUPPLEMENT,
            "HIGH" if requirement.is_mandatory else "MEDIUM",
            f"요구 실적 조건({condition})을 만족하는 납품실적이 없습니다.",
            action_items=["실적 요건 충족 여부 재확인 — 미충족 시 입찰 참가자격 미달"],
            trace=trace,
        )
    company_value = "; ".join(e["label"] for e in evidences)
    min_amount = norm.get("min_amount_krw")
    if min_amount:
        amounts = [r.amount_krw for r, _ in qualifying if r.amount_krw is not None]
        if not amounts:
            return RuleResult(
                NEEDS_CONFIRMATION,
                "MEDIUM",
                f"조건에 맞는 실적 {len(qualifying)}건이 있으나 금액 정보가 없어 기준금액 {min_amount:,}원 충족 여부를 확인해야 합니다.",
                company_value,
                action_items=["실적증명서의 계약금액 확인"],
                evidences=evidences,
                trace=trace,
            )
        if max(amounts) < min_amount:
            return RuleResult(
                NEEDS_SUPPLEMENT,
                "HIGH",
                f"조건에 맞는 실적의 최대 금액({max(amounts):,}원)이 기준금액({min_amount:,}원)에 못 미칩니다.",
                company_value,
                evidences=evidences,
                trace=trace,
            )
    return RuleResult(
        MET,
        "LOW",
        f"요구 실적 조건({condition})을 만족하는 납품실적 {len(qualifying)}건이 있습니다.",
        company_value,
        evidences=evidences,
        trace=trace,
    )


RULES = {
    "CERTIFICATION": evaluate_certification,
    "TRACK_RECORD": evaluate_track_record,
}


def evaluate(requirement, ctx: EvaluationContext) -> RuleResult | None:
    rule = RULES.get(requirement.category)
    return rule(requirement, ctx) if rule else None
