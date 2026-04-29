import re

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from .models import ResearchArtifact, ResearchVersion, Tag
from .forms import ArtifactForm, VersionForm
from .filters import ArtifactFilter


# ── Permission helpers ─────────────────────────────────────────
def _get_artifact_for_view(request, pk):
    """Fetch an artifact and 404 if the current user can't view it."""
    artifact = get_object_or_404(
        ResearchArtifact.objects.prefetch_related("tags", "versions", "shared_with"),
        pk=pk,
    )
    if not artifact.can_view(request.user):
        raise PermissionDenied("You don't have access to this artifact.")
    return artifact


def _get_artifact_for_edit(request, pk):
    """Fetch an artifact and 403 if the current user can't modify it."""
    artifact = get_object_or_404(ResearchArtifact, pk=pk)
    if not artifact.can_edit(request.user):
        raise PermissionDenied("Only the owner or a superuser can modify this artifact.")
    return artifact


def _slugify_for_filename(value: str, fallback: str = "version") -> str:
    """Make a string safe for use in a filename (cross-OS)."""
    value = (value or "").strip()
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    value = re.sub(r"[\s_-]+", "-", value).strip("-").lower()
    return value[:80] or fallback


def build_magic_prompt(artifact: ResearchArtifact) -> str:
    """
    Build a ready-to-paste AI prompt that uses the artifact's own metadata
    and (optionally) its latest version's analysis as context.

    The AI is instructed to return output in EXACTLY the section format the
    Add-Version form expects, so the user can copy-paste the result back.
    """
    latest = artifact.latest_version
    is_first = latest is None

    tags_str = ", ".join(artifact.tags.values_list("name", flat=True)) or "—"
    codebase = artifact.codebase or "<not specified>"
    last_ref = (latest.codebase_ref if latest else "") or "<unknown>"

    header = (
        f"You are helping me document a code study for a research database called \"Ganje\".\n"
        f"Below is the metadata for the study. "
        + ("Analyse it carefully and produce findings in EXACTLY the format described.\n"
           if is_first else
           "Re-analyse it against the CURRENT state of the codebase and produce findings\n"
           "in EXACTLY the format described.\n")
    )

    metadata_block = (
        "## Study\n"
        f"**Question / title:** {artifact.title}\n\n"
        f"**Description:** {artifact.description or '(none provided)'}\n\n"
        f"**Codebase:** `{codebase}`\n\n"
        f"**Category:** {artifact.category or '(none)'}\n\n"
        f"**Keywords / tags:** {tags_str}\n"
    )

    if not is_first:
        prev_block = (
            "\n## Previous analysis (version "
            f"v{latest.version_number}{', ref `' + last_ref + '`' if last_ref != '<unknown>' else ''})\n\n"
            "<details>\n<summary>Click to expand</summary>\n\n"
            f"{latest.analysis.strip()}\n\n"
            "</details>\n"
        )
        new_version_focus = (
            "\nFocus on **what has changed** since the previous version. If nothing has\n"
            "materially changed, say so clearly in the analysis.\n"
        )
    else:
        prev_block = ""
        new_version_focus = ""

    output_format = (
        "\n## Output format\n"
        "Produce your response as plain Markdown using these EXACT delimiter sections,\n"
        "in this order. Do not add any extra prose before or after.\n\n"
        "=== CODEBASE_REF ===\n"
        "<the git commit hash, branch, or version tag for THIS analysis>\n\n"
        "=== MODEL ===\n"
        "<the AI model name you are running as, e.g. GPT-4o, Claude-3.5-Sonnet, Gemini-1.5-Pro>\n\n"
        "=== ANALYSIS ===\n"
        f"# {artifact.title}\n\n"
        + ("## What changed since last version\n"
           "- bullet points highlighting differences from the previous analysis\n"
           "- be explicit when something was removed, renamed, or restructured\n\n"
           if not is_first else "")
        + "## Overview\n"
          "<1-2 paragraph high-level summary>\n\n"
          "## Key findings\n"
          "- bullet points\n"
          "- with concrete code references like `path/to/file.py:42`\n"
          "- one finding per bullet\n\n"
          "## Detailed walkthrough\n"
          "<step-by-step explanation, with code snippets in fenced blocks>\n\n"
          "## Caveats / open questions\n"
          "<anything you are unsure about, assumptions you made, or things worth verifying>\n\n"
        "=== NOTES ===\n"
        "<your personal observations: was the change risky? does it open new questions?\n"
        " leave blank if none>\n"
    )

    return header + "\n" + metadata_block + prev_block + new_version_focus + output_format


