<script lang="ts">
  import type { DjenComunicacaoQuery } from '../lib/djen';
  import { TRIBUNAL_GROUPS } from '../lib/tribunais';

  interface Props {
    filters: DjenComunicacaoQuery;
  }

  let { filters = $bindable() }: Props = $props();
  let showSecondaryFilters = $state(false);

  type DatePreset = 'today' | '7d' | '30d' | 'month';

  const DATE_PRESETS: Array<{ value: DatePreset; label: string }> = [
    { value: 'today', label: 'Hoje' },
    { value: '7d', label: 'Últimos 7 dias' },
    { value: '30d', label: 'Últimos 30 dias' },
    { value: 'month', label: 'Este mês' },
  ];

  function formatLocalDate(d: Date): string {
    // Format as YYYY-MM-DD in the browser's local timezone so presets don't
    // shift by a day when the user is ahead/behind UTC.
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function datePresetRange(preset: DatePreset) {
    const now = new Date();
    const today = formatLocalDate(now);
    const start = new Date(now);

    if (preset === 'today') {
      return { start: today, end: today };
    }
    if (preset === '7d') {
      start.setDate(start.getDate() - 7);
    } else if (preset === '30d') {
      start.setDate(start.getDate() - 30);
    } else if (preset === 'month') {
      start.setDate(1);
    }

    return { start: formatLocalDate(start), end: today };
  }

  function isDatePresetActive(preset: DatePreset) {
    const range = datePresetRange(preset);
    return (
      filters.dataDisponibilizacaoInicio === range.start &&
      filters.dataDisponibilizacaoFim === range.end
    );
  }

  function updateFilters(patch: Partial<DjenComunicacaoQuery>) {
    filters = { ...filters, ...patch, pagina: 1 };
  }

  function setDatePreset(preset: DatePreset) {
    const range = datePresetRange(preset);
    updateFilters({
      dataDisponibilizacaoInicio: range.start,
      dataDisponibilizacaoFim: range.end,
    });
  }

  function clearDates() {
    updateFilters({
      dataDisponibilizacaoInicio: undefined,
      dataDisponibilizacaoFim: undefined,
    });
  }

  function clearAll() {
    filters = { itensPorPagina: 30, pagina: 1 };
  }
</script>

<fieldset class="publication-filters">
  <div class="auto-grid-sm publication-filters__grid">
    <label>
      Tribunal
      <select
        value={filters.siglaTribunal ?? ''}
        onchange={(e) => updateFilters({ siglaTribunal: e.currentTarget.value || undefined })}
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

    <label>
      Data início
      <input
        type="date"
        value={filters.dataDisponibilizacaoInicio ?? ''}
        oninput={(e) =>
          updateFilters({
            dataDisponibilizacaoInicio: e.currentTarget.value || undefined,
          })}
      />
    </label>

    <label>
      Data fim
      <input
        type="date"
        value={filters.dataDisponibilizacaoFim ?? ''}
        oninput={(e) =>
          updateFilters({
            dataDisponibilizacaoFim: e.currentTarget.value || undefined,
          })}
      />
    </label>
  </div>

  <div aria-label="Presets de período mais usados">
    <small>Período:</small>
    {#each DATE_PRESETS as preset (preset.value)}
      <button
        type="button"
        class:contrast={isDatePresetActive(preset.value)}
        class:secondary={!isDatePresetActive(preset.value)}
        class:outline={!isDatePresetActive(preset.value)}
        aria-pressed={isDatePresetActive(preset.value)}
        onclick={() => setDatePreset(preset.value)}
      >{preset.label}</button>
    {/each}
    <button type="button" class="outline" onclick={clearDates}>Limpar datas</button>
  </div>

  <details bind:open={showSecondaryFilters}>
    <summary>Mais filtros</summary>
    <div class="auto-grid-sm">
      <label>
        OAB — número
        <input
          type="text"
          inputmode="numeric"
          pattern="[0-9]*"
          autocomplete="off"
          placeholder="123456"
          value={filters.numeroOab ?? ''}
          oninput={(e) => updateFilters({ numeroOab: e.currentTarget.value || undefined })}
        />
      </label>

      <label>
        OAB — UF
        <input
          type="text"
          autocapitalize="characters"
          autocomplete="off"
          placeholder="SP"
          maxlength="2"
          value={filters.ufOab ?? ''}
          oninput={(e) => updateFilters({ ufOab: e.currentTarget.value.toUpperCase() || undefined })}
        />
      </label>

      <label>
        Nome do advogado
        <input
          type="text"
          autocomplete="off"
          placeholder="Ex.: João da Silva"
          value={filters.nomeAdvogado ?? ''}
          oninput={(e) => updateFilters({ nomeAdvogado: e.currentTarget.value || undefined })}
        />
      </label>

      <label>
        Nome da parte
        <input
          type="text"
          autocomplete="off"
          placeholder="Ex.: Empresa XYZ LTDA"
          value={filters.nomeParte ?? ''}
          oninput={(e) => updateFilters({ nomeParte: e.currentTarget.value || undefined })}
        />
      </label>

      <fieldset>
        <legend>Meio</legend>
        <label>
          <input
            type="radio"
            name="meio"
            checked={filters.meio == null}
            onchange={() => updateFilters({ meio: undefined })}
          /> Todos
        </label>
        <label>
          <input
            type="radio"
            name="meio"
            checked={filters.meio === 'D'}
            onchange={() => updateFilters({ meio: 'D' })}
          /> Diário
        </label>
        <label>
          <input
            type="radio"
            name="meio"
            checked={filters.meio === 'E'}
            onchange={() => updateFilters({ meio: 'E' })}
          /> Edital
        </label>
      </fieldset>

      <fieldset>
        <legend>Itens por página</legend>
        {#each [5, 30, 100] as size (size)}
          <label>
            <input
              type="radio"
              name="itensPorPagina"
              checked={(filters.itensPorPagina ?? 30) === size}
              onchange={() => updateFilters({ itensPorPagina: size })}
            /> {size}
          </label>
        {/each}
      </fieldset>
    </div>
  </details>

  <div>
    <button type="button" class="outline" data-tone="error" onclick={clearAll}>Limpar tudo</button>
  </div>
</fieldset>
