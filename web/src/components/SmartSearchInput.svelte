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

<form class="smart-search" role="search" onsubmit={(e) => { e.preventDefault(); onsubmit?.(); }}>
  <div class="smart-search__field">
    <label class="smart-search__label" for="publication-smart-search">Buscar publicações</label>
    <svg class="smart-search__icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path fill-rule="evenodd" d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z" clip-rule="evenodd" />
    </svg>
    <input
      id="publication-smart-search"
      data-global-search
      type="search"
      bind:this={inputRef}
      bind:value
      onkeydown={handleKeyDown}
      {placeholder}
      autocomplete="off"
      spellcheck="false"
      enterkeyhint="search"
    />
    {#if value}
      <button type="reset" class="smart-search__clear secondary outline" onclick={() => (value = '')} aria-label="Limpar busca">×</button>
    {/if}
  </div>
  <span class="smart-search__shortcut search-shortcut-hint" aria-hidden="true"><kbd>Ctrl</kbd><kbd>K</kbd></span>
  {#if hint}
    <small class="smart-search__hint" data-kind={kind} role="status" aria-live="polite">{hint}</small>
  {/if}
</form>

<style>
  .smart-search {
    display: grid;
    gap: 0.5rem;
  }

  .smart-search__field {
    position: relative;
    display: flex;
    align-items: center;
  }

  .smart-search__label {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .smart-search__icon {
    position: absolute;
    inset-inline-start: 1rem;
    inline-size: 1rem;
    block-size: 1rem;
    flex: 0 0 auto;
    color: var(--fg-muted, var(--color-content-tertiary));
    pointer-events: none;
  }

  .smart-search__field :global(input[type='search']) {
    inline-size: 100%;
    padding-inline-start: 2.75rem;
    padding-inline-end: 3rem;
  }

  .smart-search__clear {
    position: absolute;
    inset-inline-end: 0.5rem;
    inline-size: 2rem;
    block-size: 2rem;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .smart-search__shortcut {
    justify-self: start;
  }

  .smart-search__hint {
    color: var(--fg-muted, var(--color-content-tertiary));
  }
</style>
