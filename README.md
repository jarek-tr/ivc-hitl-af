# ivc-hitl-af

**CU Boulder Computer Science – Image and Video Computing Group (IVC)**  
**Human-in-the-Loop Annotation Framework**

A durable, API-first backend with **hot-swappable annotation frontends**, designed for long-lived research datasets and MTurk-style workflows.

---

## Goals
- Long-lived research infrastructure for image/video annotation
- Versioned task definitions so annotations remain interpretable years later
- Pluggable frontends per task type (compiled React bundles registered by manifest)
- Auditable, idempotent ingestion for crowdsourced annotations

---

## Tech Stack
- **Backend:** Django + DRF + Postgres
- **Async jobs:** Celery + Redis (MTurk HIT creation, polling, ingestion)
- **Assets:** S3-compatible storage (recommended via presigned URLs)
- **Frontends:** Framework-agnostic static bundles (React recommended)

---

## How It Works (Mental Model)

A UI is selected at runtime by resolving:

```
Task → TaskDefinition → TaskType → FrontendPlugin
```

Each `FrontendPlugin` registers a compiled UI bundle (JS/CSS) via a manifest.  
The backend injects that bundle into a minimal HTML shell at:

```
/api/tasks/<task_id>/annotate/
```

No frontend code is baked into Django.

---

## Quick Start (Development)

1. Copy environment config:
   ```bash
   cp .env.example .env
   ```

2. Start infrastructure:
   ```bash
   docker compose up -d db redis
   ```

3. Start application services:
   ```bash
   docker compose up -d web worker beat
   ```

4. Visit API:
   - API root: http://localhost:8000/api/
   - OpenAPI schema: http://localhost:8000/api/schema/
   - Swagger UI: http://localhost:8000/api/docs/

---

## Core Concepts

- **TaskType**  
  Logical annotation task (e.g., `bbox`, `salient_poly`, `qa`)

- **TaskDefinition (versioned)**  
  JSON schema defining labeling rules and UI expectations

- **Task**  
  A unit of work tied to an Asset + TaskDefinition

- **Annotation**  
  Versioned result JSON submitted by a frontend

- **FrontendPlugin**  
  A compiled UI bundle registered for a TaskType via manifest

---

## MTurk & Ingestion Notes

- MTurk operations live in `core.mturk`:
  - `create_hits_for_tasks`
  - `sync_open_hits`
  - `ingest_submitted_assignments`
- Annotations are **idempotent** via `submission_id`
  - Duplicate submissions return HTTP 200 with the original payload
- Assignment rows persist raw MTurk payloads and timestamps for auditability
- Plugin manifests are validated against the `frontends/` directory before activation

---

## Salient Polygon Plugin (`frontends/salient-poly`)

A polished React UI for single-object salient segmentation using polygons.

### Build the plugin
```bash
cd frontends/salient-poly
npm install
npm run build
```

Vite emits:
```
dist/assets/index.js
dist/assets/index.css
```

These paths must match the plugin manifest.

---

### Register the plugin
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
        "is_active": True,
    },
)
PY
```

---

### Patch an Asset with a test image
```bash
curl -X PATCH http://localhost:8000/api/assets/<asset_id>/ \
  -H "Content-Type: application/json" \
  -H "X-IVC-Write-Token: <your_write_token>" \
  -d '{"metadata":{"image_url":"https://picsum.photos/1200/800.jpg"}}'
```

Create a `Task` that uses the `salient_poly` TaskDefinition, then open:

```
http://localhost:8000/api/tasks/<task_id>/annotate/
```

---

## Status

This repository is intended as **shared lab infrastructure**, not a one-off project.  
Design favors clarity, explicitness, and auditability over clever abstractions.
