# Annotation Frontend Plugin Development Guide

This guide explains how to build annotation frontend plugins for the IVC HITL (Human-in-the-Loop) system. We use the **salient-poly** plugin as a reference example throughout.

## Overview

Annotation plugins are self-contained frontend applications that handle human annotation of media assets (images, video frames, etc.). Each plugin:
- Renders an interactive interface for a specific annotation task type
- Receives asset data via a standardized API
- Submits annotations back to the backend
- Operates independently within the IVC HITL platform

---

## 1. Plugin Structure

### Directory Layout

Plugins live in the `/frontends` directory of the project:

```
frontends/
  salient-poly/              # Your plugin name
    dist/                    # Built output (auto-generated)
      assets/
        index.js
        index.css
    src/
      main.tsx              # Entry point
      App.tsx               # Main component
      styles.css
    index.html              # Template for Vite
    manifest.json           # Plugin metadata
    package.json            # NPM configuration
    vite.config.ts          # Build configuration
    tsconfig.json
```

### Manifest.json Requirements

The `manifest.json` file declares your plugin to the backend system:

```json
{
  "name": "Salient Object Polygon Segmentor",
  "task_type": "salient_poly",
  "version": "0.1.0",
  "root": "salient-poly/dist",
  "css": ["assets/index.css"],
  "js": ["assets/index.js"],
  "result_schema_version": "1.0.0"
}
```

**Required Fields:**

- **`name`** (string): Human-readable plugin name
- **`task_type`** (string): Unique identifier matching a `TaskType` in the database
  - Must be lowercase with underscores (e.g., `salient_poly`, `bbox`)
  - Referenced when creating `TaskDefinition` objects
- **`version`** (string): Semantic version (e.g., `0.1.0`, `1.2.3`)
  - Bumped when deploying plugin updates
- **`root`** (string): Relative path to built artifacts from `/frontends`
  - Typically `"{plugin-name}/dist"`
  - Must be a relative path, no `..` or absolute paths
- **`js`** (array): JavaScript asset files relative to `root`
  - Typically `["assets/index.js"]` for single-entry Vite builds
  - Supports multiple files if code-split by Vite
- **`css`** (array): CSS asset files relative to `root`
  - Typically `["assets/index.css"]` for Vite builds
  - Can be empty if styles are bundled into JS
- **`result_schema_version`** (string): Version of your annotation result format
  - Used for backward compatibility when result schema changes
  - Recommend tracking alongside `version`

**Optional Fields:**

- Any additional custom metadata is preserved through validation

---

## 2. Frontend Contract: window.__IVC_BOOT__

The backend injects a global object into the HTML that provides context:

```javascript
window.__IVC_BOOT__ = {
  "taskId": 42,
  "apiBase": "/api",
  "mturk": {
    "assignmentId": "...",
    "hitId": "...",
    "workerId": "...",
    "sandbox": false,
    "submitUrl": "https://www.mturk.com/mturk/externalSubmit"
  }
}
```

**Salient-poly's Fallback Resolution:**

Since the exact structure can vary across deployment contexts, salient-poly defensively resolves values:

```typescript
interface BootWindow extends Window {
  __BOOTSTRAP__?: Record<string, any>;
  __BOOT_CONFIG__?: Record<string, any>;
  BOOT?: Record<string, any>;
}

const bootWindow = window as BootWindow;
const bootConfig =
  bootWindow.__BOOTSTRAP__ ??
  bootWindow.__BOOT_CONFIG__ ??
  bootWindow.BOOT ??
  {};

// Resolve task ID from multiple possible locations
const resolveTaskId = (boot: Record<string, any>): string | number | undefined => {
  return (
    boot.task_id ??
    boot.task?.id ??
    boot.bundle?.task?.id ??
    boot.taskId ??
    boot.bundle?.task_id ??
    undefined
  );
};
```

**Best Practice:** Copy this defensive resolution pattern into your plugin.

---

## 3. Required API Calls

