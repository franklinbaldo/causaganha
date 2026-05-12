<script lang="ts">
  interface Props {
    limit: number | null;
    remaining: number | null;
    usedFallback?: boolean;
  }

  let { limit, remaining, usedFallback = false }: Props = $props();

  const tone = $derived.by(() => {
    if (remaining == null) return 'idle';
    if (remaining < 3) return 'danger';
    if (remaining < 10) return 'warning';
    return 'ok';
  });

  const label = $derived.by(() => {
    if (remaining == null || limit == null) return 'Cota DJEN: —';
    return `${remaining} / ${limit} requisições restantes`;
  });
</script>

<div class="rate-limit-badge {tone}" title="Janela de rate limit da API do DJEN. Ao zerar, aguarde 1 minuto.">
  <span class="dot" aria-hidden="true"></span>
  <span class="label">{label}</span>
  {#if usedFallback}
    <span class="fallback-tag" title="Resposta vinda do proxy de fallback">proxy</span>
  {/if}
</div>

<style>
  .rate-limit-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.6rem;
    border-radius: 999px;
    font-size: var(--font-size-xs, 0.75rem);
    border: 1px solid var(--color-base-300);
    background: var(--color-base-100);
    color: var(--color-base-content, inherit);
  }

  .dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 999px;
    background: currentColor;
    opacity: 0.7;
  }

  .rate-limit-badge.idle {
    opacity: 0.6;
  }

  .rate-limit-badge.ok {
    border-color: var(--color-success);
    color: var(--color-success);
  }

  .rate-limit-badge.warning {
    border-color: var(--color-warning);
    /* --color-warning is a light gold; mix toward base-content so the small
       badge text clears WCAG AA contrast on the light theme background. */
    color: color-mix(in srgb, var(--color-warning) 50%, var(--color-base-content));
  }

  .rate-limit-badge.danger {
    border-color: var(--color-error);
    color: var(--color-error);
  }

  .fallback-tag {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.1rem 0.35rem;
    border-radius: var(--radius-sm, 0.25rem);
    background: rgba(148, 163, 184, 0.2);
    color: var(--color-base-content, inherit);
  }
</style>
