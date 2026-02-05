from django.conf import settings
from django.contrib import admin
from django.db import models
from django.forms import widgets

from apps.analysis.models import PortalEvent


if getattr(settings, "PORTAL_ADMIN_ENABLED", False):
    @admin.register(PortalEvent)
    class PortalEventAdmin(admin.ModelAdmin):
        list_display = (
            "detected_at",
            "subdivision_fullname",
            "event_type_name",
            "is_test",
        )
        list_filter = ("is_test", "detected_at")
        search_fields = ("subdivision_fullname", "raw_text", "event_type_name")
        date_hierarchy = "detected_at"
        readonly_fields = ("created_at", "updated_at")
        fieldsets = (
            (
                None,
                {
                    "fields": (
                        "detected_at",
                        "subdivision_id",
                        "subdivision_fullname",
                        "event_type_id",
                        "event_type_name",
                        "raw_text",
                        "offenders",
                        "is_test",
                        "created_at",
                        "updated_at",
                    )
                },
            ),
        )
        formfield_overrides = {
            models.JSONField: {"widget": widgets.Textarea(attrs={"rows": 6, "cols": 80})},
        }
