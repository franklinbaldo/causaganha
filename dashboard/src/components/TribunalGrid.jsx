import { useState } from 'react';
import clsx from 'clsx';
import { Search, XCircle, CheckCircle, AlertCircle, Clock, FileText, Loader2 } from 'lucide-react';
import { SkeletonLoader, SkeletonText } from './SkeletonLoader';

function TribunalCardSkeleton() {
  return (
    <div className="p-4 bg-surface border border-border rounded-xl min-h-[130px]">
      <div className="flex justify-between items-start mb-3">
        <SkeletonText width="w-3/4" height="h-5" />
        <SkeletonLoader className="w-5 h-5 rounded-full" />
      </div>
      <div className="space-y-2">
        <SkeletonText width="w-24" height="h-3" />
        <SkeletonText width="w-32" height="h-3" />
      </div>
    </div>
  );
}

export function TribunalGrid({ stats, loading = false, refreshing = false }) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  const tribunals = stats?.tribunals || {};
  const items = Object.entries(tribunals).sort((a, b) => a[0].localeCompare(b[0]));

  const filteredItems = items.filter(([name, data]) => {
    const matchesSearch = name.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === 'all' ||
      (filter === 'success' && data.status === 'success') ||
      (filter === 'error' && data.status !== 'success' && data.status !== 'absent') ||
      (filter === 'absent' && data.status === 'absent');
    return matchesSearch && matchesFilter;
  });

  const counts = {
    all: items.length,
    success: items.filter(([, d]) => d.status === 'success').length,
    error: items.filter(([, d]) => d.status !== 'success' && d.status !== 'absent').length,
    absent: items.filter(([, d]) => d.status === 'absent').length,
  };

  if (loading && items.length === 0) {
    return (
      <div className="card min-h-[400px]">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-6 gap-4">
          <SkeletonText width="w-48" height="h-7" />
          <div className="flex gap-3 w-full lg:w-auto">
            <SkeletonLoader className="w-full lg:w-64 h-10 rounded-lg" />
            <SkeletonLoader className="w-full lg:w-56 h-10 rounded-lg" />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-3">
          {[...Array(12)].map((_, i) => <TribunalCardSkeleton key={i} />)}
        </div>
      </div>
    );
  }

  return (
    <div className="card min-h-[400px]">
      {/* Header & Controls */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-5 gap-4">
        <div>
          <h2 className="text-lg font-semibold text-content flex items-center gap-2">
            Tribunal Status
            {refreshing && <Loader2 className="w-4 h-4 animate-spin text-accent" />}
          </h2>
          <p className="text-sm text-content-tertiary mt-0.5">
            {filteredItems.length} of {items.length} courts
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
          {/* Search */}
          <div className="relative group w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-content-tertiary group-focus-within:text-accent transition-colors" />
            <input
              type="text"
              placeholder="Search courts..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-surface border border-border rounded-lg px-9 py-2 text-sm text-content focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-all placeholder:text-content-tertiary"
              aria-label="Search tribunals"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-content-tertiary hover:text-content"
              >
                <XCircle className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Filter Pills */}
          <div className="flex bg-surface border border-border rounded-lg p-1 gap-0.5">
            {[
              { id: 'all', label: 'All' },
              { id: 'success', label: 'Online' },
              { id: 'error', label: 'Error' },
              { id: 'absent', label: 'Offline' },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={clsx(
                  "px-3 py-1.5 text-xs font-medium transition-colors rounded-md whitespace-nowrap flex-1 text-center",
                  filter === f.id
                    ? "bg-accent text-white shadow-sm"
                    : "text-content-secondary hover:text-content hover:bg-surface-overlay"
                )}
                aria-pressed={filter === f.id}
              >
                {f.label}
                <span className="ml-1 opacity-60">{counts[f.id]}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Grid Content */}
      {filteredItems.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center py-16 text-center">
          <Search className="w-12 h-12 text-content-tertiary opacity-30 mb-4" />
          <p className="text-content font-medium text-base">No matching courts</p>
          <p className="text-sm text-content-tertiary mt-1">
            Try adjusting your search or filter
          </p>
          <div className="flex gap-3 mt-6">
            <button
              onClick={() => setSearch('')}
              className="text-sm border border-border px-4 py-2 rounded-lg hover:border-accent hover:text-accent transition-colors font-medium"
            >
              Clear Search
            </button>
            <button
              onClick={() => { setSearch(''); setFilter('all'); }}
              className="text-sm bg-accent text-white px-4 py-2 rounded-lg hover:bg-accent-dark transition-colors font-medium"
            >
              Reset All
            </button>
          </div>
        </div>
      ) : (
        <div role="list" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-3">
          {filteredItems.map(([name, data]) => {
            const statusColor = data.status === 'success'
              ? 'border-l-success'
              : data.status === 'absent'
                ? 'border-l-content-tertiary'
                : 'border-l-danger';

            return (
              <div
                key={name}
                className={clsx(
                  "group p-4 bg-surface border border-border rounded-xl transition-all duration-200 hover:shadow-card-hover border-l-[3px]",
                  statusColor
                )}
                role="listitem"
              >
                <div className="flex justify-between items-start mb-2.5">
                  <span className="font-medium text-sm text-content truncate pr-2" title={name}>
                    {name}
                  </span>
                  {data.status === 'success' ? (
                    <CheckCircle className="w-4 h-4 text-success flex-shrink-0" aria-label="Online" />
                  ) : data.status === 'absent' ? (
                    <AlertCircle className="w-4 h-4 text-content-tertiary flex-shrink-0" aria-label="Offline" />
                  ) : (
                    <XCircle className="w-4 h-4 text-danger flex-shrink-0" aria-label="Error" />
                  )}
                </div>

                <div className="space-y-1.5 text-xs text-content-secondary">
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-content-tertiary" />
                    <span className="font-mono tabular-nums">
                      {data.last_update ? new Date(data.last_update).toLocaleDateString() : 'No date'}
                    </span>
                  </div>
                  {data.doc_count !== undefined ? (
                    <div className="flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-content-tertiary" />
                      <span className="font-mono tabular-nums">{data.doc_count.toLocaleString()} docs</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-content-tertiary">
                      <FileText className="w-3.5 h-3.5 opacity-60" />
                      <span>No metrics</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
