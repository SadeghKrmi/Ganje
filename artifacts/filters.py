import django_filters
from django import forms
from django.db import models

from .models import ResearchArtifact


class ArtifactFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(
        method="search_filter",
        label="Search",
        widget=forms.TextInput(attrs={
            "placeholder": "Search title, category, codebase, or tag…",
            "class": "form-control",
            "autocomplete": "off",
        }),
    )
    category = django_filters.CharFilter(
        field_name="category",
        lookup_expr="icontains",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Category"}),
    )
    status = django_filters.ChoiceFilter(
        choices=[("", "All statuses")] + ResearchArtifact.STATUS_CHOICES,
        empty_label=None,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    codebase = django_filters.CharFilter(
        field_name="codebase",
        lookup_expr="icontains",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Codebase"}),
    )
    tag = django_filters.CharFilter(
        field_name="tags__name",
        lookup_expr="iexact",
        label="Tag",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Tag"}),
    )

    class Meta:
        model = ResearchArtifact
        fields = ["q", "category", "status", "codebase", "tag"]

    def search_filter(self, queryset, name, value):
        return queryset.filter(
            models.Q(title__icontains=value)
            | models.Q(category__icontains=value)
            | models.Q(codebase__icontains=value)
            | models.Q(tags__name__icontains=value)
            | models.Q(description__icontains=value)
        ).distinct()
