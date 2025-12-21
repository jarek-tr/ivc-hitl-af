from django.urls import path
from .ui_views import annotate_task_shell, plugin_asset, mturk_annotate_task

urlpatterns = [
    path("mturk/", mturk_annotate_task, name="mturk-annotate"),
    path("", annotate_task_shell, name="annotate-task"),
    path("plugin/<path:asset_path>", plugin_asset, name="plugin-asset"),
]
