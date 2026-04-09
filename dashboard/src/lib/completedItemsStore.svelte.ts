/**
 * Shared singleton store for completed-items.json from Internet Archive.
 * Fetches once and shares across TribunalCoverageHeatmap, LatencyHeatmap, etc.
 * Uses Svelte 5 module-level $state (universal reactivity).
 */

let _data = $state<Record<string, any> | null>(null);
let _loading = $state(true);
let _error = $state<string | null>(null);
let _initialized = false;

function ensureLoaded() {
  if (_initialized || typeof window === 'undefined') return;
  _initialized = true;

  fetch(`https://archive.org/download/causaganha-catalog/completed-items.json?t=${Date.now()}`)
    .then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then(json => {
      _data = json.completed_items || {};
      _error = null;
    })
    .catch(e => {
      _error = e instanceof Error ? e.message : String(e);
      console.error('Failed to fetch catalog completed-items.json:', e);
    })
    .finally(() => {
      _loading = false;
    });
}

export const completedItemsStore = {
  get data()    { return _data; },
  get loading() { return _loading; },
  get error()   { return _error; },
  load: ensureLoaded,
};
