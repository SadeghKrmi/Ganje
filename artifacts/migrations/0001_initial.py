import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, unique=True)),
                ("color", models.CharField(default="#6c757d", help_text="Hex color code", max_length=7)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ResearchArtifact",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("uid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField(blank=True, help_text="Brief summary of what is being studied")),
                ("category", models.CharField(blank=True, help_text="e.g. Architecture, Performance, Security", max_length=120)),
                ("codebase", models.CharField(blank=True, help_text="Name or path of the codebase being analysed", max_length=200)),
                ("status", models.CharField(
                    choices=[("active", "Active"), ("draft", "Draft"), ("archived", "Archived")],
                    default="draft",
                    max_length=20,
                )),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tags", models.ManyToManyField(blank=True, to="artifacts.tag")),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="ResearchVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version_number", models.PositiveIntegerField()),
                ("prompt", models.TextField(help_text="The prompt sent to the AI model")),
                ("analysis", models.TextField(help_text="The AI-generated analysis (Markdown supported)")),
                ("model_used", models.CharField(blank=True, help_text="e.g. GPT-4o, Claude-3.5-Sonnet", max_length=100)),
                ("codebase_ref", models.CharField(blank=True, help_text="Git commit hash, branch, or version tag at time of analysis", max_length=200)),
                ("notes", models.TextField(blank=True, help_text="Any personal notes about this version")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("artifact", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versions", to="artifacts.researchartifact")),
            ],
            options={"ordering": ["-version_number"]},
        ),
        migrations.AddConstraint(
            model_name="researchversion",
            constraint=models.UniqueConstraint(fields=["artifact", "version_number"], name="unique_artifact_version"),
        ),
    ]
