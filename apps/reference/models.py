import uuid

from django.core.exceptions import ValidationError
from django.db import models


class Pu(models.Model):
    short_name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.short_name


class SubdivisionRef(models.Model):
    pu = models.ForeignKey(Pu, on_delete=models.CASCADE)
    code = models.CharField(max_length=100, unique=True, blank=True, null=True)
    short_name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=255)
    aliases = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return self.short_name


class EventType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Тип события"
        verbose_name_plural = "Типы событий"

    def __str__(self) -> str:
        return self.name


class EventTypePattern(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.ForeignKey(
        EventType, on_delete=models.CASCADE, related_name="patterns"
    )
    pattern_text = models.TextField()
    koap_article = models.CharField(max_length=64, blank=True, default="")
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=100)

    class Meta:
        verbose_name = "Паттерн события"
        verbose_name_plural = "Паттерны событий"
        constraints = [
            models.UniqueConstraint(
                fields=["event_type", "pattern_text", "koap_article"],
                name="uq_event_type_pattern",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if not self.pattern_text or not self.pattern_text.strip():
            raise ValidationError({"pattern_text": "Текст паттерна не может быть пустым."})

    def __str__(self) -> str:
        return f"{self.event_type}: {self.pattern_text[:50]}"