### GET /api/tasks/{id}/bundle/

**Purpose:** Fetch all context needed to annotate a task in a single request.

**Response Example:**
```json
{
  "task": {
    "id": 42,
    "project": 1,
    "asset": 5,
    "task_definition": 3,
    "status": "pending",
    "priority": 1,
    "assigned_to": "",
    "payload": {},
    "created_at": "2025-01-15T10:30:00Z"
  },
  "asset": {
    "id": 5,
    "project": 1,
    "media_type": "image/jpeg",
    "s3_key": "uploads/photo.jpg",
    "sha256": "abc123...",
    "width": 1920,
    "height": 1080,
    "metadata": {},
    "created_at": "2025-01-14T09:00:00Z"
  },
  "task_type": {
    "id": 2,
    "slug": "salient_poly",
    "name": "Salient Object Segmentation",
    "description": "Outline dominant object with polygon"
  },
  "task_definition": {
    "id": 3,
    "task_type": 2,
    "version": "1.0",
    "definition": { /* custom task configuration */ },
    "created_at": "2025-01-10T08:00:00Z"
  },
  "plugin": {
    "name": "Salient Object Polygon Segmentor",
    "task_type": "salient_poly",
    "version": "0.1.0",
    "root": "salient-poly/dist",
    "css": ["assets/index.css"],
    "js": ["assets/index.js"],
    "result_schema_version": "1.0.0"
  }
}
```

**Usage in Salient-poly:**
- The plugin extracts `task.id` to identify the task
- Uses `asset` metadata to construct media URLs (from S3 or CDN)
- Stores `task_definition.definition` for task-specific rules

---

### POST /api/annotations/

**Purpose:** Submit a completed annotation.

**Request Body Format:**
```json
{
  "task": 42,
  "result": {
    "object": {
      "type": "polygon",
      "label": "salient_object",
      "points": [[100.5, 200.3], [150.2, 250.1], [120.0, 280.4]]
    }
  },
  "schema_version": "1.0.0",
  "tool_version": "salient-poly@0.1.0",
  "actor": "worker_123",
  "submission_id": "uuid-or-unique-id",
  "raw_payload": {
    "source": "salient-poly",
    "ui": {
      "closed": true,
      "num_points": 3
    }
  },
  "assignment": null
}
```

**Field Descriptions:**

- **`task`** (int, required): Task ID being annotated
- **`result`** (object, required): Your annotation result
  - Structure is task-type-specific
  - For salient-poly: `{ object: { type: "polygon", label: "...", points: [...] } }`
- **`schema_version`** (string, required): Version of result format
  - Must match `result_schema_version` in manifest
  - Supports schema evolution without breaking old annotations
- **`tool_version`** (string, recommended): Full version of your plugin
  - Format: `"{plugin-name}@{version}"` (e.g., `"salient-poly@0.1.0"`)
  - Aids debugging and reproducibility
- **`actor`** (string, optional): Identifier for the annotator
  - Can be worker ID, user email, "dev", etc.
  - Leave empty if anonymous
- **`submission_id`** (string, optional): Unique ID for this submission
  - Prevents double-submission bugs
  - Auto-generated as UUID if not provided
  - Backend deduplicates by (task, submission_id) pair
- **`raw_payload`** (object, optional): Additional metadata
  - Unstructured field for plugin-specific debug info
  - For salient-poly: UI state (closed polygon, point count)
- **`assignment`** (int, optional): Assignment ID (for MTurk workflows)
  - Omit if not using MTurk integration

**Response Status Codes:**

- **201 Created**: New annotation successfully submitted
- **200 OK**: Duplicate submission (same task + submission_id)
  - Returns the existing annotation unchanged
  - Prevents errors from retry logic
- **400 Bad Request**: Validation error (missing required fields, invalid structure)
- **429 Too Many Requests**: Rate limited (100 annotations per hour per IP)

---

## 4. Annotation Submission Format

### Salient-poly Example

The salient-poly plugin submits polygon annotations:

