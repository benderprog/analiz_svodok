from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class AppUserManager(BaseUserManager):
    def create_user(self, login: str, password: str | None = None, **extra_fields):
        if not login:
            raise ValueError("Login is required")
        user = self.model(login=login, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, login: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(login, password, **extra_fields)


class AppUser(AbstractBaseUser, PermissionsMixin):
    login = models.CharField(max_length=150, unique=True)
    role = models.CharField(max_length=50, default="user")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = AppUserManager()

    USERNAME_FIELD = "login"
    REQUIRED_FIELDS: list[str] = []

    def __str__(self) -> str:
        return self.login


class Setting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self) -> str:
        return self.key
