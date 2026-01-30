from django.contrib import admin
from django.urls import path

from apps.core import views as core_views
from apps.analysis import views as analysis_views

urlpatterns = [
    path("", core_views.root, name="root"),
    path("admin/", admin.site.urls),
    path("login", core_views.login_view, name="login"),
    path("logout", core_views.logout_view, name="logout"),
    path("upload", analysis_views.upload_view, name="upload"),
    path("jobs/<uuid:job_id>/progress", analysis_views.progress_view, name="progress"),
    path("jobs/<uuid:job_id>/result", analysis_views.result_view, name="result"),
    path("jobs/<uuid:job_id>/clear", analysis_views.clear_view, name="clear"),
    path("help", core_views.help_view, name="help"),
]
