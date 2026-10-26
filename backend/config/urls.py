from django.contrib import admin
from django.urls import include, path, re_path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Versionamento na URL (URLPathVersioning): /api/v1/...
    re_path(r"^api/(?P<version>v1)/", include("apps.api.v1.urls")),
]
