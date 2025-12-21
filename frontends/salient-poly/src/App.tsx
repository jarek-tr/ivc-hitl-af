import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type BootLike = Record<string, any>;

interface BootWindow extends Window {
  __BOOTSTRAP__?: BootLike;
  __BOOT_CONFIG__?: BootLike;
  BOOT?: BootLike;
}

type Point = { x: number; y: number };
type DisplayPoint = { x: number; y: number };

interface ImageInfo {
  naturalWidth: number;
  naturalHeight: number;
  renderedWidth: number;
  renderedHeight: number;
}

type StatusKind = 'idle' | 'pending' | 'success' | 'error';

interface StatusState {
  state: StatusKind;
  message: string;
}

const TEST_JPG_URL =
  'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1600&q=80';
const TOOL_VERSION = 'salient-poly@0.1.0';

const bootWindow = window as BootWindow;
const bootConfig: BootLike =
  bootWindow.__BOOTSTRAP__ ?? bootWindow.__BOOT_CONFIG__ ?? bootWindow.BOOT ?? {};

const resolveTaskId = (boot: BootLike): string | number | undefined => {
  return (
    boot.task_id ??
    boot.task?.id ??
    boot.bundle?.task?.id ??
    boot.taskId ??
    boot.bundle?.task_id ??
    undefined
  );
};

const resolveImageUrl = (boot: BootLike): string | undefined => {
  return (
    boot.image_url ??
    boot.asset?.url ??
    boot.asset?.metadata?.image_url ??
    boot.bundle?.image_url ??
    boot.bundle?.asset_url ??
    boot.bundle?.asset?.metadata?.image_url ??
    undefined
  );
};

const resolvedTaskId = resolveTaskId(bootConfig);
const resolvedImageUrl = resolveImageUrl(bootConfig) ?? TEST_JPG_URL;

const getCsrfToken = (): string | null => {
  if (typeof document === 'undefined') {
    return null;
  }
  const match = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/i);
  return match ? decodeURIComponent(match[1]) : null;
};

