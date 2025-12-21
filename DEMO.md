# Demo Script for Advisor Meeting

## Pre-Demo Setup (Do this before the meeting)

```bash
cd /Users/jarek/Code/ivc-hitl-af

# Ensure containers are running
docker compose up -d

# Verify everything is healthy
curl http://localhost:8000/api/health/ | jq .
```

## Demo Flow (15-20 minutes)

### 1. System Overview (3 minutes)

Open the README and highlight:
- **Architecture**: Plugin-based, hot-swappable frontends
- **Tech Stack**: Django + DRF, PostgreSQL, Celery, Redis
- **Production-Ready**: Deployed to main branch with all improvements

### 2. Live API Demo (5 minutes)

#### Health Check (Production Monitoring)
```bash
curl http://localhost:8000/api/health/ | jq .
```
**Show**: Database, Redis, and Celery worker status

#### Project Statistics
```bash
curl http://localhost:8000/api/projects/1/stats/ | jq .
```
**Point out**: Real-time task tracking, annotation counts, unique actors

#### Browse Projects
```bash
# List all projects
curl http://localhost:8000/api/projects/ | jq .

# Get specific project details
curl http://localhost:8000/api/projects/1/ | jq .
```

#### Export Annotations
```bash
# Export as JSON
curl http://localhost:8000/api/projects/1/export/ > annotations.json
cat annotations.json | jq '.[0]'  # Show first annotation

# Export as JSONL (for big data processing)
curl 'http://localhost:8000/api/projects/1/export/?format=jsonl' | head -1 | jq .
```
**Explain**: Production-ready export formats for analysis pipelines

#### Swagger API Documentation
Open in browser:
```
http://localhost:8000/api/docs/
```
**Show**: Interactive API documentation with try-it-out functionality

### 3. Example Data Showcase (2 minutes)

```bash
# Show all task types
curl http://localhost:8000/api/task-types/ | jq '.[] | {slug: .slug, name: .name}'

# Show tasks for each project
curl http://localhost:8000/api/tasks/ | jq '.results[] | {id: .id, project: .project, status: .status}'

# Show an annotation
curl http://localhost:8000/api/annotations/ | jq '.results[0]'
```

**Explain**:
- 3 different annotation types (classification, bounding box, polygon)
- Versioned task definitions for long-lived datasets
- Idempotent submissions via submission_id

### 4. Documentation Tour (3 minutes)

#### Architecture Guide
```bash
open docs/architecture.md
```
**Scroll through sections:**
- Core principles
- Data model diagrams
- API endpoints with examples
- Plugin system architecture
- MTurk integration workflow

**Stats**: 1,179 lines of comprehensive documentation

#### Deployment Guide
```bash
open docs/deployment.md
```
**Show the comparison table:**
- 6 deployment options (Heroku, Render, DigitalOcean, AWS, etc.)
- Cost estimates ($15-114/mo)
- One-click deploy configurations

**Point to**:
- Procfile (Heroku)
- render.yaml (Render.com)
- app.json (Heroku Button)

#### Plugin Development Guide
```bash
open docs/plugin-guide.md
```
**Highlight:**
- Complete tutorial for building custom annotation UIs
- Manifest format specification
- API integration examples
- 802 lines of guidance

### 5. Security & Testing (2 minutes)

#### Show Security Tests
```bash
# Run security tests
docker compose exec web pytest backend/core/tests/test_security.py -v

# Show what's being tested
cat backend/core/tests/test_security.py | grep "def test_"
```

**Explain protections:**
- Directory traversal prevention
- Rate limiting (100 requests/hour)
- Write token authentication
- CSRF protection

#### Show MTurk Tests
```bash
cat backend/core/tests/test_mturk.py | grep "def test_"
```

### 6. Production Readiness (3 minutes)

#### CLI Tool
```bash
# Show available commands
docker compose exec web python -c "from ivc_hitl_af.cli import main; main(['--help'])"
```

**Demonstrate:**
```bash
# Validate plugins (for CI/CD)
docker compose exec web python manage.py validate_plugins

# Export via management command
docker compose exec web python manage.py shell -c "
from core.models import Project
for p in Project.objects.all():
    print(f'{p.id}. {p.slug} - {p.name}')
"
```

#### Deployment Configs
```bash
# Show Heroku setup
cat Procfile
cat app.json | jq '.formation'

# Show Render setup
cat render.yaml | head -20

# Show Python packaging
cat setup.py | grep -A 10 'install_requires'
```

**Explain**: Ready to deploy with a single command to multiple platforms

## Key Talking Points

### What Was Delivered
"I implemented **all 16 incremental improvements** from the architectural review:"

1. **Tier 1 - Critical Security**: Directory traversal protection, health checks, rate limiting
2. **Tier 2 - Production Readiness**: Database optimizations, MTurk workflow completeness
3. **Tier 3 - Quality of Life**: Stats/export endpoints, CLI tool, periodic tasks
4. **Tier 4 - Extensibility**: S3 plugin support, deployment automation

### Production Readiness
"The system is now production-ready with:"
- ✅ Comprehensive monitoring (health checks for all services)
- ✅ Security hardening (rate limiting, input validation)
- ✅ Complete documentation (2,783 lines)
- ✅ Test suite (security + MTurk integration)
- ✅ Multiple deployment options (6 platforms documented)
- ✅ Example datasets for onboarding

### Research Infrastructure Value
"This is publishable research infrastructure that:"
- Future students can inherit and understand (comprehensive docs)
- Scales from laptop to production (6 deployment options documented)
- Includes example datasets for quick onboarding
- Supports long-lived datasets with versioned schemas
- Provides complete audit trails for crowdsourced annotations
- Is ready to deploy today

### Cost Estimates
"Depending on workload, deployment costs range from:"
- Self-hosted: $15-30/month (DigitalOcean droplet)
- Render: $35/month (hobby tier)
- Heroku: $114/month (full production)
- Can handle thousands of annotations for research projects

## Quick Wins to Highlight

1. **One-Click Deploy**: "We can deploy to Heroku or Render with a single click"
2. **Example Data**: "New students can start annotating in 5 minutes"
3. **API-First**: "Everything is accessible via REST API for integration"
4. **Monitoring**: "Health checks integrate with any container orchestration platform"
5. **Documentation**: "Complete guides for architecture, deployment, and plugin development"

## Backup: If Demo Fails

If containers aren't working, fall back to showing:
1. The comprehensive documentation files
2. The test suite demonstrating security
3. The deployment configurations
4. The example dataset fixture
5. Git commit history showing incremental improvements

## After the Demo

Mention next steps:
- Ready to deploy to staging environment
- Can create custom plugins for specific annotation tasks
- Documentation supports future lab members
- System scales with research needs

Good luck! The system is in excellent shape.
