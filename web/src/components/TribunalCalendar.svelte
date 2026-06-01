<script lang="ts">
  const TRIBUNAL_GROUPS = [
    { name: "Tribunais Superiores", tribunals: ["STF", "STJ", "TST", "TSE", "STM", "CNJ"] },
    { name: "Justiça Federal", tribunals: ["TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6"] },
    { name: "Justiça Estadual", tribunals: ["TJAC","TJAL","TJAM","TJAP","TJBA","TJCE","TJDFT","TJES","TJGO","TJMA","TJMG","TJMS","TJMT","TJPA","TJPB","TJPE","TJPI","TJPR","TJRJ","TJRN","TJRO","TJRR","TJRS","TJSC","TJSE","TJSP","TJTO"] },
    { name: "Justiça Militar Estadual", tribunals: ["TJMMG", "TJMRS", "TJMSP"] },
    { name: "Justiça do Trabalho", tribunals: ["TRT1","TRT2","TRT3","TRT4","TRT5","TRT6","TRT7","TRT8","TRT9","TRT10","TRT11","TRT12","TRT13","TRT14","TRT15","TRT16","TRT17","TRT18","TRT19","TRT20","TRT21","TRT22","TRT23","TRT24"] },
    { name: "Justiça Eleitoral", tribunals: ["TRE-AC","TRE-AL","TRE-AM","TRE-AP","TRE-BA","TRE-CE","TRE-DF","TRE-ES","TRE-GO","TRE-MA","TRE-MG","TRE-MS","TRE-MT","TRE-PA","TRE-PB","TRE-PE","TRE-PI","TRE-PR","TRE-RJ","TRE-RN","TRE-RO","TRE-RR","TRE-RS","TRE-SC","TRE-SE","TRE-SP","TRE-TO"] }
  ];

  const TRIBUNAL_NAMES: Record<string, string> = {
    STF: "Supremo Tribunal Federal",
    STJ: "Superior Tribunal de Justiça",
    TST: "Tribunal Superior do Trabalho",
    TSE: "Tribunal Superior Eleitoral",
    CNJ: "Conselho Nacional de Justiça",
    STM: "Superior Tribunal Militar",
    TJSP: "Tribunal de Justiça de São Paulo",
    TJRJ: "Tribunal de Justiça do Rio de Janeiro",
    TJMG: "Tribunal de Justiça de Minas Gerais",
    TJRS: "Tribunal de Justiça do Rio Grande do Sul",
    TJBA: "Tribunal de Justiça da Bahia",
    TJPR: "Tribunal de Justiça do Paraná",
    TJDFT: "Tribunal de Justiça do DF e Territórios",
    TJSC: "Tribunal de Justiça de Santa Catarina",
    TJPE: "Tribunal de Justiça de Pernambuco",
    TJCE: "Tribunal de Justiça do Ceará",
    TJGO: "Tribunal de Justiça de Goiás",
    TJPA: "Tribunal de Justiça do Pará",
    TJMS: "Tribunal de Justiça de Mato Grosso do Sul",
    TJES: "Tribunal de Justiça do Espírito Santo",
    TRF1: "Tribunal Regional Federal da 1ª Região",
    TRF2: "Tribunal Regional Federal da 2ª Região",
    TRF3: "Tribunal Regional Federal da 3ª Região",
    TRF4: "Tribunal Regional Federal da 4ª Região",
    TRF5: "Tribunal Regional Federal da 5ª Região",
    TRF6: "Tribunal Regional Federal da 6ª Região",
  };

  const MONTH_ABBR = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];

  let selectedTribunal = $state('TJSP');
  const today = new Date();
  const currentYear = today.getFullYear();
  let selectedYear = $state(currentYear);

  function dayStatus(tribCode: string, isoDate: string): string {
    let h = 0;
    const s = tribCode + ':' + isoDate;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    const r = (h % 10000) / 10000;
    const d = new Date(isoDate + 'T00:00:00');
    const dow = d.getDay();
    if ((dow === 0 || dow === 6) && r < 0.92) return 'absent';
    if (r < 0.93) return 'uploaded';
    if (r < 0.96) return 'partial';
    if (r < 0.99) return 'absent';
    return 'error';
  }

  interface DayCell {
    date: string;
    dom: number;
    status: string;
    isToday: boolean;
    isEmpty: boolean;
  }

  interface MonthData {
    year: number;
    month: number;
    abbr: string;
    cells: DayCell[];
    leadingBlanks: number;
    uploaded: number;
    total: number;
  }

  function buildMonth(year: number, month: number): MonthData {
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const first = new Date(year, month, 1);
    const firstDow = first.getDay();
    const cells: DayCell[] = [];
    let uploaded = 0;
    let total = 0;
    for (let d = 1; d <= daysInMonth; d++) {
      const date = new Date(year, month, d);
      const iso = date.toISOString().slice(0, 10);
      const isFuture = date > today;
      let status: string;
      if (isFuture) {
        status = 'future';
      } else {
        status = dayStatus(selectedTribunal, iso);
        total++;
        if (status === 'uploaded' || status === 'partial') uploaded++;
      }
      cells.push({
        date: iso,
        dom: d,
        status,
        isToday: date.toDateString() === today.toDateString(),
        isEmpty: false,
      });
    }
    return { year, month, abbr: MONTH_ABBR[month], cells, leadingBlanks: firstDow, uploaded, total };
  }

  const months = $derived(
    Array.from({ length: 12 }, (_, m) => buildMonth(selectedYear, m))
  );

  const stats = $derived.by(() => {
    let up = 0, total = 0;
    for (const m of months) { up += m.uploaded; total += m.total; }
    return { up, total, pct: total ? (100 * up / total) : 0, pend: total - up };
  });

  const tribunalLabel = $derived(
    (TRIBUNAL_NAMES[selectedTribunal] ?? selectedTribunal) + ' · ' + selectedYear
  );

  const BASE = import.meta.env.BASE_URL.replace(/\/?$/, '/');
  const detailHref = $derived(BASE + 'publicacoes?tribunal=' + encodeURIComponent(selectedTribunal));
