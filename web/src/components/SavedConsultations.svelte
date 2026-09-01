<script lang="ts">
  import { onMount } from 'svelte';
  import { formatCnj } from '../lib/processoCnj';
  import {
    SAVED_CONSULTATIONS_STORAGE_KEY,
    parseSavedConsultations,
    removeSavedConsultation,
    renameSavedConsultation,
    saveProcessConsultation,
    serializeSavedConsultations,
    type SavedConsultation,
  } from '../lib/savedConsultations';

  const BASE = import.meta.env.BASE_URL.endsWith('/')
    ? import.meta.env.BASE_URL
    : `${import.meta.env.BASE_URL}/`;

  let items = $state<SavedConsultation[]>([]);
  let cnj = $state('');
  let label = $state('');
  let error = $state<string | null>(null);
  let notice = $state<string | null>(null);
  let ready = $state(false);

  function persist(next: SavedConsultation[]) {
    items = next;
    localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(next));
  }

  function addProcess(event: SubmitEvent) {
    event.preventDefault();
    error = null;
    notice = null;
    try {
      const next = saveProcessConsultation(items, cnj, label);
      persist(next);
      const saved = next.find((item) => item.cnj === cnj.replace(/\D/g, ''));
      notice = saved ? `${saved.label} salvo neste navegador.` : 'Processo salvo neste navegador.';
      cnj = '';
      label = '';
    } catch {
      error = 'CNJ inválido. Use os 20 dígitos, com ou sem máscara.';
    }
  }

  function removeItem(id: string) {
    persist(removeSavedConsultation(items, id));
    notice = 'Consulta removida.';
  }

  function renameItem(item: SavedConsultation) {
    const nextLabel = window.prompt('Nome desta consulta', item.label);
    if (nextLabel === null) return;
    persist(renameSavedConsultation(items, item.id, nextLabel));
  }

  onMount(() => {
    items = parseSavedConsultations(localStorage.getItem(SAVED_CONSULTATIONS_STORAGE_KEY));
    ready = true;
  });
</script>

<section class="saved-consultations" aria-labelledby="saved-consultations-title">
  <div class="saved-consultations__intro">
    <span class="kicker">Uso recorrente</span>
    <h2 id="saved-consultations-title">Seus processos, <em>neste navegador.</em></h2>
    <p>
      Guarde os CNJs que você consulta com frequência. A lista fica somente neste dispositivo:
      não exige conta, não é enviada ao CausaGanha e desaparece se você limpar os dados locais do navegador.
    </p>
  </div>

  <form class="saved-consultations__form" onsubmit={addProcess}>
    <label for="saved-cnj">Adicionar processo</label>
    <div class="saved-consultations__form-grid">
      <input
        id="saved-cnj"
        bind:value={cnj}
        placeholder="0000001-02.2024.8.22.0001"
        autocomplete="off"
        spellcheck="false"
        aria-describedby="saved-cnj-hint"
      />
      <input
        bind:value={label}
        placeholder="Apelido opcional"
        aria-label="Apelido opcional da consulta"
      />
      <button type="submit">Salvar processo</button>
    </div>
    <small id="saved-cnj-hint" class="meta-text">Você pode usar o CNJ com ou sem pontuação.</small>
  </form>

  {#if error}
    <aside role="alert" class="alert" data-level="warning"><p>{error}</p></aside>
  {/if}
  {#if notice}
    <p role="status" class="meta-text">{notice}</p>
  {/if}

  {#if !ready}
    <p aria-busy="true">Carregando consultas salvas…</p>
  {:else if items.length === 0}
    <article class="empty-state">
      <h3>Nenhum processo salvo ainda</h3>
      <p>Adicione um CNJ acima. Depois, um clique reabre o dossiê já com o número preenchido.</p>
    </article>
  {:else}
    <ol class="saved-consultations__list" aria-label="Processos salvos">
      {#each items as item}
        <li>
          <div>
            <strong>{item.label}</strong>
            <code>{formatCnj(item.cnj)}</code>
          </div>
          <div class="saved-consultations__actions">
            <a class="button" href={`${BASE}processo?cnj=${encodeURIComponent(formatCnj(item.cnj))}`}>
              Abrir dossiê
            </a>
            <button type="button" class="outline secondary" onclick={() => renameItem(item)}>Renomear</button>
            <button type="button" class="outline secondary" onclick={() => removeItem(item.id)}>Remover</button>
          </div>
        </li>
      {/each}
    </ol>
  {/if}
</section>

<style>
  .saved-consultations {
    display: grid;
    gap: var(--s-6, 1.5rem);
  }

  .saved-consultations__intro {
    max-width: 52rem;
  }

  .saved-consultations__intro h2 {
    margin-top: var(--s-2, 0.5rem);
  }

  .saved-consultations__form {
    padding: var(--s-5, 1.25rem);
    border: 1px solid var(--border);
    background: var(--papel-20, var(--color-surface));
  }

  .saved-consultations__form-grid {
    display: grid;
    grid-template-columns: minmax(16rem, 2fr) minmax(12rem, 1fr) auto;
    gap: var(--s-2, 0.5rem);
    margin-top: var(--s-2, 0.5rem);
  }

  .saved-consultations__list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    gap: var(--s-3, 0.75rem);
  }

  .saved-consultations__list li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--s-4, 1rem);
    padding: var(--s-4, 1rem);
    border: 1px solid var(--border);
    background: var(--papel-00, var(--color-canvas));
  }

  .saved-consultations__list li > div:first-child {
    display: grid;
    gap: 0.25rem;
  }

  .saved-consultations__actions {
    display: flex;
    gap: 0.45rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  @media (max-width: 48rem) {
    .saved-consultations__form-grid {
      grid-template-columns: 1fr;
    }

    .saved-consultations__list li {
      align-items: stretch;
      flex-direction: column;
    }

    .saved-consultations__actions {
      justify-content: flex-start;
    }
  }
</style>