def _build_markdown_export(artifact: ResearchArtifact, version: ResearchVersion) -> str:
    """Render a single ResearchVersion as a portable Markdown document with YAML frontmatter."""
    tags = ", ".join(artifact.tags.values_list("name", flat=True))
    fm_lines = [
        "---",
        f'artifact_id: "{artifact.artifact_id}"',
        f"uid: {artifact.uid}",
        f'title: "{artifact.title.replace(chr(34), chr(39))}"',
        f"version: {version.version_number}",
        f"status: {artifact.status}",
        f'category: "{artifact.category}"' if artifact.category else None,
        f'codebase: "{artifact.codebase}"' if artifact.codebase else None,
        f'codebase_ref: "{version.codebase_ref}"' if version.codebase_ref else None,
        f'model_used: "{version.model_used}"' if version.model_used else None,
        f'tags: [{tags}]' if tags else None,
        f"created_at: {version.created_at.isoformat()}",
        f"exported_at: {__import__('django.utils.timezone', fromlist=['now']).now().isoformat()}",
        "---",
        "",
    ]
    fm = "\n".join(line for line in fm_lines if line is not None)

    parts = [
        fm,
        f"# {artifact.title}",
        "",
        f"**Artifact:** `{artifact.artifact_id}` &nbsp;·&nbsp; **Version:** `v{version.version_number}`",
        "",
    ]
    if artifact.description:
        parts.extend([f"> {artifact.description}", ""])

    parts.extend([
        "## Prompt",
        "",
        "```text",
        version.prompt.rstrip(),
        "```",
        "",
        "## Analysis",
        "",
        version.analysis.rstrip(),
        "",
    ])
    if version.notes:
        parts.extend(["## Notes", "", version.notes.rstrip(), ""])

    return "\n".join(parts)


def artifact_list(request):
    user = request.user
    base_qs = ResearchArtifact.objects.prefetch_related("tags", "versions", "shared_with", "owner")
    visible_qs = base_qs.visible_to(user)

    # Scope filter (mine / shared / all)
    scope = request.GET.get("scope", "all")
    if scope == "mine":
        qs = visible_qs.filter(owner=user)
    elif scope == "shared":
        qs = visible_qs.shared_with_user(user)
    else:
        qs = visible_qs
        scope = "all"

    f = ArtifactFilter(request.GET, queryset=qs)

    sort = request.GET.get("sort", "-updated_at")
    allowed_sorts = {
        "title": "title",
        "-title": "-title",
        "created_at": "created_at",
        "-created_at": "-created_at",
        "updated_at": "updated_at",
        "-updated_at": "-updated_at",
        "id": "id",
        "-id": "-id",
    }
    order_by = allowed_sorts.get(sort, "-updated_at")
    filtered_qs = f.qs.order_by(order_by)

    paginator = Paginator(filtered_qs, 20)
    page = request.GET.get("page", 1)
    page_obj = paginator.get_page(page)

    # Counts for the scope tabs (always against the user's full visibility set)
    scope_counts = {
        "all":    visible_qs.count(),
        "mine":   visible_qs.filter(owner=user).count(),
        "shared": visible_qs.shared_with_user(user).count(),
    }

    return render(request, "artifacts/list.html", {
        "filter": f,
        "page_obj": page_obj,
        "current_sort": sort,
        "current_scope": scope,
        "scope_counts": scope_counts,
    })


def artifact_detail(request, pk):
    artifact = _get_artifact_for_view(request, pk)
    versions = artifact.versions.order_by("-version_number")
    latest = versions.first()
    return render(request, "artifacts/detail.html", {
        "artifact": artifact,
        "versions": versions,
        "latest": latest,
        "version_form": VersionForm(),
        "can_edit": artifact.can_edit(request.user),
        "magic_prompt": build_magic_prompt(artifact),
    })


def artifact_create(request):
    if request.method == "POST":
        form = ArtifactForm(request.POST, current_user=request.user)
        if form.is_valid():
            artifact = form.save(commit=False)
            artifact.owner = request.user
            artifact.save()
            form._save_tags(artifact)
            form._save_shared_with(artifact)
            messages.success(request, f"Artifact {artifact.artifact_id} created successfully.")
            return redirect("artifact_detail", pk=artifact.pk)
    else:
        form = ArtifactForm(current_user=request.user)
    return render(request, "artifacts/create.html", {"form": form, "action": "Create"})


