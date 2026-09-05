<script lang="ts">
  export type PublicationActionContext = "main" | "reader" | "compact";

  let {
    link,
    processHref,
    activeCopied = null,
    shareContext,
    shareLabel = "Compartilhar",
    copiedLabel = "Copiado!",
    onShare,
    activeReferenceCopied = null,
    onCopyReference,
    showClose = false,
    onClose,
    showReader = false,
    onOpenReader,
    showBack = false,
    onBack,
    showNavigation = false,
    seq,
    totalSeq,
    onNavigate,
    ariaLabel = "Ações da publicação",
  }: {
    link?: string;
    processHref?: string | null;
    activeCopied?: PublicationActionContext | null;
    shareContext: PublicationActionContext;
    shareLabel?: string;
    copiedLabel?: string;
    onShare: (event: MouseEvent, context: PublicationActionContext) => void;
    activeReferenceCopied?: PublicationActionContext | null;
    onCopyReference?: (event: MouseEvent, context: PublicationActionContext) => void;
    showClose?: boolean;
    onClose?: () => void;
    showReader?: boolean;
    onOpenReader?: () => void;
    showBack?: boolean;
    onBack?: () => void;
    showNavigation?: boolean;
    seq?: number;
    totalSeq?: number;
    onNavigate?: (newSeq: number) => void;
    ariaLabel?: string;
  } = $props();
</script>

{#snippet shareIcon()}
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
    <path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
  </svg>
{/snippet}

{#snippet openExternalIcon()}
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
    <path stroke-linecap="round" stroke-linejoin="round" d="M14 3h7m0 0v7m0-7L10 14" />
    <path stroke-linecap="round" stroke-linejoin="round" d="M21 14v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
  </svg>
{/snippet}

<div class="publication-actions" aria-label={ariaLabel}>
  {#if showClose && onClose}
    <button type="button" class="outline secondary" onclick={onClose} title="Fechar detalhes">
      Fechar
    </button>
  {/if}

  {#if showBack && onBack}
    <button type="button" class="outline secondary" onclick={onBack} title="Sair do Modo Leitura">
      Voltar
    </button>
  {/if}

  {#if showReader && onOpenReader}
    <button type="button" class="outline" onclick={onOpenReader} title="Abrir Modo Leitura">
      Modo Leitura
    </button>
  {/if}

  {#if processHref}
    <a class="outline" href={processHref}>
      Abrir dossiê
    </a>
  {/if}

  {#if link}
    <a class="outline secondary" href={link} target="_blank" rel="noopener noreferrer">
      {@render openExternalIcon()}
      Inteiro teor
    </a>
  {/if}

  {#if link && onCopyReference}
    <button
      type="button"
      class="outline secondary"
      onclick={(event: MouseEvent) => onCopyReference(event, shareContext)}
      title="Copiar referência verificável em texto puro"
    >
      {activeReferenceCopied === shareContext ? 'Referência copiada' : 'Copiar referência'}
    </button>
  {/if}

  <div class="nav-actions" aria-label="Ações de navegação">
    {#if showNavigation && onNavigate && seq != null}
      <button
        type="button"
        class="outline secondary"
        onclick={() => onNavigate?.(seq - 1)}
        disabled={seq <= 1}
      >
        Anterior
      </button>
      <button
        type="button"
        class="outline secondary"
        onclick={() => onNavigate?.(seq + 1)}
        disabled={totalSeq != null && seq >= totalSeq}
      >
        Próxima
      </button>
    {/if}

    <button
      type="button"
      class="outline secondary"
      onclick={(event: MouseEvent) => onShare(event, shareContext)}
      title="Copiar link"
    >
      {@render shareIcon()}
      {activeCopied === shareContext ? copiedLabel : shareLabel}
    </button>
  </div>
</div>
