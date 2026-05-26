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
