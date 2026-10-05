import json

from django.core.management.base import BaseCommand, CommandError

from apps.documents.loader import load_company


class Command(BaseCommand):
    help = "Load initial-data/ into the database (specs/12-initial-data.md)."

    def add_arguments(self, parser):
        parser.add_argument("--mode", choices=["skip", "update"], default="skip")
        parser.add_argument("--only", choices=["company", "bids"], default=None)
        parser.add_argument(
            "--no-llm", action="store_true", help="Rule extraction only (no LLM calls)."
        )

    def handle(self, *args, mode, only, no_llm, **options):
        if only == "bids":
            raise CommandError("입찰 공고 적재(--only bids)는 Phase 5에서 지원됩니다.")
        try:
            summary = load_company(
                mode=mode, report=lambda p, m="": self.stdout.write(f"[{p:3d}%] {m}")
            )
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps({"company": summary}, ensure_ascii=False, indent=2))
        if only is None:
            self.stdout.write("입찰 공고(bid_sample) 적재는 Phase 5에서 추가됩니다.")
        if summary["failed"]:
            raise CommandError(f"{len(summary['failed'])}개 파일 처리 실패")
