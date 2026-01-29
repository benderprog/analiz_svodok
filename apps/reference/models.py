from django.db import models


class Pu(models.Model):
    short_name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.short_name


class SubdivisionRef(models.Model):
    pu = models.ForeignKey(Pu, on_delete=models.CASCADE)
    short_name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.short_name
