<script lang="ts">
  import { setQueryClientContext } from '@tanstack/svelte-query';
  import { SvelteQueryDevtools } from '@tanstack/svelte-query-devtools';
  import { getQueryClient } from '../lib/queryClient';
  import type { Snippet } from 'svelte';

  let { children }: { children: Snippet } = $props();

  // Set the QueryClient context for this island tree
  setQueryClientContext(getQueryClient());
</script>

{@render children()}
{#if import.meta.env.DEV}
  <SvelteQueryDevtools initialIsOpen={false} />
{/if}