const App = () => {
  const [points, setPoints] = useState<Point[]>([]);
  const [closed, setClosed] = useState(false);
  const [imageInfo, setImageInfo] = useState<ImageInfo | null>(null);
  const [status, setStatus] = useState<StatusState>({
    state: 'idle',
    message: 'Add vertices to outline the salient object.'
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const imageRef = useRef<HTMLImageElement | null>(null);
  const overlayRef = useRef<HTMLDivElement | null>(null);

  const vertexCount = points.length;
  const canSubmit = Boolean(resolvedTaskId) && closed && vertexCount >= 3 && !isSubmitting;

  const updateImageMetrics = useCallback(() => {
    const img = imageRef.current;
    if (!img) {
      return;
    }

    const naturalWidth = img.naturalWidth || img.width;
    const naturalHeight = img.naturalHeight || img.height;
    const renderedWidth = img.clientWidth;
    const renderedHeight = img.clientHeight;

    if (naturalWidth === 0 || naturalHeight === 0) {
      return;
    }

    setImageInfo({
      naturalWidth,
      naturalHeight,
      renderedWidth,
      renderedHeight
    });
  }, []);

  useEffect(() => {
    updateImageMetrics();
    window.addEventListener('resize', updateImageMetrics);
    return () => {
      window.removeEventListener('resize', updateImageMetrics);
    };
  }, [updateImageMetrics]);

  const convertDisplayToImage = useCallback(
    (displayPoint: DisplayPoint): Point | null => {
      if (!imageInfo || imageInfo.renderedWidth === 0 || imageInfo.renderedHeight === 0) {
        return null;
      }

      const scaleX = imageInfo.naturalWidth / imageInfo.renderedWidth;
      const scaleY = imageInfo.naturalHeight / imageInfo.renderedHeight;

      return {
        x: Number((displayPoint.x * scaleX).toFixed(2)),
        y: Number((displayPoint.y * scaleY).toFixed(2))
      };
    },
    [imageInfo]
  );

  const displayPoints = useMemo<DisplayPoint[]>(() => {
    if (!imageInfo) {
      return [];
    }

    const { naturalWidth, naturalHeight, renderedWidth, renderedHeight } = imageInfo;
    if (!naturalWidth || !naturalHeight) {
      return [];
    }

    return points.map((pt) => ({
      x: (pt.x / naturalWidth) * renderedWidth,
      y: (pt.y / naturalHeight) * renderedHeight
    }));
  }, [points, imageInfo]);

  const isNearFirstPoint = useCallback(
    (displayPoint: DisplayPoint) => {
      if (displayPoints.length === 0) {
        return false;
      }
      const first = displayPoints[0];
      const distance = Math.hypot(displayPoint.x - first.x, displayPoint.y - first.y);
      return distance <= 12;
    },
    [displayPoints]
  );

  const handleOverlayClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (!imageInfo || !overlayRef.current) {
        return;
      }

      const rect = overlayRef.current.getBoundingClientRect();
      const clickPoint: DisplayPoint = {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top
      };

      if (!closed && vertexCount >= 3 && isNearFirstPoint(clickPoint)) {
        setClosed(true);
        setStatus({ state: 'idle', message: 'Polygon closed. Submit when ready.' });
        return;
      }

      if (closed) {
        return;
      }

      const imagePoint = convertDisplayToImage(clickPoint);
      if (!imagePoint) {
        return;
      }

      setPoints((prev) => [...prev, imagePoint]);
      setStatus({
        state: 'idle',
        message: `Vertex ${vertexCount + 1} recorded in image pixels.`
      });
    },
    [closed, convertDisplayToImage, imageInfo, isNearFirstPoint, vertexCount]
  );

  const closePolygon = useCallback(() => {
    if (closed || vertexCount < 3) {
      return;
    }
    setClosed(true);
    setStatus({ state: 'idle', message: 'Polygon closed. Submit when ready.' });
  }, [closed, vertexCount]);

  const undoLastPoint = useCallback(() => {
    setPoints((prev) => prev.slice(0, -1));
    setStatus({ state: 'idle', message: 'Removed the last vertex.' });
  }, []);

  const resetPolygon = useCallback((message: string) => {
    setPoints([]);
    setClosed(false);
    setStatus({ state: 'idle', message });
  }, []);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === 'Enter') {
        if (!closed && vertexCount >= 3) {
          event.preventDefault();
          closePolygon();
        }
      } else if (event.key === 'Backspace') {
        if (!closed && vertexCount > 0) {
          event.preventDefault();
          undoLastPoint();
        }
      } else if (event.key.toLowerCase() === 'r') {
        event.preventDefault();
        resetPolygon('Polygon reset. Start outlining again.');
      } else if (event.key === 'Escape') {
        event.preventDefault();
        resetPolygon('Annotation cleared.');
      }
    },
    [closePolygon, closed, resetPolygon, undoLastPoint, vertexCount]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const polygonPointsAttr = useMemo(() => {
    if (displayPoints.length === 0) {
      return '';
    }
    return displayPoints.map((pt) => `${pt.x},${pt.y}`).join(' ');
  }, [displayPoints]);

  const handleSubmit = useCallback(async () => {
    if (!resolvedTaskId || !closed || points.length < 3) {
      return;
    }

    const submissionId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `salient-${Date.now()}`;
    const payload = {
      task: resolvedTaskId,
      result: {
        object: {
          type: 'polygon',
          label: 'salient_object',
          points: points.map((pt) => [Number(pt.x.toFixed(2)), Number(pt.y.toFixed(2))])
        }
      },
      schema_version: '1.0.0',
      tool_version: TOOL_VERSION,
      actor: 'dev',
      submission_id: submissionId,
      raw_payload: {
        source: 'salient-poly',
        ui: {
          closed: true,
          num_points: points.length
        }
      }
    };

    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }

    setIsSubmitting(true);
    setStatus({ state: 'pending', message: 'Submitting annotation…' });

    try {
      const response = await fetch('/api/annotations/', {
        method: 'POST',
        headers,
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const text = await response.text();
        const errorMessage = text || `Annotation request failed (${response.status})`;
        throw new Error(errorMessage);
      }

      setStatus({ state: 'success', message: 'Annotation submitted successfully.' });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unexpected error while submitting.';
      setStatus({ state: 'error', message });
    } finally {
      setIsSubmitting(false);
    }
  }, [closed, points, resolvedTaskId]);

  const statusStateLabel = status.state === 'idle' ? 'Status' : status.state === 'pending' ? 'In flight' : status.state === 'success' ? 'Success' : 'Error';

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">Plugin · Salient Object</p>
          <h1>Trace the dominant object with a single polygon</h1>
          <p className="subtitle">
            Click to place vertices. Close the loop by clicking the first vertex or pressing
            Enter. Work in natural image pixels for annotation-ready submissions.
          </p>
        </div>
        <ul className="hotkey-list">
          <li>
            <span>Enter</span>Close polygon
          </li>
          <li>
            <span>Backspace</span>Undo vertex
          </li>
          <li>
            <span>R</span>Reset
          </li>
          <li>
            <span>Esc</span>Clear
          </li>
        </ul>
      </header>

      <main className="workspace">
        <section className="image-panel">
          <div className="image-stage">
            <img
              ref={imageRef}
              src={resolvedImageUrl}
              onLoad={updateImageMetrics}
              alt="Annotation target"
            />
            <div
              className="annotation-overlay"
              ref={overlayRef}
              onClick={handleOverlayClick}
              role="presentation"
            >
              <svg width="100%" height="100%">
                {displayPoints.length >= 3 && closed && (
                  <polygon className="polygon-fill" points={polygonPointsAttr} />
                )}
                {displayPoints.length >= 2 && (
                  <polyline className="polygon-outline" points={polygonPointsAttr} />
                )}
                {displayPoints.map((pt, index) => (
                  <circle
                    key={`${pt.x}-${pt.y}-${index}`}
                    className={`vertex ${index === 0 ? 'vertex--first' : ''}`}
                    cx={pt.x}
                    cy={pt.y}
                    r={index === 0 ? 6 : 4}
                  />
                ))}
              </svg>
              {!imageInfo && <div className="overlay-hint">Loading image…</div>}
            </div>
          </div>
          <div className="canvas-callouts">
            <div>
              <p className="callout-title">Canvas overlay</p>
              <p className="callout-copy">
                Vertices snap to the source image in native pixels. Use Backspace for mistakes
                and Enter to seal the loop.
              </p>
            </div>
            <div className="callout-meta">
              <span>Task</span>
              <strong>{resolvedTaskId ?? 'Unknown'}</strong>
            </div>
          </div>
        </section>

        <aside className="side-panel">
          <div className="info-card">
            <div>
              <p className="muted-label">Task ID</p>
              <p className="info-value">{resolvedTaskId ?? 'Unavailable'}</p>
            </div>
            <div>
              <p className="muted-label">Vertices</p>
              <p className="info-value">{vertexCount}</p>
            </div>
            <div>
              <p className="muted-label">Polygon</p>
              <p className="info-value">{closed ? 'Closed' : 'Open'}</p>
            </div>
          </div>

          <div className="action-stack">
            <button
              type="button"
              className="primary-button"
              onClick={handleSubmit}
              disabled={!canSubmit}
            >
              {isSubmitting ? 'Submitting…' : 'Submit annotation'}
            </button>
            <button
              type="button"
              className="ghost-button"
              onClick={() => resetPolygon('Annotation cleared.')}
            >
              Reset polygon
            </button>
          </div>

          <div className="status-box" data-state={status.state}>
            <p className="muted-label">{statusStateLabel}</p>
            <p>{status.message}</p>
          </div>
        </aside>
      </main>
    </div>
  );
};

export default App;