def artifact_edit(request, pk):
    artifact = _get_artifact_for_edit(request, pk)
    if request.method == "POST":
        form = ArtifactForm(request.POST, instance=artifact, current_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Artifact updated.")
            return redirect("artifact_detail", pk=artifact.pk)
    else:
        form = ArtifactForm(instance=artifact, current_user=request.user)
    return render(request, "artifacts/create.html", {
        "form": form,
        "artifact": artifact,
        "action": "Edit",
    })


def artifact_delete(request, pk):
    artifact = _get_artifact_for_edit(request, pk)
    if request.method == "POST":
        artifact.delete()
        messages.success(request, "Artifact deleted.")
        return redirect("artifact_list")
    return render(request, "artifacts/confirm_delete.html", {"artifact": artifact})


def version_add(request, pk):
    artifact = _get_artifact_for_edit(request, pk)
    if request.method == "POST":
        form = VersionForm(request.POST)
        if form.is_valid():
            version = form.save(commit=False)
            version.artifact = artifact
            version.save()
            messages.success(
                request,
                f"Version {version.version_number} added to {artifact.artifact_id}.",
            )
            return redirect("version_detail", pk=artifact.pk, version_number=version.version_number)
    else:
        form = VersionForm()
    return render(request, "artifacts/version_form.html", {
        "artifact": artifact,
        "form": form,
        "action": "Add New Version",
    })


def version_detail(request, pk, version_number):
    artifact = _get_artifact_for_view(request, pk)
    version = get_object_or_404(ResearchVersion, artifact=artifact, version_number=version_number)
    all_versions = artifact.versions.order_by("-version_number")
    return render(request, "artifacts/version_detail.html", {
        "artifact": artifact,
        "version": version,
        "all_versions": all_versions,
        "can_edit": artifact.can_edit(request.user),
    })


def version_edit(request, pk, version_number):
    artifact = _get_artifact_for_edit(request, pk)
    version = get_object_or_404(ResearchVersion, artifact=artifact, version_number=version_number)
    if request.method == "POST":
        form = VersionForm(request.POST, instance=version)
        if form.is_valid():
            form.save()
            messages.success(request, "Version updated.")
            return redirect("version_detail", pk=artifact.pk, version_number=version.version_number)
    else:
        form = VersionForm(instance=version)
    return render(request, "artifacts/version_form.html", {
        "artifact": artifact,
        "version": version,
        "form": form,
        "action": "Edit Version",
    })


def version_export(request, pk, version_number):
    """Download a version as a Markdown file (read access required)."""
    artifact = _get_artifact_for_view(request, pk)
    version = get_object_or_404(
        ResearchVersion, artifact=artifact, version_number=version_number
    )

    md = _build_markdown_export(artifact, version)
    slug = _slugify_for_filename(artifact.title)
    filename = f"ganje-{artifact.pk:07d}-{slug}-v{version.version_number}.md"

    response = HttpResponse(md, content_type="text/markdown; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Length"] = len(md.encode("utf-8"))
    return response


def stats_view(request):
    user = request.user
    visible = ResearchArtifact.objects.visible_to(user)
    visible_versions = ResearchVersion.objects.filter(artifact__in=visible)

    by_status = dict(visible.values_list("status").annotate(c=Count("id")))
    by_category = list(
        visible.exclude(category="")
        .values("category")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    top_tags = list(
        Tag.objects.filter(researchartifact__in=visible)
        .annotate(count=Count("researchartifact"))
        .order_by("-count")[:15]
        .values("name", "color", "count")
    )
    recent_versions = visible_versions.select_related("artifact").order_by("-created_at")[:10]

    by_visibility = dict(visible.values_list("visibility").annotate(c=Count("id")))

    return render(request, "artifacts/stats.html", {
        "by_status": by_status,
        "by_category": by_category,
        "top_tags": top_tags,
        "recent_versions": recent_versions,
        "by_visibility": by_visibility,
        "total_artifacts": visible.count(),
        "total_versions": visible_versions.count(),
        "owned_count": visible.filter(owner=user).count(),
    })
