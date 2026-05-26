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

  const STATUS_MAP: Record<string, { text: string; tone: string }> = {
    collected: { text: '\u2705 Collected & Uploaded', tone: 'success' },
    missing: { text: '\u274C Missing', tone: 'error' },
    partial: { text: '\u26A0\uFE0F Partial', tone: 'warning' },
    outside: { text: 'Outside active range', tone: '' },
  };

  const DEFAULT_STATUS = { text: '', tone: '' };

  let { cellData, position }: CellTooltipProps = $props();

  let tooltipEl = $state<HTMLDivElement | undefined>(undefined);
  let style = $state<{ top: number; left: number; opacity: number }>({ top: -9999, left: -9999, opacity: 0 });

  const mapped = $derived(STATUS_MAP[cellData.status] ?? { ...DEFAULT_STATUS, text: cellData.status });
  const statusText = $derived(mapped.text);
  const statusTone = $derived(mapped.tone);

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
  <article
    bind:this={tooltipEl}
    role="tooltip"
    style="position:fixed; top: {style.top}px; left: {style.left}px; opacity: {style.opacity};"
  >
    <header>
      {cellData.date}
    </header>
    <div data-tone={statusTone || undefined}>
      {statusText}
    </div>

    {#if cellData.uploadedAt}
      <footer>
        <small><span>Uploaded:</span>{' '}<span>{new Date(cellData.uploadedAt).toLocaleString('pt-BR')}</span></small>
        {#if cellData.sizeMb}
          <small><span>Size:</span>{' '}<span>{cellData.sizeMb.toFixed(2)} MB</span></small>
        {/if}
      </footer>
    {:else if cellData.sizeMb}
      <footer>
        <small><span>Size:</span>{' '}<span>{cellData.sizeMb.toFixed(2)} MB</span></small>
      </footer>
    {/if}
  </article>
{/if}
