<script lang="ts">
  import type { SmartParseKind } from '../lib/searchQueryString';

  interface Props {
    value: string;
    hint?: string;
    kind?: SmartParseKind | '';
    placeholder?: string;
    onsubmit?: () => void;
    inputRef?: HTMLInputElement | null;
  }

  let {
    value = $bindable(''),
    hint = '',
    kind = '',
    placeholder = 'OAB, número do processo ou texto livre...',
    onsubmit,
    inputRef = $bindable(null),
  }: Props = $props();

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter' && onsubmit) {
      e.preventDefault();
      onsubmit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      value = '';
    }
  }
</script>

<div class="smart-input">
  <label class="input-wrapper">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="search-icon" aria-hidden="true">
      <path fill-rule="evenodd" d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z" clip-rule="evenodd" />
    </svg>
    <input
      type="search"
      bind:this={inputRef}
      bind:value
      onkeydown={handleKeyDown}
      {placeholder}
      autocomplete="off"
      spellcheck="false"
      enterkeyhint="search"
      aria-label="Buscar publicações"
    />
    <kbd class="kbd-tag">Ctrl</kbd>
    <kbd class="kbd-tag">K</kbd>
    {#if value}
      <button type="button" class="clear-btn" onclick={() => (value = '')} aria-label="Limpar busca">×</button>
    {/if}
  </label>
  {#if hint}
    <div class="hint" data-kind={kind} role="status" aria-live="polite">
      <span class="hint-icon" aria-hidden="true">
        {#if kind === 'oab'}⚖️{:else if kind === 'processo'}📋{:else}🔍{/if}
      </span>
      {hint}
    </div>
  {/if}
</div>
