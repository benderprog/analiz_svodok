from django import forms


class EventTypeImportForm(forms.Form):
    file = forms.FileField(label="XLSX файл", required=True)
