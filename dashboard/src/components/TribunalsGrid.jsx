import { useState } from 'react';
import clsx from 'clsx';
import { Search, Filter, CheckCircle, XCircle, AlertCircle, Clock, FileText, Loader2, RefreshCw } from 'lucide-react';
import { SkeletonLoader, SkeletonText } from './SkeletonLoader';

function TribunalCardSkeleton() {
  return (
    <div className="p-4 bg-cyber-dark border border-cyber-border rounded flex flex-col justify-between min-h-[140px]">
      <div className="pl-3 w-full">
        <div className="flex justify-between items-start mb-3">
          <SkeletonText width="w-3/4" height="h-6" />
          <SkeletonLoader className="w-5 h-5 rounded-full" />
        </div>
        <div className="space-y-2">
          <div className="flex items-center">
            <SkeletonLoader className="w-3.5 h-3.5 mr-2 rounded-sm" />
            <SkeletonText width="w-24" height="h-3" />
          </div>
          <div className="flex items-center">
            <SkeletonLoader className="w-3.5 h-3.5 mr-2 rounded-sm" />
            <SkeletonText width="w-32" height="h-3" />
          </div>
        </div>
      </div>
      <div className="pl-3 mt-3 pt-3 border-t border-cyber-border flex justify-between items-center">
        <SkeletonText width="w-20" height="h-4" />
        <SkeletonText width="w-14" height="h-4" />
      </div>
    </div>
  );
}

