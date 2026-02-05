from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
import uuid

import yaml
from django.conf import settings


@dataclass(frozen=True)
class SubdivisionSeed:
    id: int
    fullname: str


@dataclass(frozen=True)
class OffenderSeed:
    first_name: str
    middle_name: str
    last_name: str
    date_of_birth: date | None = None
    birth_year: int | None = None


@dataclass(frozen=True)
class EventSeed:
    id: str
    subdivision_id: int
    date_detection: datetime
    offenders: list[OffenderSeed]


@dataclass(frozen=True)
class DocxSeed:
    paragraph: str
    case: str


def build_local_portal_seed(scale: int = 10) -> tuple[list[SubdivisionSeed], list[EventSeed], list[DocxSeed]]:
    subdivisions = _load_divisions_from_yaml()

    base_events = [
        EventSeed(
            id="11111111-1111-1111-1111-111111111111",
            subdivision_id=1101,
            date_detection=datetime(2024, 1, 10, 12, 0),
            offenders=[
                OffenderSeed(
                    first_name="Иван",
                    middle_name="Иванович",
                    last_name="Иванов",
                    date_of_birth=date(1990, 5, 5),
                )
            ],
        ),
        EventSeed(
            id="22222222-2222-2222-2222-222222222222",
            subdivision_id=1102,
            date_detection=datetime(2024, 1, 11, 9, 30),
            offenders=[
                OffenderSeed(
                    first_name="Петр",
                    middle_name="Петрович",
                    last_name="Петров",
                    date_of_birth=date(1985, 3, 12),
                )
            ],
        ),
        EventSeed(
            id="33333333-3333-3333-3333-333333333333",
            subdivision_id=1202,
            date_detection=datetime(2024, 1, 12, 14, 20),
            offenders=[
                OffenderSeed(
                    first_name="Анна",
                    middle_name="Сергеевна",
                    last_name="Сидорова",
                    date_of_birth=date(1992, 7, 1),
                )
            ],
        ),
        EventSeed(
            id="44444444-4444-4444-4444-444444444444",
            subdivision_id=1201,
            date_detection=datetime(2024, 1, 13, 16, 45),
            offenders=[
                OffenderSeed(
                    first_name="Алексей",
                    middle_name="Николаевич",
                    last_name="Кузнецов",
                    date_of_birth=date(1978, 9, 9),
                )
            ],
        ),
        EventSeed(
            id="55555555-5555-5555-5555-555555555555",
            subdivision_id=1301,
            date_detection=datetime(2024, 1, 14, 10, 15),
            offenders=[
                OffenderSeed(
                    first_name="Роман",
                    middle_name="Романович",
                    last_name="Романов",
                    date_of_birth=date(1995, 12, 30),
                )
            ],
        ),
        EventSeed(
            id="66666666-6666-6666-6666-666666666666",
            subdivision_id=1101,
            date_detection=datetime(2024, 1, 14, 10, 15),
            offenders=[
                OffenderSeed(
                    first_name="Роман",
                    middle_name="Романович",
                    last_name="Романов",
                    date_of_birth=date(1995, 12, 30),
                )
            ],
        ),
    ]

    docx_events = [
        DocxSeed(
            case="3/3 совпало",
            paragraph=(
                "10.01.2024 12:00 службой ПОГЗ №2 (с. Васильки) выявлены: "
                "Иванов Иван Иванович 05.05.1990"
            ),
        ),
        DocxSeed(
            case="2/3 совпало (подразделение отличается)",
            paragraph=(
                "11.01.2024 09:30 на посту ОПК «Центральное» (г. Южный) задержан: "
                "Петров Петр Петрович 12.03.1985"
            ),
        ),
        DocxSeed(
            case="время в окне ±30 минут",
            paragraph=(
                "12.01.2024 14:20 в районе ПОГК «Северная» (пгт Северный): "
                "Сидорова Анна Сергеевна 01.07.1992"
            ),
        ),
        DocxSeed(
            case="нарушитель отличается",
            paragraph=(
                "13.01.2024 16:45 службой ПЗ1 выявлены: "
                "Кузнецов Алексей Николаевич 09.09.1978, "
                "Иванова Мария Ивановна 1990"
            ),
        ),
        DocxSeed(
            case="не найдено",
            paragraph=(
                "15.01.2024 08:00 ПОГК «Солнечная» (пгт Солнечный): "
                "Орлов Олег Олегович 10.10.1991"
            ),
        ),
        DocxSeed(
            case="дубликаты",
            paragraph=(
                "14.01.2024 10:15 ПОГЗ №3 (с. Южные Ключи): "
                "Романов Роман Романович 30.12.1995"
            ),
        ),
    ]

    desired_total = max(scale, len(base_events))
    extra_count = desired_total - len(base_events)
    extra_events: list[EventSeed] = []
    start_time = datetime(2024, 2, 1, 9, 0)
    for index in range(extra_count):
        extra_events.append(
            EventSeed(
                id=_build_event_uuid(index),
                subdivision_id=subdivisions[index % len(subdivisions)].id,
                date_detection=start_time + timedelta(minutes=index * 5),
                offenders=[
                    OffenderSeed(
                        first_name="Тест",
                        middle_name="Тестович",
                        last_name=f"Тестов{index}",
                        date_of_birth=date(1990, 1, 1),
                    )
                ],
            )
        )

    return subdivisions, base_events + extra_events, docx_events


def _build_event_uuid(index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"portal-event-{index}"))


def _load_divisions_from_yaml() -> list[SubdivisionSeed]:
    config_path = Path(settings.BASE_DIR) / "configs" / "divisions.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Не найден файл подразделений: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}

    subdivisions: list[SubdivisionSeed] = []
    for pu_entry in data.get("pus") or []:
        for subdivision in pu_entry.get("subdivisions") or []:
            subdivision_id = subdivision.get("id")
            if subdivision_id is None:
                continue
            fullname = subdivision.get("fullname") or subdivision.get("full_name")
            if not fullname:
                fullname = _build_full_name(
                    subdivision.get("type"),
                    subdivision.get("number"),
                    subdivision.get("name"),
                    subdivision.get("locality"),
                )
            subdivisions.append(
                SubdivisionSeed(id=int(subdivision_id), fullname=str(fullname))
            )

    return subdivisions


def _build_full_name(
    div_type: str | None,
    number: int | None,
    name: str | None,
    locality: dict[str, Any] | None,
) -> str:
    short_name = _build_short_name(div_type, number, name)
    locality_label = _format_locality(locality)
    if locality_label:
        return f"{short_name} ({locality_label})"
    return short_name


def _build_short_name(div_type: str | None, number: int | None, name: str | None) -> str:
    if not div_type:
        return ""
    if number is not None:
        return f"{div_type} №{number}"
    if name:
        return f"{div_type} «{name}»"
    return str(div_type)


def _format_locality(locality: dict[str, Any] | None) -> str:
    if not locality:
        return ""
    kind = str(locality.get("kind") or "").strip()
    name = str(locality.get("name") or "").strip()
    if not kind or not name:
        return ""
    return f"{kind} {name}"
