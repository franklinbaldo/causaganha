<script lang="ts">
  interface Props {
    title: string;
    message: string;
    level?: 'info' | 'success' | 'warning' | 'error';
    /** Set to true only for urgent, dynamically injected alerts (e.g. form errors).
     *  Static informational banners should leave this false to avoid spamming AT. */
    live?: boolean;
  }

  let { title, message, level = 'info', live = false }: Props = $props();
</script>

<aside role={live ? 'alert' : 'note'} class="alert" data-level={level}>
  <strong>{title}</strong>
  <p>{message}</p>
</aside>
