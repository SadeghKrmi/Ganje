from django import forms
from django.contrib.auth import get_user_model

from .models import ResearchArtifact, ResearchVersion, Tag


class TagWidget(forms.TextInput):
    """Comma-separated tag input."""


class UserMultiSelectWidget(forms.SelectMultiple):
    """SelectMultiple that adds data-name/data-email/data-initial attributes
    to each <option>, so a JS picker can render rich chips/dropdown rows.

    Use ``set_user_data(mapping)`` from the form's ``__init__`` to provide
    the lookup dict (keyed by str pk) — this avoids N+1 queries per option.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user_data = {}

    def set_user_data(self, mapping):
        # mapping: { "<pk>": {"name": ..., "email": ..., "initial": ...} }
        self._user_data = {str(k): v for k, v in mapping.items()}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        info = self._user_data.get(str(option["value"]))
        if info:
            option["attrs"]["data-name"]    = info["name"]
            option["attrs"]["data-email"]   = info["email"]
            option["attrs"]["data-initial"] = info["initial"]
        return option


class ArtifactForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "e.g. registry, handler, context (comma separated)",
            "class": "form-control",
            "id": "tags-input",
        }),
        label="Tags",
        help_text="Comma-separated list of tags",
    )

    visibility = forms.ChoiceField(
        choices=ResearchArtifact.VISIBILITY_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "visibility-radio"}),
        initial=ResearchArtifact.VIS_PRIVATE,
        label="Visibility",
    )

    shared_with = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.none(),  # set in __init__
        required=False,
        widget=UserMultiSelectWidget(attrs={
            "class": "user-picker-select",
            "id": "id_shared_with",
        }),
        label="Share with users",
        help_text="Search by name or email below to add users one at a time.",
    )

    class Meta:
        model = ResearchArtifact
        fields = ["title", "description", "category", "codebase", "status", "visibility"]
        widgets = {
            "title":       forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. How context handlers are registered in ContextRegistry"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Brief overview of what you are studying…"}),
            "category":    forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Architecture, Performance, Security"}),
            "codebase":    forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. my-service, github.com/org/repo"}),
            "status":      forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user

        # Limit shareable users to active accounts excluding the owner themselves
        UserModel = get_user_model()
        users_qs = UserModel.objects.filter(is_active=True).order_by("first_name", "last_name", "email")
        if current_user is not None:
            users_qs = users_qs.exclude(pk=current_user.pk)
        self.fields["shared_with"].queryset = users_qs
        self.fields["shared_with"].label_from_instance = (
            lambda u: f"{u.get_full_name() or u.username} <{u.email}>" if u.email else (u.get_full_name() or u.username)
        )

        # Pre-compute user metadata so the widget can decorate <option>s without N+1 queries
        user_meta = {}
        for u in users_qs.only("id", "first_name", "last_name", "email", "username"):
            full = (u.get_full_name() or "").strip()
            display = full or u.username or u.email
            user_meta[u.pk] = {
                "name":    display,
                "email":   u.email or "",
                "initial": (display[:1] or "?").upper(),
            }
        widget = self.fields["shared_with"].widget
        if hasattr(widget, "set_user_data"):
            widget.set_user_data(user_meta)

        if self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(
                self.instance.tags.values_list("name", flat=True)
            )
            self.fields["shared_with"].initial = self.instance.shared_with.all()

    def clean(self):
        data = super().clean()
        visibility = data.get("visibility")
        shared = data.get("shared_with")
        if visibility == ResearchArtifact.VIS_SHARED and not shared:
            self.add_error(
                "shared_with",
                "Pick at least one user to share with, or change visibility to Public/Private.",
            )
        return data

    def save(self, commit=True):
        artifact = super().save(commit=commit)
        if commit:
            self._save_tags(artifact)
            self._save_shared_with(artifact)
        return artifact

    def _save_tags(self, artifact):
        raw = self.cleaned_data.get("tags_input", "")
        names = [t.strip() for t in raw.split(",") if t.strip()]
        tag_objs = []
        for name in names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tag_objs.append(tag)
        artifact.tags.set(tag_objs)

    def _save_shared_with(self, artifact):
        if artifact.visibility == ResearchArtifact.VIS_SHARED:
            artifact.shared_with.set(self.cleaned_data.get("shared_with") or [])
        else:
            # not shared → drop the list to keep data tidy
            artifact.shared_with.clear()


class VersionForm(forms.ModelForm):
    class Meta:
        model = ResearchVersion
        fields = ["prompt", "analysis", "model_used", "codebase_ref", "notes"]
        widgets = {
            "prompt": forms.Textarea(attrs={
                "class": "form-control font-monospace",
                "rows": 6,
                "placeholder": "Paste the exact prompt you sent to the AI model…",
            }),
            "analysis": forms.Textarea(attrs={
                "class": "form-control font-monospace",
                "rows": 18,
                "placeholder": "Paste the AI analysis here. Markdown is supported.",
            }),
            "model_used": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. GPT-4o, Claude-3.5-Sonnet",
            }),
            "codebase_ref": forms.TextInput(attrs={
                "class": "form-control font-monospace",
                "placeholder": "e.g. abc1234 (git commit hash or branch name)",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Any personal notes or context about this version…",
            }),
        }
        labels = {
            "codebase_ref": "Codebase Reference",
        }
