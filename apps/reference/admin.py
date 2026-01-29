from django.contrib import admin

from .models import Pu, SubdivisionRef


@admin.register(Pu)
class PuAdmin(admin.ModelAdmin):
    list_display = ("short_name", "full_name")
    search_fields = ("short_name", "full_name")


@admin.register(SubdivisionRef)
class SubdivisionRefAdmin(admin.ModelAdmin):
    list_display = ("short_name", "full_name", "pu")
    search_fields = ("short_name", "full_name")
    list_filter = ("pu",)
