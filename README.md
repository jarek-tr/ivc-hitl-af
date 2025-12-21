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
