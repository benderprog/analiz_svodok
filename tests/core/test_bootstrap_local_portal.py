import pytest
from django.core.management import call_command
from django.db import connections
from django.db.utils import OperationalError


def _portal_available() -> bool:
    try:
        with connections["portal"].cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except OperationalError:
        return False
    except Exception:
        return False


@pytest.mark.django_db(databases=["default", "portal"])
def test_bootstrap_local_portal_seeds_cases() -> None:
    if not _portal_available():
        pytest.skip("Portal database is not available in this environment")

    call_command("bootstrap_local_portal", "--reset", "--scale", "6")

    with connections["portal"].cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM subdivision WHERE is_test = true")
        subdivision_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM events WHERE is_test = true")
        event_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM offenders WHERE is_test = true")
        offender_count = cursor.fetchone()[0]

    assert subdivision_count >= 3
    assert event_count >= 6
    assert offender_count >= 6
