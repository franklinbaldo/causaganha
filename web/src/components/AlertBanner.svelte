<script lang="ts">
  interface Props {
    title: string;
    message: string;
    level?: 'info' | 'success' | 'warning' | 'error';
  }

  let { title, message, level = 'info' }: Props = $props();
</script>

<aside role="alert" class="alert" data-level={level}>
  <strong>{title}</strong>
  <p>{message}</p>
</aside>

<style>
  .alert {
    --_c: var(--color-info);
    padding: 1rem;
    border-radius: var(--pico-border-radius);
    border: 1px solid var(--_c);
    background: color-mix(in srgb, var(--_c) 12%, transparent);
    color: var(--_c);
    margin-block: 1rem;
  }

  .alert[data-level='success'] { --_c: var(--color-success); }
  .alert[data-level='warning'] { --_c: var(--color-warning); }
  .alert[data-level='error']   { --_c: var(--color-error); }

  p {
    font-size: var(--font-size-sm);
    margin: 0.25rem 0 0;
  }
</style>
