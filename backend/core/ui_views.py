import json
import mimetypes
from pathlib import Path
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.html import escape
from .models import Task

FRONTENDS_DIR = Path(__file__).resolve().parent.parent.parent / "frontends"

def annotate_task_shell(request, task_id: int):
    """Minimal HTML shell that loads a registered frontend plugin bundle."""
    task = get_object_or_404(Task.objects.select_related("task_definition__task_type"), pk=task_id)
    tt = task.task_definition.task_type
    plugin = getattr(tt, "plugin", None)
    if not plugin or not plugin.is_active:
        return HttpResponse(
            f"<h3>No active plugin registered for task type: {escape(tt.slug)}</h3>",
            status=404,
        )

    manifest = plugin.manifest or {}
    css_files = manifest.get("css", [])
    js_files = manifest.get("js", [])

    # Serve plugin assets through Django to keep deployment simple.
    css_tags = "\n".join([f'<link rel="stylesheet" href="plugin/{escape(p)}">' for p in css_files])
    js_tags = "\n".join([f'<script type="module" src="plugin/{escape(p)}"></script>' for p in js_files])

    boot = {
        "taskId": task.id,
        "apiBase": "/api",
    }

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Annotate #{task.id} — {escape(tt.slug)}</title>
{css_tags}
</head>
<body>
<div id="root"></div>
<script>window.__IVC_BOOT__ = {json.dumps(boot)};</script>
{js_tags}
</body>
</html>
"""
    return HttpResponse(html)

def plugin_asset(request, task_id: int, asset_path: str):
    task = get_object_or_404(Task.objects.select_related("task_definition__task_type"), pk=task_id)
    tt = task.task_definition.task_type
    plugin = getattr(tt, "plugin", None)
    if not plugin or not plugin.is_active:
        raise Http404("No active plugin")

    # Assets are addressed relative to a plugin root folder declared in manifest.
    manifest = plugin.manifest or {}
    plugin_root = manifest.get("root", "")
    safe_root = (FRONTENDS_DIR / plugin_root).resolve()
    safe_file = (safe_root / asset_path).resolve()

    if not str(safe_file).startswith(str(safe_root)):
        raise Http404("Invalid path")
    if not safe_file.exists() or not safe_file.is_file():
        raise Http404("Missing asset")

    mime, _ = mimetypes.guess_type(str(safe_file))
    mime = mime or "application/octet-stream"
    return HttpResponse(safe_file.read_bytes(), content_type=mime)

def mturk_annotate_task(request, task_id: int):
    """MTurk-compatible wrapper.
    MTurk appends query params like assignmentId, hitId, workerId.
    We render the same plugin shell but provide `mturk` metadata so the plugin (or wrapper)
    can submit back to MTurk.
    """
    task = get_object_or_404(Task.objects.select_related("task_definition__task_type"), pk=task_id)
    assignment_id = request.GET.get("assignmentId", "")
    hit_id = request.GET.get("hitId", "")
    worker_id = request.GET.get("workerId", "")
    sandbox = request.GET.get("sandbox", "1") == "1"

    # MTurk uses a fixed submit URL pattern.
    submit_host = "https://www.mturk.com" if not sandbox else "https://workersandbox.mturk.com"
    submit_url = f"{submit_host}/mturk/externalSubmit"

    tt = task.task_definition.task_type
    plugin = getattr(tt, "plugin", None)
    if not plugin or not plugin.is_active:
        return HttpResponse(
            f"<h3>No active plugin registered for task type: {escape(tt.slug)}</h3>",
            status=404,
        )

    manifest = plugin.manifest or {}
    css_files = manifest.get("css", [])
    js_files = manifest.get("js", [])

    css_tags = "\n".join([f'<link rel="stylesheet" href="plugin/{escape(p)}">' for p in css_files])
    js_tags = "\n".join([f'<script type="module" src="plugin/{escape(p)}"></script>' for p in js_files])

    boot = {
        "taskId": task.id,
        "apiBase": "/api",
        "mturk": {
            "assignmentId": assignment_id,
            "hitId": hit_id,
            "workerId": worker_id,
            "sandbox": sandbox,
            "submitUrl": submit_url,
        },
    }

    html = f"""<!doctype html>
    <html>
    <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>MTurk Annotate #{task.id} — {escape(tt.slug)}</title>
    {css_tags}
    </head>
    <body>
    <div id="root"></div>
    <script>window.__IVC_BOOT__ = {json.dumps(boot)};</script>
    {js_tags}
    </body>
    </html>
    """
    return HttpResponse(html)
