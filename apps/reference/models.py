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
