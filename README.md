# ivc-hitl-af
**CU Boulder Computer Science Image and Video Computing Group (IVC) Human-in-the-Loop Annotation Framework** — a durable, API-first backend + hot-swappable annotation frontends.

## Goals
- Long-lived research infrastructure for image/video annotation workflows (including MTurk-based pipelines)
- Versioned task definitions + label schemas so annotations remain interpretable years later
- Pluggable/replaceable frontends per task type (React bundles registered via a manifest)

## Tech
- Django + DRF + Postgres
- Celery + Redis for background jobs (e.g., MTurk HIT creation / polling / ingestion)
- S3 for assets and exports (recommended via presigned URLs)

## Quick Start (dev)
1. Copy env:
   ```bash
   cp .env.example .env
   ```
2. Start Services:
   ```bash
   docker compose up --build
   ```
3. Visit API Schema:
   - http://localhost:8000/api/schema/
   - Swagger UI: http://localhost:8000/api/docs/

## Core Concepts
- **TaskType**: logical annotation task (e.g., bbox, polygons, QA)
- **TaskDefinition (versioned)**: JSON defining UI + labeling rules
- **Task**: work unit tied to an Asset + TaskDefinition
- **Annotation**: versioned result JSON submitted by a frontend
- **FrontendPlugin**: a compiled UI bundle registered by manifest for a TaskType

## MTurk + Ingestion Notes
- Use the Celery tasks in `core.mturk` for MTurk operations:
  - `core.mturk.create_hits_for_tasks` (batch HIT creation with retries)
  - `core.mturk.sync_open_hits` (polls MTurk for assignment updates)
  - `core.mturk.ingest_submitted_assignments` (creates Annotations from MTurk answers if the UI could not reach the API)
- Annotations are idempotent via `submission_id` (use MTurk assignmentId or a stable client UUID). Duplicate submissions return HTTP 200 with the first Annotation payload.
- Assignment rows capture raw MTurk payloads + ingestion timestamps for auditing.
- Plugin manifests are validated against the `frontends/` directory before activation (required keys: name, task_type, version, root, js, result_schema_version).

## Salient Polygon Plugin
The `frontends/salient-poly` package ships the annotation UI for salient object segmentation. After cloning:

1. **Build the bundle**
   ```bash
   cd frontends/salient-poly
   npm install
   npm run build
   ```
   Vite emits `dist/assets/index.js` and `dist/assets/index.css`, matching the manifest contract.

2. **Register the plugin**
   ```bash
   python manage.py shell <<'PY'
   import json
   from core.models import TaskType, FrontendPlugin

   task_type, _ = TaskType.objects.get_or_create(
       slug="salient_poly",
       defaults={"name": "Salient Object Segmentation"},
   )
   with open("frontends/salient-poly/manifest.json") as fh:
       manifest = json.load(fh)
   FrontendPlugin.objects.update_or_create(
       task_type=task_type,
       defaults={
           "name": manifest["name"],
           "version": manifest["version"],
           "manifest": manifest,
       },
   )
   PY
   ```

3. **Patch an Asset for testing**
   Use any public JPG; the UI defaults to `https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1600&q=80`.
   ```bash
   curl -X PATCH http://localhost:8000/api/assets/<asset_id>/ \
     -H "Content-Type: application/json" \
     -H "Authorization: Token <api_token>" \
     -d '{"metadata":{"image_url":"https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1600&q=80"}}'
   ```
   Assign a `Task` that targets this asset + the `salient_poly` `TaskType`, then load the registered plugin to iterate rapidly.
