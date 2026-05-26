<script lang="ts">
interface Props {
  complete: number;
  partial: number;
  low: number;
  missing: number;
}

const { complete, partial, low, missing }: Props = $props();

const cards = [
  { value: complete, label: '>90%' },
  { value: partial,  label: '50–89%' },
  { value: low,      label: '<50%' },
  { value: missing,  label: 'Sem dados' },
];
</script>

<div class="summary-grid">
  {#each cards as card}
    <article class="summary-card">
      <strong class="summary-value">{card.value}</strong>
      <small>{card.label}</small>
    </article>
  {/each}
</div>

<style>
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 8rem), 1fr));
    gap: 1rem;
    margin: 1rem 0;
  }

  .summary-card {
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    padding: var(--space-sm);
  }

  .summary-value {
    font-size: var(--font-size-xl);
    font-weight: 700;
    font-family: var(--font-mono);
    line-height: 1;
  }
</style>
