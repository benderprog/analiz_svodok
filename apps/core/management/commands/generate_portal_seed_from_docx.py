from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.portal_seed_docx import generate_portal_seed_from_docx


class Command(BaseCommand):
    help = "Generate portal seed SQL from a DOCX fixture."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--docx",
            default="fixtures/test_svodka_semantic3.docx",
            help="Path to DOCX file with test summary paragraphs.",
        )
        parser.add_argument(
            "--output",
            default="seed/portal_data_generated.sql",
            help="Output path for generated SQL.",
        )
        parser.add_argument(
            "--divisions",
            default="configs/divisions.yaml",
            help="Path to divisions YAML.",
        )

    def handle(self, *args, **options) -> None:
        docx_path = Path(options["docx"])
        output_path = Path(options["output"])
        divisions_path = Path(options["divisions"])
        if not docx_path.is_absolute():
            docx_path = Path(settings.BASE_DIR) / docx_path
        if not output_path.is_absolute():
            output_path = Path(settings.BASE_DIR) / output_path
        if not divisions_path.is_absolute():
            divisions_path = Path(settings.BASE_DIR) / divisions_path
        generate_portal_seed_from_docx(docx_path, output_path, divisions_path)
        self.stdout.write(self.style.SUCCESS(f"Generated {output_path}"))
