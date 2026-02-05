from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import path

from .forms import EventTypeImportForm
from .models import EventType, EventTypePattern, Pu, SubdivisionRef
from .services.event_type_import import import_event_types_from_xlsx


@admin.register(Pu)
class PuAdmin(admin.ModelAdmin):
    list_display = ("short_name", "full_name")
    search_fields = ("short_name", "full_name")


@admin.register(SubdivisionRef)
class SubdivisionRefAdmin(admin.ModelAdmin):
    list_display = ("code", "short_name", "full_name", "pu")
    search_fields = ("code", "short_name", "full_name")
    list_filter = ("pu",)


class EventTypePatternInline(admin.TabularInline):
    model = EventTypePattern
    extra = 0
    fields = ("pattern_text", "koap_article", "priority", "is_active")


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)
    inlines = (EventTypePatternInline,)
    change_list_template = "admin/reference/eventtype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-xlsx/",
                self.admin_site.admin_view(self.import_xlsx_view),
                name="reference_eventtype_import",
            )
        ]
        return custom_urls + urls

    def import_xlsx_view(self, request: HttpRequest) -> HttpResponse:
        if request.method == "POST":
            form = EventTypeImportForm(request.POST, request.FILES)
            if form.is_valid():
                report = import_event_types_from_xlsx(
                    form.cleaned_data["file"], dry_run=False
                )
                messages.success(
                    request,
                    (
                        "Импорт завершен: типов создано "
                        f"{report.types_created}, обновлено {report.types_updated}; "
                        "паттернов создано "
                        f"{report.patterns_created}, обновлено {report.patterns_updated}; "
                        f"пустых строк пропущено {report.ignored_rows}."
                    ),
                )
                for error in report.errors:
                    messages.error(request, error)
                return redirect("..")
        else:
            form = EventTypeImportForm()
        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "title": "Импорт типов событий из XLSX",
        }
        return render(request, "admin/reference/eventtype/import_xlsx.html", context)
