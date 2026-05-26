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

<div class="auto-grid">
  {#each cards as card}
    <article>
      <strong class="stat-value">{card.value}</strong>
      <small>{card.label}</small>
    </article>
  {/each}
</div>
