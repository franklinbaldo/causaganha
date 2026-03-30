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
      statusClass = 'text-gray-500 dark:text-gray-400 italic';
      break;
    default:
      statusText = cellData.status;
      statusClass = 'text-gray-600 dark:text-gray-300';
  }

  const tooltipContent = (
    <div
      ref={tooltipRef}
      role="tooltip"
      className="fixed z-50 pointer-events-auto bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg p-3 min-w-[200px] text-sm"
      style={style}
    >
      <div className="font-mono font-medium text-black dark:text-white mb-1">
        {cellData.date}
      </div>
      <div className={clsx("font-medium", statusClass)}>
        {statusText}
      </div>

      {cellData.uploadedAt && (
        <div className="mt-2 text-xs text-gray-600 dark:text-gray-300">
          <span className="opacity-70">Uploaded:</span>{' '}
          <span className="font-mono">{new Date(cellData.uploadedAt).toLocaleString()}</span>
        </div>
      )}
      {cellData.sizeMb && (
        <div className="text-xs text-gray-600 dark:text-gray-300 mt-0.5">
          <span className="opacity-70">Size:</span>{' '}
          <span className="font-mono">{cellData.sizeMb.toFixed(2)} MB</span>
        </div>
      )}
      {cellData.zipUrl && (
        <div className="mt-1 text-[10px] text-gray-500 truncate max-w-[180px]">
          <a
            href={cellData.zipUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent hover:underline pointer-events-auto flex items-center gap-1"
          >
            <svg className="w-3 h-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download ZIP
          </a>
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