```typescript
const payload = {
  task: resolvedTaskId,
  result: {
    object: {
      type: "polygon",
      label: "salient_object",
      // Points stored in natural image pixels (not display pixels)
      points: points.map((pt) => [
        Number(pt.x.toFixed(2)),
        Number(pt.y.toFixed(2))
      ])
    }
  },
  schema_version: "1.0.0",
  tool_version: "salient-poly@0.1.0",
  actor: "dev",
  submission_id: crypto.randomUUID(),
  raw_payload: {
    source: "salient-poly",
    ui: {
      closed: true,
      num_points: points.length
    }
  }
};

const response = await fetch("/api/annotations/", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-CSRFToken": getCsrfToken()  // See CSRF section below
  },
  credentials: "same-origin",
  body: JSON.stringify(payload)
});
```

### CSRF Protection

Django requires CSRF tokens for POST requests. Extract from cookies:

```typescript
const getCsrfToken = (): string | null => {
  if (typeof document === 'undefined') {
    return null;
  }
  const match = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/i);
  return match ? decodeURIComponent(match[1]) : null;
};

const headers: Record<string, string> = {
  'Content-Type': 'application/json'
};
const csrfToken = getCsrfToken();
if (csrfToken) {
  headers['X-CSRFToken'] = csrfToken;
}
```

### Image Coordinate Systems

**Critical:** Convert display coordinates to natural image pixels before submission.

```typescript
interface ImageInfo {
  naturalWidth: number;   // Original image resolution
  naturalHeight: number;
  renderedWidth: number;  // Displayed size in browser
  renderedHeight: number;
}

// Update metrics when image loads or window resizes
const updateImageMetrics = useCallback(() => {
  const img = imageRef.current;
  if (!img) return;

  setImageInfo({
    naturalWidth: img.naturalWidth,
    naturalHeight: img.naturalHeight,
    renderedWidth: img.clientWidth,
    renderedHeight: img.clientHeight
  });
}, []);

// Convert display click to image pixels
const convertDisplayToImage = useCallback(
  (displayPoint: DisplayPoint): Point | null => {
    if (!imageInfo) return null;

    const scaleX = imageInfo.naturalWidth / imageInfo.renderedWidth;
    const scaleY = imageInfo.naturalHeight / imageInfo.renderedHeight;

    return {
      x: Number((displayPoint.x * scaleX).toFixed(2)),
      y: Number((displayPoint.y * scaleY).toFixed(2))
    };
  },
  [imageInfo]
);
```

---

## 5. MTurk Integration (Optional)

For Amazon Mechanical Turk workflows, the backend provides extra metadata:

```typescript
interface MTurkBoot {
  assignmentId: string;
  hitId: string;
  workerId: string;
  sandbox: boolean;
  submitUrl: string;
}

const boot = window.__IVC_BOOT__;
if (boot.mturk) {
  const { assignmentId, hitId, workerId, submitUrl } = boot.mturk;
  // Handle MTurk-specific submission logic
}
```

### MTurk Submission Workflow

1. User completes annotation and clicks Submit
2. Plugin calls `POST /api/annotations/` with `submission_id`
3. Backend creates `Annotation` and finds/creates matching `Assignment`
4. Plugin receives success response
5. Plugin submits MTurk form to `submitUrl`:
   ```html
   <form method="POST" action={submitUrl}>
     <input type="hidden" name="assignmentId" value={mturk.assignmentId} />
     <button type="submit">Submit to MTurk</button>
   </form>
   ```

### Optional Assignment Reference

If you have an `Assignment` object ID, pass it in the annotation:

```json
{
  "task": 42,
  "result": { /* ... */ },
  "assignment": 5
}
```

This links the annotation to MTurk tracking metadata (worker ID, HIT ID, etc.).

---

## 6. Build Process (Vite Example)

### Project Structure

```
salient-poly/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  src/
    main.tsx
    App.tsx
    styles.css
```

### package.json

