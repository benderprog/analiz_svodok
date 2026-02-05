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
