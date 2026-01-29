from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self) -> None:
        post_migrate.connect(create_default_admin, sender=self)


def create_default_admin(**_kwargs) -> None:
    from .models import AppUser, Setting

    admin_login = settings.APP_ADMIN_LOGIN
    admin_password = settings.APP_ADMIN_PASSWORD
    if admin_login and admin_password:
        if not AppUser.objects.filter(login=admin_login).exists():
            AppUser.objects.create_superuser(login=admin_login, password=admin_password)
    Setting.objects.get_or_create(
        key="semantic_threshold_subdivision", defaults={"value": 0.80}
    )
    Setting.objects.get_or_create(key="time_window_minutes", defaults={"value": 30})
