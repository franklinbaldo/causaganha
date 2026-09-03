<script lang="ts">
  interface Props {
    config: string;
    label: string;
  }

  let { config, label }: Props = $props();

  type CopyState = 'idle' | 'success' | 'error';
  let copyState = $state<CopyState>('idle');
  let feedbackTimeout: ReturnType<typeof setTimeout> | null = null;

  const feedbackText = $derived(
    copyState === 'success'
      ? 'Configuração copiada.'
      : copyState === 'error'
        ? 'Não foi possível copiar automaticamente. Selecione e copie o texto manualmente.'
        : ''
  );

  async function copyConfig() {
    if (feedbackTimeout) clearTimeout(feedbackTimeout);

    if (!navigator.clipboard?.writeText) {
      copyState = 'error';
    } else {
      try {
        await navigator.clipboard.writeText(config);
        copyState = 'success';
      } catch {
        copyState = 'error';
      }
    }

    feedbackTimeout = setTimeout(() => {
      copyState = 'idle';
      feedbackTimeout = null;
    }, 2500);
  }
</script>

<div class="config-card">
  <div class="config-card__head">
    <span>Configuração genérica</span>
    <span>{label}</span>
  </div>
  <pre><code>{config}</code></pre>
  <div class="config-card__actions">
    <button type="button" class="outline secondary" onclick={copyConfig}>
      Copiar configuração
    </button>
    <p class="feedback" role="status" aria-live="polite">{feedbackText}</p>
  </div>
</div>

<style>
  .config-card { min-width: 0; border: 1px solid var(--border); }
  .config-card__head { display: flex; justify-content: space-between; gap: 1rem; padding: .7rem .9rem; border-bottom: 1px solid var(--border); font-family: var(--font-mono); font-size: .75rem; color: var(--fg-muted); }
  pre { margin: 0; padding: 1rem; overflow-x: auto; font-size: .82rem; line-height: 1.55; }
  code { font-family: var(--font-mono); }
  .config-card__actions { display: flex; flex-wrap: wrap; align-items: center; gap: .75rem; padding: .7rem .9rem; border-top: 1px solid var(--border); }
  .feedback { margin: 0; font-family: var(--font-mono); font-size: .78rem; color: var(--fg-muted); min-height: 1.2em; }
</style>
