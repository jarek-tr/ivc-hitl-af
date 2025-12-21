# ivc-hitl-af

**CU Boulder Computer Science – Image and Video Computing Group (IVC)**  
**Human-in-the-Loop Annotation Framework**

A durable, API-first backend with **hot-swappable annotation frontends**, designed for long-lived research datasets and MTurk-style workflows.

---

## Design Intent (Read This First)

This framework is designed as a **research instrument**, not a one-off data collection tool.

Many annotation systems optimize for speed or simplicity.  
This system optimizes for **longevity, interpretability, and auditability** in research contexts where:

- Label definitions evolve over time  
- Annotation UIs influence outcomes  
- Annotator populations are heterogeneous  
- Old annotations must remain meaningful years later  

**Key principle:**  
New task types, schemas, and frontends should be added **without modifying or invalidating prior annotations**.

If you feel tempted to “simplify” the system, first ask whether that simplification would erase important provenance.

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

This separation is intentional:  
**annotation logic lives in frontends; provenance and orchestration live in the backend.**

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

4. Run migrations and load example data:
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py load_examples
   ```

5. Visit API:
   - API root: http://localhost:8000/api/  
   - OpenAPI schema: http://localhost:8000/api/schema/  
   - Swagger UI: http://localhost:8000/api/docs/  

---

## Core Concepts

- **TaskType** — logical annotation task (e.g., `bbox`, `polygon`, `qa`)  
- **TaskDefinition (versioned)** — JSON schema defining labeling rules and semantics  
- **Task** — unit of work tied to an Asset + TaskDefinition  
- **Annotation** — versioned result JSON submitted by a frontend  
- **FrontendPlugin** — compiled UI bundle registered via manifest  

---

## Status

This repository is intended as **shared lab infrastructure**, not a single-project artifact.

Design favors:
- explicitness over cleverness  
- versioning over mutation  
- provenance over convenience  

If you are a new student inheriting this codebase:  
**do not rewrite it — extend it.**
