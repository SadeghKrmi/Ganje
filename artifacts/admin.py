from django.contrib import admin
from .models import ResearchArtifact, ResearchVersion, Tag

admin.site.site_header = "Ganje Research Tracking"
admin.site.site_title  = "Ganje Admin"
admin.site.index_title = "Administration"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "color"]
    search_fields = ["name"]


class ResearchVersionInline(admin.TabularInline):
    model = ResearchVersion
    extra = 0
    readonly_fields = ["version_number", "created_at"]
    fields = ["version_number", "model_used", "codebase_ref", "created_at"]


@admin.register(ResearchArtifact)
class ResearchArtifactAdmin(admin.ModelAdmin):
    list_display = ["artifact_id", "title", "owner", "visibility", "category", "status", "version_count", "updated_at"]
    list_filter = ["status", "visibility", "category", "owner", "tags"]
    search_fields = ["title", "description", "codebase", "owner__email", "owner__username"]
    filter_horizontal = ["tags", "shared_with"]
    autocomplete_fields = ["owner"]
    inlines = [ResearchVersionInline]
    readonly_fields = ["uid", "created_at", "updated_at"]

    @admin.display(description="Versions")
    def version_count(self, obj):
        return obj.versions.count()


@admin.register(ResearchVersion)
class ResearchVersionAdmin(admin.ModelAdmin):
    list_display = ["__str__", "model_used", "codebase_ref", "created_at"]
    list_filter = ["model_used"]
    search_fields = ["artifact__title", "prompt", "analysis"]
    readonly_fields = ["version_number", "created_at"]
