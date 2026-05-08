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

<style>
  .smart-input {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .input-wrapper {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.75rem 1rem;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box, 0.75rem);
    background: var(--color-base-100);
    box-shadow: var(--shadow-sm);
    transition: border-color 120ms ease, box-shadow 120ms ease;
  }

  .input-wrapper:focus-within {
    border-color: var(--color-primary, #3b82f6);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
  }

  .search-icon {
    width: 1.1rem;
    height: 1.1rem;
    opacity: 0.55;
    flex-shrink: 0;
  }

  input {
    flex: 1;
    border: none;
    background: transparent;
    outline: none;
    font-size: var(--font-size-base, 1rem);
    color: inherit;
  }

  .kbd-tag {
    display: none;
    font-family: var(--font-mono);
    font-size: var(--font-size-xs);
    padding: 0.125rem 0.375rem;
    border-radius: var(--radius-btn);
    background: var(--color-base-200);
    border: none;
    box-shadow: none;
  }

  @media (min-width: 640px) {
    .kbd-tag {
      display: inline-flex;
    }
  }

  .clear-btn {
    border: none;
    background: transparent;
    font-size: 1.25rem;
    line-height: 1;
    padding: 0 0.25rem;
    cursor: pointer;
    color: inherit;
    opacity: 0.55;
  }

  .clear-btn:hover {
    opacity: 1;
  }

  .clear-btn:focus-visible {
    opacity: 1;
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
    border-radius: var(--radius-sm, 0.25rem);
  }

  .hint {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: var(--font-size-xs, 0.75rem);
    padding: 0.3rem 0.6rem;
    border-radius: var(--radius-sm, 0.25rem);
    background: var(--color-base-200);
    border-left: 3px solid var(--color-base-300);
    transition: border-color var(--transition-base, 200ms ease);
  }

  .hint[data-kind='oab'] {
    border-left-color: var(--color-accent);
  }

  .hint[data-kind='processo'] {
    border-left-color: var(--color-info);
  }

  .hint-icon {
    font-size: 0.8rem;
    line-height: 1;
  }
</style>
