from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand
from docx import Document

from apps.core.management.portal_seed import build_local_portal_seed


class Command(BaseCommand):
    help = "Create a DOCX file with paragraphs that match local portal test data."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--out",
            default="out/test.docx",
            help="Путь для сохранения DOCX (по умолчанию out/test.docx).",
        )

    def handle(self, *args, **options) -> None:
        output_path = Path(options["out"]).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        _subdivisions, _events, docx_events = build_local_portal_seed()

        document = Document()
        for docx_event in docx_events:
            document.add_paragraph(docx_event.paragraph)

        document.save(output_path)
        self.stdout.write(self.style.SUCCESS(f"DOCX сохранён: {output_path}"))
