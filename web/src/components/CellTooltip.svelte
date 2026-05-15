<script lang="ts">
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
    collected: { text: '\u2705 Collected & Uploaded', className: 'status-success' },
    missing: { text: '\u274C Missing', className: 'status-error' },
    partial: { text: '\u26A0\uFE0F Partial', className: 'status-warning' },
    outside: { text: 'Outside active range', className: '' },
  };

  const DEFAULT_STATUS = { text: '', className: '' };

  let { cellData, position }: CellTooltipProps = $props();

  let tooltipEl = $state<HTMLDivElement | undefined>(undefined);
  let style = $state<{ top: number; left: number; opacity: number }>({ top: -9999, left: -9999, opacity: 0 });

  const mapped = $derived(STATUS_MAP[cellData.status] ?? { ...DEFAULT_STATUS, text: cellData.status });
  const statusText = $derived(mapped.text);
  const statusClass = $derived(mapped.className);

  $effect(() => {
    // Track dependencies
    position;
    cellData;

    if (!tooltipEl || !position) return;

    const rect = tooltipEl.getBoundingClientRect();
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

    style = {
      left: Math.max(padding, left),
      top: Math.max(padding, top),
      opacity: 1,
    };
  });
</script>

{#if cellData && position}
  <div
    bind:this={tooltipEl}
    role="tooltip"
    class="tooltip-container"
    style="top: {style.top}px; left: {style.left}px; opacity: {style.opacity};"
  >
    <div class="tooltip-header">
      {cellData.date}
    </div>
    <div class={statusClass || undefined}>
      {statusText}
    </div>

    {#if cellData.uploadedAt}
      <div class="tooltip-meta">
        <span>Uploaded:</span>{' '}
        <span>{new Date(cellData.uploadedAt).toLocaleString('pt-BR')}</span>
      </div>
    {/if}
    {#if cellData.sizeMb}
      <div class="tooltip-meta-inline">
        <span>Size:</span>{' '}
        <span>{cellData.sizeMb.toFixed(2)} MB</span>
      </div>
    {/if}
  </div>
{/if}

<style>
  .tooltip-container {
    background: var(--color-neutral, #2a2e37);
    color: var(--color-neutral-content, #fff);
    padding: 1rem;
    border-radius: var(--radius-box);
    box-shadow: 0 20px 25px -5px rgba(0,0,0,.1), 0 8px 10px -6px rgba(0,0,0,.1);
    font-size: var(--font-size-sm);
    z-index: 50;
    pointer-events: none;
    position: fixed;
  }

  .tooltip-container > * + * {
    margin-top: 0.25rem;
  }

  .tooltip-header {
    font-weight: 700;
    border-bottom: 1px solid rgba(255,255,255,0.2);
    padding-bottom: 0.25rem;
    margin-bottom: 0.5rem;
  }

  .status-success {
    color: var(--color-success);
  }

  .status-error {
    color: var(--color-error);
  }

  .status-warning {
    color: var(--color-warning);
  }

  .tooltip-meta {
    font-size: var(--font-size-xs);
    opacity: 0.7;
    margin-top: 0.5rem;
  }

  .tooltip-meta-inline {
    font-size: var(--font-size-xs);
    opacity: 0.7;
  }
</style>
