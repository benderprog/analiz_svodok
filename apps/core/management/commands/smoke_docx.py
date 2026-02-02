from __future__ import annotations

import json
import time
from pathlib import Path
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from docx import Document

from apps.analysis.tasks import analyze_docx
from apps.analysis.services.result_store import ResultStore


class Command(BaseCommand):
    help = "Run a smoke analysis on a DOCX file and save summary JSON."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--path",
            required=True,
            help="Path to TXT fixture (e.g. /data/fixtures/text/sample_01.txt).",
        )
        parser.add_argument(
            "--output",
            default="/data/artifacts/smoke_result.json",
            help="Where to write smoke result JSON (default: /data/artifacts/smoke_result.json).",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=300,
            help="Max seconds to wait for analysis result (default: 300).",
        )
        parser.add_argument(
            "--use-celery",
            action="store_true",
            help="Run analysis via Celery and wait for result.",
        )

    def handle(self, *args, **options) -> None:
        txt_path = Path(options["path"]).resolve()
        if not txt_path.exists():
            raise CommandError(f"Fixture not found: {txt_path}")
        if txt_path.suffix.lower() != ".txt":
            raise CommandError("Smoke fixtures must be .txt files.")

        output_path = Path(options["output"]).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        paragraphs = self._read_txt_paragraphs(txt_path)
        if not paragraphs:
            raise CommandError("Smoke fixture is empty or has no paragraphs.")

        docx_path = output_path.parent / f"smoke_{uuid4().hex}.docx"
        self._write_docx(docx_path, paragraphs)

        job_id = uuid4().hex
        store = ResultStore()
        store.create_job(job_id)

        if options["use_celery"]:
            analyze_docx.delay(job_id, str(docx_path))
        else:
            analyze_docx(job_id, str(docx_path))

        start = time.monotonic()
        result_payload: dict | None = None
        while time.monotonic() - start < options["timeout"]:
            payload = store.get(job_id)
            if payload.get("status") == "done":
                result_payload = payload
                break
            time.sleep(1)

        if result_payload is None:
            raise CommandError("Smoke test timed out waiting for results.")

        items = result_payload.get("result", {}).get("items", [])
        found_events = sum(1 for item in items if item.get("event_found"))
        summary = {
            "job_id": job_id,
            "status": result_payload.get("status"),
            "progress": result_payload.get("progress"),
            "items_total": len(items),
            "events_found": found_events,
        }
        result_payload["summary"] = summary

        output_path.write_text(
            json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Smoke test finished: "
                f"items={summary['items_total']}, events_found={summary['events_found']}"
            )
        )

        if summary["items_total"] == 0:
            raise CommandError("Smoke test failed: no parsed items found.")

    @staticmethod
    def _read_txt_paragraphs(path: Path) -> list[str]:
        content = path.read_text(encoding="utf-8")
        chunks = [chunk.strip() for chunk in content.split("\n\n")]
        return [chunk for chunk in chunks if chunk]

    @staticmethod
    def _write_docx(path: Path, paragraphs: list[str]) -> None:
        document = Document()
        for paragraph in paragraphs:
            document.add_paragraph(paragraph)
        document.save(path)
