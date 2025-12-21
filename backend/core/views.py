from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from .models import (
    Project,
    Asset,
    TaskType,
    TaskDefinition,
    Task,
    Annotation,
    FrontendPlugin,
    EventLog,
    Assignment,
)
from .serializers import (
    ProjectSerializer,
    AssetSerializer,
    TaskTypeSerializer,
    TaskDefinitionSerializer,
    TaskSerializer,
    AnnotationSerializer,
    FrontendPluginSerializer,
    AssignmentSerializer,
)
from .permissions import HasWriteToken


def log_event(event_type: str, actor: str = "", payload=None):
    EventLog.objects.create(
        event_type=event_type, actor=actor or "", payload=payload or {}
    )


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by("id")
    serializer_class = ProjectSerializer
    permission_classes = [HasWriteToken]


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.select_related("project").all().order_by("id")
    serializer_class = AssetSerializer
    permission_classes = [HasWriteToken]


class TaskTypeViewSet(viewsets.ModelViewSet):
    queryset = TaskType.objects.all().order_by("id")
    serializer_class = TaskTypeSerializer
    permission_classes = [HasWriteToken]


class TaskDefinitionViewSet(viewsets.ModelViewSet):
    queryset = TaskDefinition.objects.select_related("task_type").all().order_by("id")
    serializer_class = TaskDefinitionSerializer
    permission_classes = [HasWriteToken]


class TaskViewSet(viewsets.ModelViewSet):
    queryset = (
        Task.objects.select_related(
            "project", "asset", "task_definition", "task_definition__task_type"
        )
        .all()
        .order_by("id")
    )
    serializer_class = TaskSerializer
    permission_classes = [HasWriteToken]

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def bundle(self, request, pk=None):
        """Return everything the frontend needs in one call."""
        task: Task = self.get_object()
        td = task.task_definition
        tt = td.task_type
        plugin = getattr(tt, "plugin", None)
        plugin_manifest = plugin.manifest if plugin and plugin.is_active else None
        return Response(
            {
                "task": TaskSerializer(task).data,
                "asset": AssetSerializer(task.asset).data,
                "task_type": TaskTypeSerializer(tt).data,
                "task_definition": TaskDefinitionSerializer(td).data,
                "plugin": plugin_manifest,
            }
        )


class AnnotationViewSet(viewsets.ModelViewSet):
    queryset = Annotation.objects.select_related("task").all().order_by("id")
    serializer_class = AnnotationSerializer
    permission_classes = [HasWriteToken]

    def create(self, request, *args, **kwargs):
        self._duplicate_annotation = None
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        annotation = self.perform_create(serializer)
        duplicate = getattr(self, "_duplicate_annotation", None)
        instance = duplicate or annotation
        output = self.get_serializer(instance)
        status_code = status.HTTP_200_OK if duplicate else status.HTTP_201_CREATED
        headers = {}
        if not duplicate:
            headers = self.get_success_headers(output.data)
        return Response(output.data, status=status_code, headers=headers)

    def perform_create(self, serializer):
        data = serializer.validated_data
        submission_id = data.get("submission_id", "")
        task = data["task"]
        assignment = data.get("assignment")
        actor = data.get("actor", "")

        if not assignment and submission_id:
            assignment = Assignment.objects.filter(
                backend="mturk", assignment_id=submission_id
            ).first()
            if assignment:
                data["assignment"] = assignment

        if submission_id:
            existing = Annotation.objects.filter(
                task=task, submission_id=submission_id
            ).first()
            if existing:
                self._duplicate_annotation = existing
                return existing

        with transaction.atomic():
            obj = serializer.save()
            if assignment:
                dirty = []
                if assignment.ingested_at is None:
                    assignment.ingested_at = obj.created_at
                    dirty.append("ingested_at")
                if assignment.status != "submitted":
                    assignment.status = "submitted"
                    dirty.append("status")
                payload = assignment.payload or {}
                new_payload = dict(payload)
                new_payload["latest_annotation_submission"] = obj.raw_payload
                if new_payload != payload:
                    assignment.payload = new_payload
                    dirty.append("payload")
                if dirty:
                    assignment.updated_at = timezone.now()
                    assignment.save(update_fields=dirty + ["updated_at"])
        log_event(
            "ANNOTATION_CREATED",
            actor=actor,
            payload={
                "task_id": obj.task_id,
                "annotation_id": obj.id,
                "submission_id": obj.submission_id,
                "assignment_id": assignment.id if assignment else None,
            },
        )
        return obj


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related("task").all().order_by("id")
    serializer_class = AssignmentSerializer
    permission_classes = [HasWriteToken]


class PluginViewSet(viewsets.ModelViewSet):
    queryset = FrontendPlugin.objects.select_related("task_type").all().order_by("id")
    serializer_class = FrontendPluginSerializer
    permission_classes = [HasWriteToken]
