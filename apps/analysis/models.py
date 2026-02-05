import uuid

from django.db import models

from apps.reference.models import EventType


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.ForeignKey(
        EventType, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )

    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"

    def __str__(self) -> str:
        return str(self.id)


class PortalEvent(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    detected_at = models.DateTimeField()
    subdivision_id = models.UUIDField()
    subdivision_fullname = models.TextField()
    event_type_id = models.UUIDField(null=True, blank=True)
    event_type_name = models.TextField(null=True, blank=True)
    raw_text = models.TextField()
    offenders = models.JSONField(default=list)
    is_test = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "portal_events"
        verbose_name = "TEST/PORTAL: событие"
        verbose_name_plural = "TEST/PORTAL: события"

    def __str__(self) -> str:
        return f"{self.subdivision_fullname} @ {self.detected_at}"
