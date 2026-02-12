import { useState } from 'preact/compat';

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'success', label: 'Online' },
  { id: 'error', label: 'Error' },
  { id: 'absent', label: 'Offline' },
];

export function TribunalFilter({ counts: initialCounts }) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  function applyFilter(searchVal, filterVal) {
    const cards = document.querySelectorAll('#tribunal-cards [data-name]');
    const countEl = document.getElementById('tribunal-count');
    const emptyEl = document.getElementById('tribunal-empty');
    const gridEl = document.getElementById('tribunal-cards');
    const lowerSearch = searchVal.toLowerCase();
    let visible = 0;

    cards.forEach(card => {
      const name = card.getAttribute('data-name');
      const status = card.getAttribute('data-status');
      const matchesSearch = !lowerSearch || name.includes(lowerSearch);
      const matchesFilter = filterVal === 'all' || status === filterVal;
      const show = matchesSearch && matchesFilter;
      card.classList.toggle('hidden', !show);
      if (show) visible++;
    });

    if (countEl) countEl.textContent = `${visible} of ${cards.length} courts`;
    if (emptyEl) emptyEl.classList.toggle('hidden', visible > 0);
    if (emptyEl && visible === 0) emptyEl.classList.add('flex');
    if (emptyEl && visible > 0) emptyEl.classList.remove('flex');
    if (gridEl) gridEl.classList.toggle('hidden', visible === 0);
  }

  function onSearch(e) {
    const val = e.target.value;
    setSearch(val);
    applyFilter(val, filter);
  }

  function onFilter(id) {
    setFilter(id);
    applyFilter(search, id);
  }

  function clearSearch() {
    setSearch('');
    applyFilter('', filter);
  }

  function resetAll() {
    setSearch('');
    setFilter('all');
    applyFilter('', 'all');
  }

  // Wire up the empty-state buttons in the static HTML
  if (typeof document !== 'undefined') {
    const clearBtn = document.getElementById('tribunal-clear-search');
    const resetBtn = document.getElementById('tribunal-reset-all');
    if (clearBtn) clearBtn.onclick = clearSearch;
    if (resetBtn) resetBtn.onclick = resetAll;
  }

  return (
    <div class="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
      {/* Search */}
      <div class="relative group w-full sm:w-64">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-content-tertiary group-focus-within:text-accent transition-colors" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <path d="m21 21-4.3-4.3"></path>
        </svg>
        <input
          type="text"
          placeholder="Search courts..."
          value={search}
          onInput={onSearch}
          class="w-full bg-surface border border-border rounded-lg px-9 py-2 text-sm text-content focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-all placeholder:text-content-tertiary"
          aria-label="Search tribunals"
        />
        {search && (
          <button
            onClick={clearSearch}
            class="absolute right-3 top-1/2 -translate-y-1/2 text-content-tertiary hover:text-content"
          >
            <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="15" y1="9" x2="9" y2="15"></line>
              <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
          </button>
        )}
      </div>

      {/* Filter Pills */}
      <div class="flex bg-surface border border-border rounded-lg p-1 gap-0.5">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => onFilter(f.id)}
            class={`px-3 py-1.5 text-xs font-medium transition-colors rounded-md whitespace-nowrap flex-1 text-center ${
              filter === f.id
                ? 'bg-accent text-white shadow-sm'
                : 'text-content-secondary hover:text-content hover:bg-surface-overlay'
            }`}
            aria-pressed={filter === f.id}
          >
            {f.label}
            {initialCounts && (
              <span class="ml-1 opacity-60">{initialCounts[f.id]}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
