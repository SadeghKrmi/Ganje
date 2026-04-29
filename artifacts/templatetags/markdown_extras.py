import markdown2
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="render_markdown")
def render_markdown(value):
    """Render markdown text to safe HTML."""
    if not value:
        return ""
    html = markdown2.markdown(
        value,
        extras=[
            "fenced-code-blocks",
            "tables",
            "code-friendly",
            "break-on-newline",
            "strike",
            "task_list",
            "header-ids",
        ],
    )
    return mark_safe(html)


@register.filter(name="status_badge_class")
def status_badge_class(status):
    mapping = {
        "active": "badge-active",
        "draft": "badge-draft",
        "archived": "badge-archived",
    }
    return mapping.get(status, "bg-secondary")
