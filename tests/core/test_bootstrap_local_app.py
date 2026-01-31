import pytest
from django.core.management import call_command

from apps.core.management.commands.bootstrap_local_app import TEST_PU, TEST_SUBDIVISIONS
from apps.core.models import Setting
from apps.reference.models import Pu, SubdivisionRef


@pytest.mark.django_db
def test_bootstrap_local_app_is_idempotent() -> None:
    call_command("bootstrap_local_app", "--reset")

    semantic = Setting.objects.get(key="semantic_threshold_subdivision")
    window = Setting.objects.get(key="time_window_minutes")
    assert semantic.value == 0.80
    assert window.value == 30

    pu = Pu.objects.get(short_name=TEST_PU["short_name"], full_name=TEST_PU["full_name"])
    assert SubdivisionRef.objects.filter(pu=pu).count() == len(TEST_SUBDIVISIONS)

    call_command("bootstrap_local_app")
    assert SubdivisionRef.objects.filter(pu=pu).count() == len(TEST_SUBDIVISIONS)

    call_command("bootstrap_local_app", "--reset")
    assert SubdivisionRef.objects.filter(pu=pu).count() == len(TEST_SUBDIVISIONS)
