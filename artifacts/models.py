import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Tag(models.Model):
    name = models.CharField(max_length=80, unique=True)
    color = models.CharField(max_length=7, default="#6c757d", help_text="Hex color code")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ResearchArtifactQuerySet(models.QuerySet):
    """Custom queryset with permission-aware filtering."""

    def visible_to(self, user):
        """Return only artifacts the given user is allowed to read."""
        if not user or not user.is_authenticated:
            return self.filter(visibility=ResearchArtifact.VIS_PUBLIC)
        if user.is_superuser:
            return self
        return self.filter(
            Q(owner=user)
            | Q(visibility=ResearchArtifact.VIS_PUBLIC)
            | Q(visibility=ResearchArtifact.VIS_SHARED, shared_with=user)
        ).distinct()

    def owned_by(self, user):
        return self.filter(owner=user)

    def shared_with_user(self, user):
        """Artifacts NOT owned by user but readable by them via sharing/public."""
        if not user or not user.is_authenticated:
            return self.none()
        return self.exclude(owner=user).filter(
            Q(visibility=ResearchArtifact.VIS_PUBLIC)
            | Q(visibility=ResearchArtifact.VIS_SHARED, shared_with=user)
        ).distinct()


class ResearchArtifact(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_DRAFT = "draft"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_DRAFT, "Draft"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    VIS_PRIVATE = "private"
    VIS_SHARED = "shared"
    VIS_PUBLIC = "public"
    VISIBILITY_CHOICES = [
        (VIS_PRIVATE, "Private (only me)"),
        (VIS_SHARED, "Shared (selected users)"),
        (VIS_PUBLIC, "Public (everyone)"),
    ]

    id = models.AutoField(primary_key=True)
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, help_text="Brief summary of what is being studied")
    category = models.CharField(max_length=120, blank=True, help_text="e.g. Architecture, Performance, Security")
    codebase = models.CharField(max_length=200, blank=True, help_text="Name or path of the codebase being analysed")
    tags = models.ManyToManyField(Tag, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    # ── Ownership & sharing ──────────────────────────────────────
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="artifacts",
        null=True, blank=True,  # nullable for legacy rows; new rows always set
    )
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VIS_PRIVATE,
    )
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="shared_artifacts",
        help_text="Users who can view this artifact when visibility is 'Shared'.",
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ResearchArtifactQuerySet.as_manager()

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"#{self.pk:07d} – {self.title}"

    @property
    def artifact_id(self):
        return f"#{self.pk:07d}"

    @property
    def latest_version(self):
        versions = list(self.versions.all())
        if not versions:
            return None
        return max(versions, key=lambda v: v.version_number)

    @property
    def version_count(self):
        return len(self.versions.all())

    # ── Permission helpers ──────────────────────────────────────
    def can_view(self, user):
        if not user or not user.is_authenticated:
            return self.visibility == self.VIS_PUBLIC
        if user.is_superuser or self.owner_id == user.pk:
            return True
        if self.visibility == self.VIS_PUBLIC:
            return True
        if self.visibility == self.VIS_SHARED:
            return self.shared_with.filter(pk=user.pk).exists()
        return False

    def can_edit(self, user):
        return bool(user and user.is_authenticated and (user.is_superuser or self.owner_id == user.pk))

    @property
    def visibility_icon(self):
        return {
            self.VIS_PRIVATE: "bi-lock",
            self.VIS_SHARED: "bi-people",
            self.VIS_PUBLIC: "bi-globe",
        }.get(self.visibility, "bi-question")


class ResearchVersion(models.Model):
    artifact = models.ForeignKey(ResearchArtifact, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    prompt = models.TextField(help_text="The prompt sent to the AI model")
    analysis = models.TextField(help_text="The AI-generated analysis (Markdown supported)")
    model_used = models.CharField(max_length=100, blank=True, help_text="e.g. GPT-4o, Claude-3.5-Sonnet")
    codebase_ref = models.CharField(
        max_length=200,
        blank=True,
        help_text="Git commit hash, branch, or version tag at time of analysis",
    )
    notes = models.TextField(blank=True, help_text="Any personal notes about this version")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-version_number"]
        unique_together = [("artifact", "version_number")]

    def __str__(self):
        return f"{self.artifact.artifact_id} v{self.version_number}"

    def save(self, *args, **kwargs):
        if not self.pk:
            last = (
                ResearchVersion.objects.filter(artifact=self.artifact)
                .order_by("-version_number")
                .first()
            )
            self.version_number = (last.version_number + 1) if last else 1
        super().save(*args, **kwargs)
        self.artifact.status = ResearchArtifact.STATUS_ACTIVE
        self.artifact.save(update_fields=["status", "updated_at"])
