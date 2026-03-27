import { useEffect, useRef, useState } from 'preact/compat';
import { createPortal } from 'preact/compat';
import clsx from 'clsx';

export function CellTooltip({ cellData, position }) {
  const tooltipRef = useRef(null);
  const [style, setStyle] = useState({ top: -9999, left: -9999, opacity: 0 });

  useEffect(() => {
    if (!tooltipRef.current || !position) return;

    const rect = tooltipRef.current.getBoundingClientRect();
    const padding = 12; // distance from cursor

    let left = position.x + padding;
    let top = position.y + padding;

    // Check right edge
    if (left + rect.width > window.innerWidth - padding) {
      left = position.x - rect.width - padding;
    }

    // Check bottom edge
    if (top + rect.height > window.innerHeight - padding) {
      top = position.y - rect.height - padding;
    }

    setStyle({
      left: Math.max(padding, left),
      top: Math.max(padding, top),
      opacity: 1,
    });
  }, [position, cellData]);

  if (!cellData || !position) return null;

  let statusText = '';
  let statusClass = '';

  switch (cellData.status) {
    case 'collected':
      statusText = '✅ Collected & Uploaded';
      statusClass = 'text-success';
      break;
    case 'missing':
      statusText = '❌ Missing';
      statusClass = 'text-danger';
      break;
    case 'partial':
      statusText = '⚠️ Partial';
      statusClass = 'text-warning';
      break;
    case 'outside':
      statusText = 'Outside active range';
      statusClass = 'text-content-tertiary italic';
      break;
    default:
      statusText = cellData.status;
      statusClass = 'text-content-secondary';
  }

  const tooltipContent = (
    <div
      ref={tooltipRef}
      role="tooltip"
      className="fixed z-50 pointer-events-none bg-surface border border-border rounded-lg shadow-lg p-3 min-w-[200px] text-sm"
      style={style}
    >
      <div className="font-mono font-medium text-content mb-1">
        {cellData.date}
      </div>
      <div className={clsx("font-medium", statusClass)}>
        {statusText}
      </div>

      {cellData.uploadedAt && (
        <div className="mt-2 text-xs text-content-secondary">
          <span className="opacity-70">Uploaded:</span>{' '}
          <span className="font-mono">{new Date(cellData.uploadedAt).toLocaleString()}</span>
        </div>
      )}
      {cellData.sizeMb && (
        <div className="text-xs text-content-secondary mt-0.5">
          <span className="opacity-70">Size:</span>{' '}
          <span className="font-mono">{cellData.sizeMb.toFixed(2)} MB</span>
        </div>
      )}
    </div>
  );

  // Render to document.body to avoid parent z-index issues and overflow hidden
  if (typeof document !== 'undefined') {
    return createPortal(tooltipContent, document.body);
  }

  return null;
}
