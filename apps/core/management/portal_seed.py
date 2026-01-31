from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


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
    id: int
    subdivision_id: int
    date_detection: datetime
    offenders: list[OffenderSeed]


@dataclass(frozen=True)
class DocxSeed:
    paragraph: str
    case: str


def build_local_portal_seed(scale: int = 10) -> tuple[list[SubdivisionSeed], list[EventSeed], list[DocxSeed]]:
    subdivisions = [
        SubdivisionSeed(id=101, fullname="ПУ-1 Центральное"),
        SubdivisionSeed(id=102, fullname="ПУ-2 Северное"),
        SubdivisionSeed(id=103, fullname="ПУ-3 Южное"),
    ]

    base_events = [
        EventSeed(
            id=1001,
            subdivision_id=101,
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
            id=1002,
            subdivision_id=102,
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
            id=1003,
            subdivision_id=101,
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
            id=1004,
            subdivision_id=103,
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
            id=1005,
            subdivision_id=101,
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
            id=1006,
            subdivision_id=101,
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
                "10.01.2024 12:00 ПУ-1 Центральное: "
                "Иванов Иван Иванович 05.05.1990"
            ),
        ),
        DocxSeed(
            case="2/3 совпало (подразделение отличается)",
            paragraph=(
                "11.01.2024 09:30 ПУ-1 Центральное: "
                "Петров Петр Петрович 12.03.1985"
            ),
        ),
        DocxSeed(
            case="время в окне ±30 минут",
            paragraph=(
                "12.01.2024 14:00 ПУ-1 Центральное: "
                "Сидорова Анна Сергеевна 01.07.1992"
            ),
        ),
        DocxSeed(
            case="нарушитель отличается",
            paragraph=(
                "13.01.2024 16:45 ПУ-3 Южное: "
                "Кузнецов Алексей Николаевич 09.09.1978, "
                "Иванова Мария Ивановна 1990"
            ),
        ),
        DocxSeed(
            case="не найдено",
            paragraph=(
                "15.01.2024 08:00 ПУ-2 Северное: "
                "Орлов Олег Олегович 10.10.1991"
            ),
        ),
        DocxSeed(
            case="дубликаты",
            paragraph=(
                "14.01.2024 10:15 ПУ-1 Центральное: "
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
                id=2000 + index,
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
