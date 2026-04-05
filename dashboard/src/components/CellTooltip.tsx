import { useEffect, useRef, useState } from 'preact/compat';
import { createPortal } from 'preact/compat';

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
  missing: { text: '\u274C Missing', className: 'text-error' },
  partial: { text: '\u26A0\uFE0F Partial', className: 'text-warning' },
  outside: { text: 'Outside active range', className: '' },
};

const DEFAULT_STATUS = { text: '', className: '' };

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
    if (left + rect.width> window.innerWidth - padding) {
      left = position.x - rect.width - padding;
    }

    // Check bottom edge
    if (top + rect.height> window.innerHeight - padding) {
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
      ref={tooltipRef} role="tooltip"
      className="bg-neutral text-neutral-content p-4 rounded-lg shadow-xl text-sm z-50 pointer-events-none fixed space-y-1"
      style={style}>
      <div className="font-bold border-b border-neutral-content/20 pb-1 mb-2">
        {cellData.date}
      </div>
      <div className={statusClass || undefined}>
        {statusText}
      </div>

      {cellData.uploadedAt && (
        <div className="text-xs opacity-70 mt-2">
          <span>Uploaded:</span>{' '}
          <span>{new Date(cellData.uploadedAt).toLocaleString()}</span>
        </div>
      )}
      {cellData.sizeMb && (
        <div className="text-xs opacity-70">
          <span>Size:</span>{' '}
          <span>{cellData.sizeMb.toFixed(2)} MB</span>
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
