from django.conf import settings
from django.db import migrations, models


def backfill_owner(apps, schema_editor):
    """Assign existing artifacts (if any) to the first available superuser."""
    ResearchArtifact = apps.get_model("artifacts", "ResearchArtifact")
    User = apps.get_model(settings.AUTH_USER_MODEL.split(".")[0], settings.AUTH_USER_MODEL.split(".")[1])

    if not ResearchArtifact.objects.filter(owner__isnull=True).exists():
        return

    fallback_user = (
        User.objects.filter(is_superuser=True).order_by("pk").first()
        or User.objects.order_by("pk").first()
    )
    if fallback_user is None:
        # No users exist yet – leave owner null; new artifacts will set it.
        return

    ResearchArtifact.objects.filter(owner__isnull=True).update(owner=fallback_user)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("artifacts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="researchartifact",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="artifacts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="researchartifact",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("private", "Private (only me)"),
                    ("shared",  "Shared (selected users)"),
                    ("public",  "Public (everyone)"),
                ],
                default="private",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="researchartifact",
            name="shared_with",
            field=models.ManyToManyField(
                blank=True,
                help_text="Users who can view this artifact when visibility is 'Shared'.",
                related_name="shared_artifacts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_owner, noop_reverse),
    ]
