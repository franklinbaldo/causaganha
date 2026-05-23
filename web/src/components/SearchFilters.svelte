<script lang="ts">
  import type { DjenComunicacaoQuery } from '../lib/djen';
  import { TRIBUNAL_GROUPS } from '../lib/tribunais';

  interface Props {
    filters: DjenComunicacaoQuery;
  }

  let { filters = $bindable() }: Props = $props();

  function formatLocalDate(d: Date): string {
    // Format as YYYY-MM-DD in the browser's local timezone so presets don't
    // shift by a day when the user is ahead/behind UTC.
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function setDatePreset(preset: 'today' | '7d' | '30d' | 'month') {
    const now = new Date();
    const today = formatLocalDate(now);
    const start = new Date(now);

    if (preset === 'today') {
      filters = { ...filters, dataDisponibilizacaoInicio: today, dataDisponibilizacaoFim: today };
      return;
    }
    if (preset === '7d') {
      start.setDate(start.getDate() - 7);
    } else if (preset === '30d') {
      start.setDate(start.getDate() - 30);
    } else if (preset === 'month') {
      start.setDate(1);
    }
    filters = {
      ...filters,
      dataDisponibilizacaoInicio: formatLocalDate(start),
      dataDisponibilizacaoFim: today,
    };
  }

  function clearDates() {
    filters = {
      ...filters,
      dataDisponibilizacaoInicio: undefined,
      dataDisponibilizacaoFim: undefined,
    };
  }

  function clearAll() {
    filters = { itensPorPagina: filters.itensPorPagina, pagina: 1 };
  }
</script>

<div class="filters-panel">
  <div class="filter-grid">
    <label class="field">
      <span>Tribunal</span>
      <select
        value={filters.siglaTribunal ?? ''}
        onchange={(e) => (filters = { ...filters, siglaTribunal: (e.currentTarget.value || undefined) })}
      >
        <option value="">Todos</option>
        {#each TRIBUNAL_GROUPS as group (group.name)}
          <optgroup label={group.name}>
            {#each group.tribunals as t (t)}
              <option value={t}>{t}</option>
            {/each}
          </optgroup>
        {/each}
      </select>
    </label>

    <label class="field">
      <span>OAB — número</span>
      <input
        type="text"
        inputmode="numeric"
        pattern="[0-9]*"
        autocomplete="off"
        placeholder="123456"
        value={filters.numeroOab ?? ''}
        oninput={(e) => (filters = { ...filters, numeroOab: e.currentTarget.value || undefined })}
      />
    </label>

    <label class="field">
      <span>OAB — UF</span>
      <input
        type="text"
        autocapitalize="characters"
        autocomplete="off"
        placeholder="SP"
        maxlength="2"
        value={filters.ufOab ?? ''}
        oninput={(e) => (filters = { ...filters, ufOab: e.currentTarget.value.toUpperCase() || undefined })}
      />
    </label>

    <label class="field">
      <span>Nome do advogado</span>
      <input
        type="text"
        autocomplete="off"
        placeholder="Ex.: João da Silva"
        value={filters.nomeAdvogado ?? ''}
        oninput={(e) => (filters = { ...filters, nomeAdvogado: e.currentTarget.value || undefined })}
      />
    </label>

    <label class="field">
      <span>Nome da parte</span>
      <input
        type="text"
        autocomplete="off"
        placeholder="Ex.: Empresa XYZ LTDA"
        value={filters.nomeParte ?? ''}
        oninput={(e) => (filters = { ...filters, nomeParte: e.currentTarget.value || undefined })}
      />
    </label>

    <label class="field">
      <span>Data início</span>
      <input
        type="date"
        value={filters.dataDisponibilizacaoInicio ?? ''}
        oninput={(e) =>
          (filters = {
            ...filters,
            dataDisponibilizacaoInicio: e.currentTarget.value || undefined,
          })}
      />
    </label>

    <label class="field">
      <span>Data fim</span>
      <input
        type="date"
        value={filters.dataDisponibilizacaoFim ?? ''}
        oninput={(e) =>
          (filters = {
            ...filters,
            dataDisponibilizacaoFim: e.currentTarget.value || undefined,
          })}
      />
    </label>

    <div class="field">
      <span>Meio</span>
      <div class="radio-row">
        <label>
          <input
            type="radio"
            name="meio"
            checked={filters.meio == null}
            onchange={() => (filters = { ...filters, meio: undefined })}
          /> Todos
        </label>
        <label>
          <input
            type="radio"
            name="meio"
            checked={filters.meio === 'D'}
            onchange={() => (filters = { ...filters, meio: 'D' })}
          /> Diário
        </label>
        <label>
          <input
            type="radio"
            name="meio"
            checked={filters.meio === 'E'}
            onchange={() => (filters = { ...filters, meio: 'E' })}
          /> Edital
        </label>
      </div>
    </div>

    <div class="field">
      <span>Itens por página</span>
      <div class="radio-row">
        {#each [5, 30, 100] as size (size)}
          <label>
            <input
              type="radio"
              name="itensPorPagina"
              checked={(filters.itensPorPagina ?? 30) === size}
              onchange={() => (filters = { ...filters, itensPorPagina: size, pagina: 1 })}
            /> {size}
          </label>
        {/each}
      </div>
    </div>
  </div>

  <div class="presets-row">
    <span class="presets-label">Período:</span>
    <button type="button" onclick={() => setDatePreset('today')}>Hoje</button>
    <button type="button" onclick={() => setDatePreset('7d')}>7 dias</button>
    <button type="button" onclick={() => setDatePreset('30d')}>30 dias</button>
    <button type="button" onclick={() => setDatePreset('month')}>Este mês</button>
    <button type="button" class="ghost" onclick={clearDates}>Limpar datas</button>
    <button type="button" class="ghost danger" onclick={clearAll}>Limpar tudo</button>
  </div>
</div>

<style>
  .filters-panel {
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box, 0.75rem);
    background: var(--color-base-100);
    padding: 1rem 1.25rem;
    margin-top: 0.75rem;
  }

  .filter-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.85rem;
  }

  @media (min-width: 640px) {
    .filter-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (min-width: 960px) {
    .filter-grid {
      grid-template-columns: repeat(3, 1fr);
    }
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: var(--font-size-sm, 0.875rem);
  }

  .field > span {
    font-weight: 600;
    opacity: 0.75;
  }

  .field input,
  .field select {
    padding: 0.5rem 0.65rem;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-sm, 0.375rem);
    background: var(--color-base-100);
    color: inherit;
    font-size: var(--font-size-sm, 0.875rem);
  }

  .field input:focus,
  .field select:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 15%, transparent);
  }

  .radio-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    padding: 0.35rem 0;
  }

  .radio-row label {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    cursor: pointer;
  }

  .presets-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-items: center;
    margin-top: 1rem;
    padding-top: 0.85rem;
    border-top: 1px dashed var(--color-base-300);
  }

  .presets-label {
    font-size: var(--font-size-sm, 0.875rem);
    opacity: 0.7;
    margin-right: 0.25rem;
  }

  .presets-row button {
    padding: 0.35rem 0.75rem;
    border: 1px solid var(--color-base-300);
    border-radius: 999px;
    background: var(--color-base-100);
    color: inherit;
    font-size: var(--font-size-xs, 0.75rem);
    cursor: pointer;
    transition: all 120ms ease;
  }

  .presets-row button:hover,
  .presets-row button:focus-visible {
    border-color: var(--color-primary);
    color: var(--color-primary);
    outline: none;
  }

  .presets-row button:focus-visible {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 25%, transparent);
  }

  .presets-row .ghost {
    background: transparent;
    opacity: 0.75;
  }

  .presets-row .ghost.danger:hover,
  .presets-row .ghost.danger:focus-visible {
    color: var(--color-error);
    border-color: var(--color-error);
  }

  .presets-row .ghost.danger:focus-visible {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-error) 25%, transparent);
  }

  @media (pointer: coarse) {
    .presets-row button {
      min-height: 44px;
    }
  }
</style>
