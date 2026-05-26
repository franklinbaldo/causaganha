<script lang="ts">
  interface Props {
    title: string;
    message: string;
    actionHref?: string;
    actionLabel?: string;
  }

  let { title, message, actionHref, actionLabel }: Props = $props();
</script>

<article class="empty-state">
  <h3>{title}</h3>
  <p>{message}</p>
  {#if actionHref && actionLabel}
    <a href={actionHref} role="button">{actionLabel}</a>
  {/if}
</article>

<style>
  .empty-state {
    text-align: center;
  }
</style>
