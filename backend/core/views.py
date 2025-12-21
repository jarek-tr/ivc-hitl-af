from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
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

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def stats(self, request, pk=None):
        """Return annotation progress statistics for this project."""
        from django.db.models import Count, Q

        project = self.get_object()
        tasks = Task.objects.filter(project=project)

        task_stats = tasks.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            in_progress=Count('id', filter=Q(status='in_progress')),
            complete=Count('id', filter=Q(status='complete')),
            failed=Count('id', filter=Q(status='failed')),
        )

        annotation_count = Annotation.objects.filter(task__project=project).count()
        unique_actors = Annotation.objects.filter(
            task__project=project
        ).exclude(actor='').values('actor').distinct().count()

        assignment_stats = Assignment.objects.filter(task__project=project).aggregate(
            total=Count('id'),
            created=Count('id', filter=Q(status='created')),
            submitted=Count('id', filter=Q(status='submitted')),
            approved=Count('id', filter=Q(status='approved')),
            rejected=Count('id', filter=Q(status='rejected')),
            returned=Count('id', filter=Q(status='returned')),
            expired=Count('id', filter=Q(status='expired')),
        )

        return Response({
            'project_id': project.id,
            'project_slug': project.slug,
            'tasks': task_stats,
            'annotations': {
                'total': annotation_count,
                'unique_actors': unique_actors,
            },
            'assignments': assignment_stats,
        })

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def export(self, request, pk=None):
        """Export all annotations for this project in JSON format."""
        import json
        from django.http import HttpResponse

        project = self.get_object()
        format_type = request.query_params.get('format', 'json')

        if format_type not in ['json', 'jsonl']:
            return Response(
                {'error': 'Invalid format. Supported: json, jsonl'},
                status=status.HTTP_400_BAD_REQUEST
            )

        annotations = Annotation.objects.filter(
            task__project=project
        ).select_related('task', 'task__asset', 'assignment').order_by('task_id', 'created_at')

        export_data = []
        for ann in annotations:
            record = {
                'annotation_id': ann.id,
                'task_id': ann.task_id,
                'asset_id': ann.task.asset_id,
                'asset_s3_key': ann.task.asset.s3_key,
                'result': ann.result,
                'schema_version': ann.schema_version,
                'tool_version': ann.tool_version,
                'actor': ann.actor,
                'submission_id': ann.submission_id,
                'created_at': ann.created_at.isoformat(),
                'assignment_id': ann.assignment_id,
            }
            export_data.append(record)

        if format_type == 'json':
            response = HttpResponse(
                json.dumps(export_data, indent=2),
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="{project.slug}_annotations.json"'
        else:  # jsonl
            lines = '\n'.join([json.dumps(record) for record in export_data])
            response = HttpResponse(lines, content_type='application/x-ndjson')
            response['Content-Disposition'] = f'attachment; filename="{project.slug}_annotations.jsonl"'

        return response


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

    @action(detail=True, methods=["post"], permission_classes=[HasWriteToken])
    def duplicate(self, request, pk=None):
        """Create a duplicate task with a new asset."""
        source_task = self.get_object()
        asset_id = request.data.get('asset_id')

        if not asset_id:
            return Response(
                {'error': 'asset_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_asset = Asset.objects.get(id=asset_id)
        except Asset.DoesNotExist:
            return Response(
                {'error': f'Asset {asset_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create duplicate task
        new_task = Task.objects.create(
            project=source_task.project,
            asset=new_asset,
            task_definition=source_task.task_definition,
            status='pending',
            priority=source_task.priority,
            assigned_to=request.data.get('assigned_to', ''),
            payload=source_task.payload.copy() if source_task.payload else {},
        )

        return Response(
            TaskSerializer(new_task).data,
            status=status.HTTP_201_CREATED
        )


class AnnotationViewSet(viewsets.ModelViewSet):
    queryset = Annotation.objects.select_related("task").all().order_by("id")
    serializer_class = AnnotationSerializer
    permission_classes = [HasWriteToken]

    @method_decorator(ratelimit(key='ip', rate='100/h', method='POST'))
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
