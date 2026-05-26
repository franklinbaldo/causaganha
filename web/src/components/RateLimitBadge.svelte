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