```json
{
  "name": "salient-poly",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.5",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.7.2",
    "vite": "^5.2.9"
  }
}
```

### vite.config.ts

Configure Vite to output assets in the structure manifest.json expects:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    cssCodeSplit: false,  // Single CSS file
    rollupOptions: {
      input: 'index.html',
      output: {
        entryFileNames: 'assets/index.js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.css')) {
            return 'assets/index.css';
          }
          return 'assets/[name][extname]';
        }
      }
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173
  }
});
```

### index.html

Vite uses this template during build:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Salient Poly Plugin</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### Build Commands

```bash
cd frontends/salient-poly

# Install dependencies (once)
npm install

# Development mode (hot reload)
npm run dev
# Opens http://localhost:5173

# Production build
npm run build
# Generates dist/ with assets/index.js and assets/index.css
```

### Output Structure

After `npm run build`, Vite creates:

```
dist/
  assets/
    index.js       # Main bundle
    index.css      # Styles
  index.html       # (not used by backend, only in dev)
```

The manifest.json references these:
```json
{
  "root": "salient-poly/dist",
  "js": ["assets/index.js"],
  "css": ["assets/index.css"]
}
```

---

## 7. Registration Process

### Step 1: Create TaskType (if new)

```bash
cd backend
python manage.py shell
```

```python
from core.models import TaskType

task_type, created = TaskType.objects.get_or_create(
    slug='salient_poly',
    defaults={
        'name': 'Salient Object Segmentation',
        'description': 'Outline the dominant object in an image with a polygon'
    }
)
print(f"TaskType: {task_type.id} ({'created' if created else 'existing'})")
```

### Step 2: Register Plugin in Database

Use the Django admin or API:

**Option A: Django Admin**
1. Navigate to `/admin/core/frontendplugin/`
2. Click "Add Frontend Plugin"
3. Fill in:
   - **Task Type**: Select your TaskType
   - **Name**: "Salient Object Polygon Segmentor"
   - **Version**: "0.1.0"
   - **Manifest**: Paste the manifest.json content as JSON
   - **Is Active**: Check to enable
4. Save

**Option B: REST API**
```bash
curl -X POST http://localhost:8000/api/plugins/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "task_type": 2,
    "name": "Salient Object Polygon Segmentor",
    "version": "0.1.0",
    "manifest": {
      "name": "Salient Object Polygon Segmentor",
      "task_type": "salient_poly",
      "version": "0.1.0",
      "root": "salient-poly/dist",
      "css": ["assets/index.css"],
      "js": ["assets/index.js"],
      "result_schema_version": "1.0.0"
    },
    "is_active": true
  }'
```

### Step 3: Create TaskDefinition

```python
from core.models import TaskDefinition, TaskType

task_type = TaskType.objects.get(slug='salient_poly')
task_def, created = TaskDefinition.objects.get_or_create(
    task_type=task_type,
    version='1.0',
    defaults={
        'definition': {
            'instructions': 'Outline the dominant object with a polygon'
        }
    }
)
print(f"TaskDefinition: {task_def.id}")
```

### Step 4: Create Tasks

```python
from core.models import Task, Project, Asset

project = Project.objects.first()
asset = Asset.objects.first()
task_def = TaskDefinition.objects.get(task_type__slug='salient_poly', version='1.0')

task = Task.objects.create(
    project=project,
    asset=asset,
    task_definition=task_def,
    status='pending',
    priority=1
)
print(f"Task: {task.id}")
```

### Step 5: Access Annotation UI

Navigate to: `http://localhost:8000/annotate/tasks/{task_id}/`

The backend will:
1. Load the TaskType for this task
2. Find the active FrontendPlugin for that TaskType
3. Inject the plugin HTML shell with `window.__IVC_BOOT__`
4. Serve plugin assets from the manifest

---

## 8. Validation

### Command: validate_plugins

Django management command validates all registered plugins:

