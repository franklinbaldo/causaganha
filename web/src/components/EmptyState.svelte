<script lang="ts">
  interface Props {
    title: string;
    message: string;
    actionHref?: string;
    actionLabel?: string;
  }

  let { title, message, actionHref, actionLabel }: Props = $props();
</script>

<div class="card">
  <div class="card-body">
    <h3 class="card-heading">{title}</h3>
    <p class="card-message">{message}</p>
    {#if actionHref && actionLabel}
      <div class="card-actions">
        <a href={actionHref} class="btn btn-primary">{actionLabel}</a>
      </div>
    {/if}
  </div>
</div>

<style>
  .card-heading {
    font-size: 1.125rem;
    font-weight: 600;
  }

  .card-message {
    opacity: 0.7;
  }

  .card-actions {
    display: flex;
    justify-content: center;
    margin-top: 0.5rem;
  }
</style>
