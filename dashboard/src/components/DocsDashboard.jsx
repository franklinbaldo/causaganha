import { useState } from 'preact/compat';

export function DocsDashboard({ docsWarnings }) {
  if (!docsWarnings) {
    return (
      <div className="p-8 text-center bg-gray-50 dark:bg-slate-900 rounded-xl border border-gray-100 dark:border-slate-800">
        <p className="text-gray-500 dark:text-gray-400">Loading docs warnings data...</p>
      </div>
    );
  }

  const { summary, details } = docsWarnings;

  const categories = [
    { id: 'missing_nav_targets', label: 'Missing Nav Targets', count: summary.categories.missing_nav_targets, icon: '❌' },
    { id: 'broken_links', label: 'Broken Links', count: summary.categories.broken_links, icon: '🔗' },
    { id: 'orphaned_docs', label: 'Orphaned Docs (Not in Nav)', count: summary.categories.orphaned_docs, icon: '👻' },
    { id: 'broken_autorefs', label: 'Broken Autorefs', count: summary.categories.broken_autorefs, icon: '🔍' },
    { id: 'git_revision_warnings', label: 'Git Revision Warnings', count: summary.categories.git_revision_warnings, icon: '⏱️' },
    { id: 'other', label: 'Other Warnings', count: summary.categories.other, icon: '⚠️' }
  ];

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-gray-100 dark:border-slate-800 shadow-sm flex flex-col justify-center items-center">
          <span className="text-4xl font-bold text-black dark:text-white mb-2">{summary.total_warnings}</span>
          <span className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Total Warnings</span>
        </div>

        {categories.filter(c => c.count > 0).map(cat => (
          <div key={cat.id} className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-gray-100 dark:border-slate-800 shadow-sm flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{cat.icon}</span>
              <span className="font-medium text-gray-700 dark:text-gray-300">{cat.label}</span>
            </div>
            <span className="text-xl font-bold text-black dark:text-white bg-gray-100 dark:bg-slate-800 px-3 py-1 rounded-full">
              {cat.count}
            </span>
          </div>
        ))}
      </div>

      {/* Details Sections */}
      <div className="space-y-6">
        {details.missing_nav_targets?.length > 0 && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-100 dark:border-slate-800 overflow-hidden">
            <div className="p-4 border-b border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800/50 flex items-center gap-2">
              <span>❌</span>
              <h3 className="font-medium text-black dark:text-white">Missing Nav Targets</h3>
            </div>
            <div className="p-4">
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400">
                {details.missing_nav_targets.map((item, idx) => (
                  <li key={idx}><code className="bg-gray-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-red-600 dark:text-red-400">{item}</code></li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {details.broken_links_examples?.length > 0 && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-100 dark:border-slate-800 overflow-hidden">
            <div className="p-4 border-b border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800/50 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span>🔗</span>
                <h3 className="font-medium text-black dark:text-white">Broken Links (Examples)</h3>
              </div>
              <span className="text-xs text-gray-500">Top 5 shown</span>
            </div>
            <div className="p-4">
              <ul className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
                {details.broken_links_examples.map((item, idx) => (
                  <li key={idx} className="flex flex-col gap-1 border-b border-gray-50 dark:border-slate-800 pb-2 last:border-0 last:pb-0">
                    <div>In <code className="bg-gray-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-blue-600 dark:text-blue-400">{item.file}</code>:</div>
                    <div className="pl-4 text-gray-500">Links to <code className="bg-gray-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">{item.link}</code> (target not found)</div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {details.orphaned_docs_examples?.length > 0 && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-100 dark:border-slate-800 overflow-hidden">
            <div className="p-4 border-b border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800/50 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span>👻</span>
                <h3 className="font-medium text-black dark:text-white">Orphaned Docs (Not in Nav)</h3>
              </div>
              <span className="text-xs text-gray-500">Top 5 shown</span>
            </div>
            <div className="p-4">
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400">
                {details.orphaned_docs_examples.map((item, idx) => (
                  <li key={idx}><code className="bg-gray-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">{item}</code></li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {details.broken_autorefs?.length > 0 && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-100 dark:border-slate-800 overflow-hidden">
            <div className="p-4 border-b border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800/50 flex items-center gap-2">
              <span>🔍</span>
              <h3 className="font-medium text-black dark:text-white">Broken Autorefs</h3>
            </div>
            <div className="p-4">
              <ul className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
                {details.broken_autorefs.map((item, idx) => (
                  <li key={idx} className="flex flex-col gap-1">
                    <div>In <code className="bg-gray-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">{item.file}</code>: missing ref <code className="bg-gray-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-orange-600">{item.target}</code></div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
