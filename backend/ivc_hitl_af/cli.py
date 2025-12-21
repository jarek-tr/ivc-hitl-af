"""
IVC HITL-AF command-line interface

Provides convenience commands for project initialization, plugin management,
and deployment operations.
"""
import os
import sys
import click
import django


def setup_django():
    """Initialize Django settings."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ivc_hitl_af.settings')
    django.setup()


@click.group()
@click.version_option(version='0.1.0')
def main():
    """IVC HITL-AF: Human-in-the-Loop Annotation Framework"""
    pass


@main.command()
@click.option('--name', prompt='Project name', help='Human-readable project name')
@click.option('--slug', prompt='Project slug', help='URL-safe project identifier')
def init_project(name, slug):
    """Initialize a new annotation project."""
    setup_django()
    from core.models import Project

    project, created = Project.objects.get_or_create(
        slug=slug,
        defaults={'name': name}
    )

    if created:
        click.echo(f"✓ Created project: {name} ({slug})")
    else:
        click.echo(f"! Project already exists: {name} ({slug})")

    click.echo(f"\nProject ID: {project.id}")
    click.echo(f"API URL: /api/projects/{project.id}/")


@main.command()
@click.option('--strict', is_flag=True, help='Exit with error if validation fails')
def validate_plugins(strict):
    """Validate all registered frontend plugins."""
    setup_django()
    from django.core.management import call_command

    try:
        args = ['validate_plugins']
        if strict:
            args.append('--strict')
        call_command(*args)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument('plugin_dir', type=click.Path(exists=True))
@click.option('--task-type', required=True, help='TaskType slug')
def register_plugin(plugin_dir, task_type):
    """Register a frontend plugin from a directory."""
    setup_django()
    from core.models import TaskType, FrontendPlugin
    from pathlib import Path
    import json

    manifest_path = Path(plugin_dir) / 'manifest.json'
    if not manifest_path.exists():
        click.echo(f"Error: No manifest.json found in {plugin_dir}", err=True)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    try:
        task_type_obj = TaskType.objects.get(slug=task_type)
    except TaskType.DoesNotExist:
        click.echo(f"Error: TaskType '{task_type}' not found", err=True)
        click.echo("Create it first with: python manage.py shell")
        sys.exit(1)

    plugin, created = FrontendPlugin.objects.update_or_create(
        task_type=task_type_obj,
        defaults={
            'name': manifest.get('name'),
            'version': manifest.get('version'),
            'manifest': manifest,
            'is_active': True,
        }
    )

    action = "Registered" if created else "Updated"
    click.echo(f"✓ {action} plugin: {plugin.name} v{plugin.version}")


@main.command()
@click.argument('project_slug')
@click.option('--format', type=click.Choice(['json', 'jsonl']), default='json')
@click.option('--output', type=click.Path(), help='Output file (default: stdout)')
def export_annotations(project_slug, format, output):
    """Export annotations for a project."""
    setup_django()
    from core.models import Project, Annotation
    import json

    try:
        project = Project.objects.get(slug=project_slug)
    except Project.DoesNotExist:
        click.echo(f"Error: Project '{project_slug}' not found", err=True)
        sys.exit(1)

    annotations = Annotation.objects.filter(
        task__project=project
    ).select_related('task', 'task__asset').order_by('task_id', 'created_at')

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
        }
        export_data.append(record)

    if format == 'json':
        content = json.dumps(export_data, indent=2)
    else:  # jsonl
        content = '\n'.join([json.dumps(record) for record in export_data])

    if output:
        with open(output, 'w') as f:
            f.write(content)
        click.echo(f"✓ Exported {len(export_data)} annotations to {output}")
    else:
        click.echo(content)


@main.command()
@click.option('--limit', default=25, help='Maximum number of HITs to sync')
def sync_mturk(limit):
    """Sync open MTurk HITs and ingest submitted assignments."""
    setup_django()
    from core.mturk import sync_open_hits, ingest_submitted_assignments

    click.echo("Syncing open MTurk HITs...")
    hit_result = sync_open_hits(limit=limit)
    click.echo(f"  Synced {hit_result.get('synced', 0)} HITs")

    click.echo("\nIngesting submitted assignments...")
    ingest_result = ingest_submitted_assignments(limit=limit)
    click.echo(f"  Ingested {ingest_result.get('ingested', 0)} assignments")


@main.command()
@click.option('--reset', is_flag=True, help='Clear existing data before loading')
@click.option('--skip-confirmation', is_flag=True, help='Skip confirmation prompt when using --reset')
def load_examples(reset, skip_confirmation):
    """Load example dataset fixtures for demonstration and testing."""
    setup_django()
    from django.core.management import call_command

    args = ['load_examples']
    if reset:
        args.append('--reset')
    if skip_confirmation:
        args.append('--skip-confirmation')

    try:
        call_command(*args)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
