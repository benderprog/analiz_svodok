import pytest

from apps.core.models import AppUser


@pytest.mark.django_db
def test_create_superuser_defaults():
    user = AppUser.objects.create_superuser(login="admin", password="password")

    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("extra_fields", "message"),
    [
        ({"is_staff": False}, "Superuser must have is_staff=True."),
        ({"is_superuser": False}, "Superuser must have is_superuser=True."),
    ],
)
def test_create_superuser_requires_permissions(extra_fields, message):
    with pytest.raises(ValueError, match=message):
        AppUser.objects.create_superuser(login="admin", password="password", **extra_fields)
