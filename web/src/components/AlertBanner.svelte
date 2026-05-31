<script lang="ts">
  interface Props {
    title: string;
    message: string;
    level?: 'info' | 'success' | 'warning' | 'error';
    /** Override the auto-derived live-region behaviour. By default, error and
     *  warning banners use role="alert" (announces immediately to AT); info and
     *  success banners use role="note" (static, no announcement). */
    live?: boolean;
  }

  let { title, message, level = 'info', live }: Props = $props();
  const isLive = live ?? (level === 'error' || level === 'warning');
</script>

<aside role={isLive ? 'alert' : 'note'} class="alert" data-level={level}>
  <strong>{title}</strong>
  <p>{message}</p>
</aside>