```bash
cd backend

# Basic validation
python manage.py validate_plugins

# Fix validation errors (update DB from filesystem)
python manage.py validate_plugins --fix

# Exit with error if any plugin fails
python manage.py validate_plugins --strict
```

**What It Checks:**

1. **Manifest Structure**
   - All required fields present (name, task_type, version, root, js, css, result_schema_version)
   - Fields have correct types (strings, arrays)

2. **Plugin Root Path**
   - `root` path exists relative to `/frontends`
   - No directory traversal attempts (`..`)

3. **Asset Files**
   - All files in `js` and `css` arrays exist
   - Paths don't escape plugin root

4. **Filesystem Manifest**
   - Optional: Checks if `manifest.json` exists next to plugin
   - Optional: Warns if DB manifest differs from filesystem

### Example Output

```
Validating 2 plugin(s)...

✓ salient_poly (v0.1.0)
  OK
○ bbox (v0.2.0)
  ERROR: Missing assets: assets/index.css

============================================================
ERRORS: 1
  - bbox: Missing assets: ['assets/index.css']
```

### Common Validation Issues

**Issue:** `Manifest root '{root}' does not exist`
- **Cause:** Path in manifest.json doesn't point to a directory in `/frontends`
- **Fix:** Build your plugin (`npm run build`) and update manifest.json

**Issue:** `Manifest asset '{asset}' not found under {root}`
- **Cause:** Referenced JS/CSS files weren't built
- **Fix:** Run `npm run build` and check Vite config (especially output paths)

**Issue:** `Manifest path '{path}' escapes plugin root`
- **Cause:** Asset path contains `..` or `root` contains `..`
- **Fix:** Use relative paths that stay within plugin directory

**Issue:** `Manifest field 'js' must be a list`
- **Cause:** `js` is not an array in manifest.json
- **Fix:** Use `"js": ["assets/index.js"]` (array, not string)

---

## Summary: Creating Your Own Plugin

1. **Create plugin directory** in `/frontends/{plugin-name}/`

2. **Initialize project** with your chosen toolchain (Vite recommended)

3. **Write manifest.json** with required fields

4. **Implement annotation UI:**
   - Read task context from window.__IVC_BOOT__
   - Fetch asset data from `/api/tasks/{id}/bundle/`
   - Submit annotations to `POST /api/annotations/`
   - Handle CSRF tokens

5. **Build** (`npm run build`)

6. **Validate** (`python manage.py validate_plugins`)

7. **Register** in database (TaskType → FrontendPlugin → TaskDefinition)

8. **Test** at `/annotate/tasks/{task_id}/`

---

## Reference: Salient-poly Key Files

- **Manifest**: `/frontends/salient-poly/manifest.json`
- **Entry Point**: `/frontends/salient-poly/src/main.tsx`
- **Component**: `/frontends/salient-poly/src/App.tsx`
- **Build Config**: `/frontends/salient-poly/vite.config.ts`
- **Styles**: `/frontends/salient-poly/src/styles.css`

All examples in this guide are extracted from salient-poly's implementation.

---

## Troubleshooting

**Q: Plugin assets fail to load (404 errors)**
- A: Check plugin root path in manifest matches built dist/ directory
- A: Verify assets exist after `npm run build`
- A: Run `python manage.py validate_plugins` to identify issues

**Q: Boot config is undefined**
- A: Use defensive resolution (see section 2)
- A: Check browser console for window.__IVC_BOOT__ value

**Q: Annotation submission fails**
- A: Verify CSRF token extraction works
- A: Check task ID is present in boot config
- A: Ensure submission_id is unique per submission (use UUID)

**Q: Plugin doesn't update after rebuild**
- A: Clear browser cache (Ctrl+Shift+Delete)
- A: Bump version in manifest.json and re-register plugin
- A: Run `python manage.py validate_plugins --fix`

**Q: Image coordinates seem off**
- A: Verify natural vs. display pixel conversion (section 4)
- A: Check image aspect ratio and scaling CSS
- A: Log both image dimensions and click points to console
