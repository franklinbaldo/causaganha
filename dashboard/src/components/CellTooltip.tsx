import { useEffect, useRef, useState } from 'preact/compat';
import { createPortal } from 'preact/compat';
import clsx from 'clsx';

interface CellData {
  date: string;
  status: string;
  uploadedAt: string | null;
  sizeMb: number | null;
}

interface CellTooltipProps {
  cellData: CellData;
  position: { x: number; y: number };
}

const STATUS_MAP: Record<string, { text: string; className: string }> = {
  collected: { text: '\u2705 Collected & Uploaded', className: 'text-success' },
  missing: { text: '\u274C Missing', className: 'text-danger' },
  partial: { text: '\u26A0\uFE0F Partial', className: 'text-warning' },
  outside: { text: 'Outside active range', className: 'text-gray-500 dark:text-gray-400 italic' },
};

const DEFAULT_STATUS = { text: '', className: 'text-gray-600 dark:text-gray-300' };

export function CellTooltip({ cellData, position }: CellTooltipProps) {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState<{ top: number; left: number; opacity: number }>({ top: -9999, left: -9999, opacity: 0 });

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

  const mapped = STATUS_MAP[cellData.status] ?? { ...DEFAULT_STATUS, text: cellData.status };
  const statusText = mapped.text;
  const statusClass = mapped.className;

  const tooltipContent = (
    <div
      ref={tooltipRef}
      role="tooltip"
      className="fixed z-50 pointer-events-none bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg p-3 min-w-[200px] text-sm"
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
    </div>
  );

  // Render to document.body to avoid parent z-index issues and overflow hidden
  if (typeof document !== 'undefined') {
    return createPortal(tooltipContent, document.body);
  }

  return null;
}
