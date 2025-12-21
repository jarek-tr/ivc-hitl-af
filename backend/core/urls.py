from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet,
    TaskTypeViewSet,
    TaskDefinitionViewSet,
    AssetViewSet,
    TaskViewSet,
    AnnotationViewSet,
    PluginViewSet,
    AssignmentViewSet,
)

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"task-types", TaskTypeViewSet, basename="tasktype")
router.register(r"task-definitions", TaskDefinitionViewSet, basename="taskdefinition")
router.register(r"assets", AssetViewSet, basename="asset")
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"annotations", AnnotationViewSet, basename="annotation")
router.register(r"assignments", AssignmentViewSet, basename="assignment")
router.register(r"plugins", PluginViewSet, basename="plugin")

urlpatterns = [
    path("", include(router.urls)),
    path("tasks/<int:task_id>/annotate/", include("core.ui_urls")),
]