export function TribunalsGrid({ stats, loading = false, refreshing = false }) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all'); // all, success, error, absent
  const [localRefreshing, setLocalRefreshing] = useState({});

  const handleLocalRefresh = (name) => {
    setLocalRefreshing(prev => ({ ...prev, [name]: true }));
    setTimeout(() => {
      setLocalRefreshing(prev => ({ ...prev, [name]: false }));
    }, 1500);
  };

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

  if (loading && items.length === 0) {
    return (
      <div className="cyber-card flex flex-col h-full min-h-[400px]">
        <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center mb-6 gap-4 border-b border-cyber-border pb-4">
          <div className="w-full xl:w-1/3">
             <div className="h-7 w-48 mb-2"><SkeletonText height="h-full" /></div>
             <div className="h-3 w-32"><SkeletonText height="h-full" /></div>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 w-full xl:w-auto">
             <SkeletonLoader className="w-full sm:w-64 h-10 rounded" />
             <SkeletonLoader className="w-full sm:w-48 h-10 rounded" />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-4 flex-1">
          {[...Array(12)].map((_, i) => (
            <TribunalCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="cyber-card flex flex-col h-full min-h-[400px]">
      {/* Header & Controls */}
      <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center mb-6 gap-4 border-b border-cyber-border pb-4">
        <div>
           <h2 className="text-xl font-bold text-cyber-primary tracking-wide flex items-center gap-2">
             <Filter className="w-5 h-5" />
             TRIBUNAL STATUS
             {refreshing && <Loader2 className="w-4 h-4 animate-spin text-cyber-secondary ml-2" />}
           </h2>
           <p className="text-sm text-cyber-gray mt-1 font-mono uppercase tracking-wider pl-7">
             Showing {filteredItems.length} of {items.length} monitored sources
           </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 w-full xl:w-auto">
          {/* Search */}
          <div className="relative group w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cyber-muted group-focus-within:text-cyber-primary transition-colors" />
            <input 
              type="text" 
              placeholder="SEARCH..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-cyber-black border border-cyber-border rounded px-10 py-2 text-sm text-cyber-text focus:outline-none focus:border-cyber-primary focus:ring-1 focus:ring-cyber-primary transition-all placeholder:text-cyber-muted font-mono uppercase"
              aria-label="Search tribunals"
            />
            {search && (
              <button 
                onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-cyber-muted hover:text-cyber-text"
              >
                <XCircle className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Filter Pills */}
          <div className="flex bg-cyber-black border border-cyber-border rounded p-1 gap-1 overflow-x-auto">
             {[
               { id: 'all', label: 'ALL' },
               { id: 'success', label: 'ONLINE' },
               { id: 'error', label: 'ERROR' },
               { id: 'absent', label: 'OFFLINE' }
             ].map((f) => (
               <button
                 key={f.id}
                 onClick={() => setFilter(f.id)}
                 className={clsx(
                   "px-3 py-1.5 text-sm font-bold uppercase transition-colors rounded-sm whitespace-nowrap flex-1 text-center",
                   filter === f.id ? "bg-cyber-primary text-cyber-black" : "text-cyber-muted hover:text-cyber-text hover:bg-cyber-dark"
                 )}
                 aria-pressed={filter === f.id}
               >
                 {f.label}
               </button>
             ))}
          </div>
        </div>
      </div>

      {/* Grid Content */}
      {filteredItems.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center py-12 border-2 border-dashed border-cyber-border/30 rounded bg-cyber-dark/30 text-center group">
              <div className="relative mb-6">
                <Filter className="w-16 h-16 text-cyber-muted opacity-20 group-hover:opacity-40 transition-opacity" />
                <Search className="w-8 h-8 text-cyber-primary absolute bottom-0 right-0 animate-bounce" />
              </div>
              <p className="text-cyber-text font-bold text-xl tracking-tighter">NO MATCHING SOURCES</p>
              <p className="text-sm text-cyber-muted mt-2 max-w-xs mx-auto">
                The search for "<span className="text-cyber-primary">{search}</span>" with filter "<span className="text-cyber-secondary uppercase">{filter}</span>" returned zero results.
              </p>
              <div className="flex gap-4 mt-8">
                <button 
                  onClick={() => setSearch('')}
                  className="text-sm border border-cyber-muted px-4 py-2 hover:border-cyber-primary hover:text-cyber-primary transition-colors uppercase tracking-widest font-bold"
                >
                  Clear Search
                </button>
                <button 
                  onClick={() => { setSearch(''); setFilter('all'); }}
                  className="text-sm bg-cyber-primary text-cyber-black px-6 py-2 hover:bg-white transition-colors uppercase font-bold tracking-widest"
                >
                  Reset All
                </button>
              </div>
          </div>
      ) : (
          <div role="list" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-4 overflow-y-auto pr-2 custom-scrollbar flex-1">
            {filteredItems.map(([name, data]) => (
                <div
                    key={name}
                    className="group relative p-4 bg-cyber-dark border border-cyber-border hover:border-cyber-primary transition-all duration-300 rounded overflow-hidden flex flex-col justify-between min-h-[140px]"
                    role="listitem"
                >
                    {/* Status Indicator Bar */}
                    <div className={clsx(
                      "absolute top-0 left-0 w-1 h-full transition-all group-hover:w-1.5",
                      data.status === 'success' ? "bg-cyber-primary shadow-[0_0_15px_rgba(0,255,65,0.2)]" :
                      data.status === 'absent' ? "bg-cyber-muted" : "bg-cyber-danger shadow-[0_0_15px_rgba(255,51,51,0.2)]"
                    )} />

                    {/* Refresh Spinner Over Card */}
                    {(refreshing || localRefreshing[name]) && (
                      <div className="absolute top-2 right-2 z-10">
                        <Loader2 className="w-4 h-4 text-cyber-primary animate-spin opacity-70" />
                      </div>
                    )}

                    <div className="pl-3 w-full">
                        <div className="flex justify-between items-start mb-3">
                           <span className="font-bold text-lg text-cyber-text group-hover:text-cyber-primary transition-colors tracking-tight truncate pr-2" title={name}>
                             {name}
                           </span>
                           
                           {/* Status Icon */}
                           {!(refreshing || localRefreshing[name]) && (
                             <div className="flex-shrink-0">
                               {data.status === 'success' ? (
                                  <CheckCircle className="w-5 h-5 text-cyber-primary" aria-label="Operational" />
                               ) : data.status === 'absent' ? (
                                  <AlertCircle className="w-5 h-5 text-cyber-muted" aria-label="No Data" />
                               ) : (
                                  <XCircle className="w-5 h-5 text-cyber-danger" aria-label="Error" />
                               )}
                             </div>
                           )}
                        </div>

                        <div className="space-y-2">
                           <div className="flex items-center text-sm text-cyber-gray group-hover:text-cyber-text transition-colors">
                              <Clock className="w-4 h-4 mr-2" />
                              <span className="font-mono">{data.last_update ? new Date(data.last_update).toLocaleDateString() : 'NO DATE'}</span>
                           </div>
                           
                           {data.doc_count !== undefined ? (
                             <div className="flex items-center text-sm text-cyber-gray group-hover:text-cyber-text transition-colors">
                               <FileText className="w-4 h-4 mr-2" />
                               <span className="font-mono">{data.doc_count.toLocaleString()} docs</span>
                             </div>
                           ) : (
                             <div className="flex items-center text-sm text-cyber-muted italic">
                               <FileText className="w-4 h-4 mr-2 opacity-60" />
                               <span>No metrics</span>
                             </div>
                           )}
                        </div>
                    </div>
                    
                    {/* Hover Action */}
                    <div className="pl-3 mt-3 pt-3 border-t border-cyber-border flex justify-between items-center opacity-80 group-hover:opacity-100 transition-opacity">
                      <span className={clsx(
                        "text-sm font-bold uppercase tracking-wider",
                        data.status === 'success' ? "text-cyber-primary" : 
                        data.status === 'absent' ? "text-cyber-muted" : "text-cyber-danger"
                      )}>
                        {data.status === 'success' ? 'ONLINE' : data.status === 'absent' ? 'OFFLINE' : 'ERROR'}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-cyber-muted group-hover:text-cyber-text transition-colors">ID: {name.substring(0,4)}</span>
                        <button 
                          onClick={(e) => { e.stopPropagation(); handleLocalRefresh(name); }}
                          className="p-1.5 hover:bg-cyber-dim rounded transition-colors group/btn"
                          title="Refresh source"
                        >
                          <RefreshCw className={clsx(
                            "w-4 h-4 text-cyber-muted group-hover/btn:text-cyber-primary transition-all",
                            localRefreshing[name] && "animate-spin text-cyber-primary"
                          )} />
                        </button>
                      </div>
                    </div>
                </div>
            ))}
          </div>
      )}
    </div>
  );
}
