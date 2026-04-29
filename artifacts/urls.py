from django.urls import path
from . import views

urlpatterns = [
    path("", views.artifact_list, name="artifact_list"),
    path("stats/", views.stats_view, name="stats"),
    path("artifact/new/", views.artifact_create, name="artifact_create"),
    path("artifact/<int:pk>/", views.artifact_detail, name="artifact_detail"),
    path("artifact/<int:pk>/edit/", views.artifact_edit, name="artifact_edit"),
    path("artifact/<int:pk>/delete/", views.artifact_delete, name="artifact_delete"),
    path("artifact/<int:pk>/version/add/", views.version_add, name="version_add"),
    path("artifact/<int:pk>/version/<int:version_number>/", views.version_detail, name="version_detail"),
    path("artifact/<int:pk>/version/<int:version_number>/edit/", views.version_edit, name="version_edit"),
    path("artifact/<int:pk>/version/<int:version_number>/export/", views.version_export, name="version_export"),
]
