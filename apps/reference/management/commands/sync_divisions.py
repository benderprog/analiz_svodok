from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.reference.models import Pu, SubdivisionRef


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return Path(settings.BASE_DIR) / path


def _format_locality(locality: dict[str, Any] | None) -> str:
    if not locality:
        return ""
    kind = str(locality.get("kind") or "").strip()
    name = str(locality.get("name") or "").strip()
    if not kind or not name:
        return ""
    return f"{kind} {name}"


def _build_short_name(div_type: str, number: int | None, name: str | None) -> str:
    if number is not None:
        return f"{div_type} №{number}"
    if name:
        return f"{div_type} «{name}»"
    return div_type


def _build_full_name(
    div_type: str, number: int | None, name: str | None, locality: dict[str, Any] | None
) -> str:
    short_name = _build_short_name(div_type, number, name)
    locality_label = _format_locality(locality)
    if locality_label:
        return f"{short_name} ({locality_label})"
    return short_name


class Command(BaseCommand):
    help = "Sync subdivision reference data from a YAML file."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--file",
            default="configs/divisions.yaml",
            help="Путь к YAML с подразделениями (по умолчанию configs/divisions.yaml).",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        config_path = _resolve_path(options["file"])
        if not config_path.exists():
            raise CommandError(f"Файл справочника не найден: {config_path}")

        with config_path.open("r", encoding="utf-8") as handle:
            data: dict[str, Any] = yaml.safe_load(handle) or {}

        pus = data.get("pus") or []
        created = 0
        updated = 0
        alias_count = 0

        for pu_entry in pus:
            pu_name = pu_entry.get("name")
            if not pu_name:
                raise CommandError("Каждое ПУ должно содержать поле 'name'.")
            pu_full_name = pu_entry.get("full_name") or pu_name
            pu, _ = Pu.objects.update_or_create(
                short_name=pu_name,
                defaults={"full_name": pu_full_name},
            )

            subdivisions = pu_entry.get("subdivisions") or []
            for subdivision in subdivisions:
                div_type = subdivision.get("type")
                if not div_type:
                    raise CommandError("Подразделение должно содержать поле 'type'.")

                number = subdivision.get("number")
                name = subdivision.get("name")
                locality = subdivision.get("locality") or {}
                full_name = subdivision.get("fullname") or subdivision.get("full_name")
                if not full_name:
                    full_name = _build_full_name(div_type, number, name, locality)
                short_name = subdivision.get("short_name")
                if not short_name:
                    short_name = _build_short_name(div_type, number, name)

                code = subdivision.get("code")
                raw_aliases = subdivision.get("aliases") or []
                aliases = [
                    str(alias).strip()
                    for alias in raw_aliases
                    if str(alias).strip()
                ]
                alias_count += len(aliases)

                defaults = {
                    "pu": pu,
                    "short_name": short_name,
                    "full_name": full_name,
                    "aliases": aliases,
                    "code": code,
                }

                if code:
                    _, created_flag = SubdivisionRef.objects.update_or_create(
                        code=code,
                        defaults=defaults,
                    )
                else:
                    _, created_flag = SubdivisionRef.objects.update_or_create(
                        full_name=full_name,
                        defaults=defaults,
                    )

                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Справочник подразделений синхронизирован. "
                f"Создано: {created}, обновлено: {updated}, алиасов: {alias_count}."
            )
        )
