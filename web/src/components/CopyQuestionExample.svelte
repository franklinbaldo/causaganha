<script lang="ts">
  interface Props {
    question: string;
  }

  let { question }: Props = $props();

  type CopyState = 'idle' | 'success' | 'error';
  let copyState = $state<CopyState>('idle');
  let feedbackTimeout: ReturnType<typeof setTimeout> | null = null;

  const feedbackText = $derived(
    copyState === 'success'
      ? 'Pergunta copiada.'
      : copyState === 'error'
        ? 'Não foi possível copiar automaticamente. Selecione e copie o texto manualmente.'
        : ''
  );

  async function copyQuestion() {
    if (feedbackTimeout) clearTimeout(feedbackTimeout);

    if (!navigator.clipboard?.writeText) {
      copyState = 'error';
    } else {
      try {
        await navigator.clipboard.writeText(question);
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

<div class="example-question">
  <p class="example-question__text">{question}</p>
  <div class="example-question__actions">
    <button type="button" class="outline secondary" onclick={copyQuestion}>
      Copiar pergunta
    </button>
    <p class="feedback" role="status" aria-live="polite">{feedbackText}</p>
  </div>
</div>

<style>
  .example-question { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border); }
  .example-question__text { margin: 0 0 .6rem; font-size: .92rem; line-height: 1.5; color: var(--fg); }
  .example-question__actions { display: flex; flex-wrap: wrap; align-items: center; gap: .75rem; }
  .feedback { margin: 0; font-family: var(--font-mono); font-size: .78rem; color: var(--fg-muted); min-height: 1.2em; }
</style>
