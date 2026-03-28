import { useState } from 'preact/compat';

export function PRGateExplainer() {
  const [prNumber, setPrNumber] = useState('');
  const [prData, setPrData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPRStatus = async (e) => {
    e.preventDefault();
    if (!prNumber) return;

    setLoading(true);
    setError(null);

    try {
      // In a real scenario, this would call a backend endpoint or use a GitHub token.
      // Since we don't have a backend and the prompt says "Prefer a textual/card view over overengineered visuals. Use existing GitHub/API integration patterns if the repo already has any.",
      // we'll fetch from the public GitHub API directly (which may be rate-limited, but serves the purpose for an admin tool).
      const repo = "franklinbaldo/causaganha"; // Replace with actual repo if different, or make configurable.

      const [prRes, reviewsRes] = await Promise.all([
        fetch(`https://api.github.com/repos/${repo}/pulls/${prNumber}`),

        fetch(`https://api.github.com/repos/${repo}/pulls/${prNumber}/reviews`)
      ]);

      if (!prRes.ok) throw new Error("Failed to fetch PR details. Make sure PR number is correct.");

      const prInfo = await prRes.json();

      const reviews = await reviewsRes.json();

      const lastCommitSha = prInfo.head.sha;
      const checkRunsRes = await fetch(`https://api.github.com/repos/${repo}/commits/${lastCommitSha}/check-runs`);
      const checkRuns = await checkRunsRes.json();

      setPrData({ prInfo, checkRuns: checkRuns.check_runs, reviews });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const summarizeStatus = (prInfo, checkRuns) => {
    const isMerged = prInfo.merged;
    const isClosed = prInfo.state === 'closed';

    if (isMerged) return { status: 'Merged', description: 'This PR is already merged.', color: 'text-success' };
    if (isClosed) return { status: 'Closed', description: 'This PR is closed without merging.', color: 'text-danger' };

    const pendingChecks = checkRuns.filter(c => c.status !== 'completed');
    const failedChecks = checkRuns.filter(c => c.status === 'completed' && c.conclusion !== 'success' && c.conclusion !== 'neutral' && c.conclusion !== 'skipped');

    // Check for "Kilo" or other specific external gates in check runs
    const blockedByKilo = failedChecks.find(c => c.name.toLowerCase().includes('kilo') || (c.output && c.output.title && c.output.title.toLowerCase().includes('kilo')));

    let status = 'Mergeable';
    let description = 'All checks passed and PR is ready to merge.';
    let color = 'text-success';

    if (failedChecks.length > 0) {
        status = 'Blocked';
        color = 'text-danger';
        if (blockedByKilo) {
            description = `CI ${failedChecks.length > 1 ? 'and Kilo failed' : 'green, Kilo ACTION_REQUIRED'} → merge blocked by external review gate.`;
        } else {
            description = `${failedChecks.length} check(s) failed.`;
        }
    } else if (pendingChecks.length > 0) {
        status = 'Pending';
        color = 'text-accent';
        description = `${pendingChecks.length} check(s) still in progress.`;
    }

    return { status, description, color, blockedByKilo: blockedByKilo || failedChecks[0] };
  };

  return (
    <div className="card p-6 w-full max-w-3xl mx-auto text-black dark:text-white">
      <h2 className="text-xl font-semibold mb-4">PR Readiness Gate Explainer</h2>
      <form onSubmit={fetchPRStatus} className="flex gap-4 mb-6">
        <input
          type="number"
          className="flex-1 p-2 border border-gray-300 dark:border-slate-700 rounded bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-accent"
          placeholder="Enter PR Number (e.g., 425)"
          value={prNumber}
          onChange={(e) => setPrNumber(e.target.value)}
        />
        <button type="submit" className="px-4 py-2 bg-accent text-white rounded hover:bg-accent-muted transition-colors disabled:opacity-50" disabled={loading || !prNumber}>
          {loading ? 'Checking...' : 'Check PR'}
        </button>
      </form>

      {error && <div className="p-4 mb-4 bg-danger/10 text-danger rounded">{error}</div>}

      {prData && (
        <div className="space-y-6">
          <div className="p-4 border border-gray-100 dark:border-slate-800 rounded bg-slate-50 dark:bg-slate-900/50">
             {(() => {
                const summary = summarizeStatus(prData.prInfo, prData.checkRuns);
                return (
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                             <h3 className="text-lg font-medium">PR #{prData.prInfo.number}: {prData.prInfo.title}</h3>
                             <span className={`px-2 py-1 text-xs font-semibold rounded-full bg-slate-200 dark:bg-slate-800 ${summary.color}`}>
                                {summary.status}
                             </span>
                        </div>
                        <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">{summary.description}</p>

                        {summary.blockedByKilo && (
                            <div className="text-sm">
                                <strong>Blocker: </strong>
                                <a href={summary.blockedByKilo.html_url || '#'} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                                    {summary.blockedByKilo.name}
                                </a>
                            </div>
                        )}
                    </div>
                )
             })()}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div>
                <h4 className="font-medium mb-3 border-b border-gray-100 dark:border-slate-800 pb-2">Completed Checks</h4>
                <ul className="space-y-2 text-sm max-h-60 overflow-y-auto">
                    {prData.checkRuns.filter(c => c.status === 'completed').map(c => (
                        <li key={c.id} className="flex justify-between items-center bg-slate-50 dark:bg-slate-900 p-2 rounded">
                            <span className="truncate mr-2" title={c.name}>{c.name}</span>
                            <span className={`flex-shrink-0 ${c.conclusion === 'success' ? 'text-success' : (c.conclusion === 'skipped' || c.conclusion === 'neutral' ? 'text-gray-500' : 'text-danger')}`}>
                                {c.conclusion === 'success' ? '✓' : (c.conclusion === 'skipped' || c.conclusion === 'neutral' ? '-' : '✗')} {c.conclusion}
                            </span>
                        </li>
                    ))}
                    {prData.checkRuns.filter(c => c.status === 'completed').length === 0 && <li className="text-gray-500">No completed checks.</li>}
                </ul>
             </div>

             <div>
                <h4 className="font-medium mb-3 border-b border-gray-100 dark:border-slate-800 pb-2">Pending Checks</h4>
                <ul className="space-y-2 text-sm max-h-60 overflow-y-auto">
                    {prData.checkRuns.filter(c => c.status !== 'completed').map(c => (
                        <li key={c.id} className="flex justify-between items-center bg-slate-50 dark:bg-slate-900 p-2 rounded">
                            <span className="truncate mr-2" title={c.name}>{c.name}</span>
                            <span className="text-accent flex-shrink-0">In Progress...</span>
                        </li>
                    ))}
                    {prData.checkRuns.filter(c => c.status !== 'completed').length === 0 && <li className="text-gray-500">No pending checks.</li>}
                </ul>
             </div>
          </div>
        </div>
      )}
    </div>
  );
}