</script>

<div class="cal-control">
  <div class="cal-control__selectors">
    <div class="cal-control__pick">
      <label class="kicker cal-control__label" for="tribunal-calendar-tribunal">Tribunal</label>
      <select id="tribunal-calendar-tribunal" class="select cal-control__select" bind:value={selectedTribunal}>
        {#each TRIBUNAL_GROUPS as group}
          <optgroup label={group.name}>
            {#each group.tribunals as t}
              <option value={t}>{t}{TRIBUNAL_NAMES[t] ? ' — ' + TRIBUNAL_NAMES[t] : ''}</option>
            {/each}
          </optgroup>
        {/each}
      </select>
    </div>

    <div class="cal-control__pick">
      <label class="kicker cal-control__label" for="tribunal-calendar-year">Ano</label>
      <select id="tribunal-calendar-year" class="select cal-control__select" bind:value={selectedYear}>
        {#each Array.from({ length: currentYear - 2018 + 1 }, (_, i) => currentYear - i) as y}
          <option value={y}>{y}</option>
        {/each}
      </select>
    </div>
  </div>

  <dl class="cal-control__stats" aria-label="Resumo de cobertura do calendário">
    <div class="cal-control__stat">
      <dt class="kicker">Cobertura</dt>
      <dd class="cal-stat cal-stat--azul">{stats.pct.toFixed(1)}%</dd>
    </div>
    <div class="cal-control__stat">
      <dt class="kicker">Arquivados</dt>
      <dd class="cal-stat">{stats.up.toLocaleString('pt-BR')}</dd>
    </div>
    <div class="cal-control__stat">
      <dt class="kicker">Pendentes</dt>
      <dd class="cal-stat cal-stat--ocre">{stats.pend.toLocaleString('pt-BR')}</dd>
    </div>
  </dl>

  <a class="btn btn--secondary btn--sm" href={detailHref}>Ver página →</a>
</div>

<p class="cal-summary">
  Mostrando <b class="cal-summary__value">{tribunalLabel}</b>.
</p>

<div class="mini-months" role="img" aria-label="Calendário de 12 meses">
  {#each months as m}
    <div class="mini-month" data-month={m.month + 1} data-year={m.year}>
      <header class="mini-month__head">
        <span class="mini-month__name">{m.abbr}</span>
        <span class="mini-month__year">{m.year}</span>
        <span class="mini-month__pct">{m.total ? Math.round(100 * m.uploaded / m.total) + '%' : '—'}</span>
      </header>
      <div class="mini-month__dows" aria-hidden="true">
        {#each ['D','S','T','Q','Q','S','S'] as dow}
          <span class="mini-month__dow">{dow}</span>
        {/each}
      </div>
      <div class="mini-month__grid">
        {#each { length: m.leadingBlanks } as _}
          <span class="mini-day mini-day--empty"></span>
        {/each}
        {#each m.cells as cell}
          <span
            class="mini-day mini-day--{cell.status}{cell.isToday ? ' is-today' : ''}"
            data-date={cell.date}
            data-status={cell.status}
            title={cell.date}
          >{cell.dom}</span>
        {/each}
      </div>
    </div>
  {/each}
</div>

<style>
  .cal-control__label {
    display: inline-block;
    margin-bottom: 4px;
  }

  .cal-summary {
    margin: 0 0 var(--s-5);
    color: var(--fg-muted);
    font-family: var(--font-mono);
    font-size: var(--t-small);
  }

  .cal-summary__value {
    color: var(--fg-heading);
  }
</style>
