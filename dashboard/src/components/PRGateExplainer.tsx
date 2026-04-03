import { useState } from 'preact/compat';
import type { JSX } from 'preact';

interface CheckRun {
  id: number;
  name: string;
  status: string;
  conclusion: string | null;
  html_url: string;
  output?: {
    title?: string;
  };
}

interface PRInfo {
  number: number;
  title: string;
  state: string;
  merged: boolean;
  head: {
    sha: string;
  };
}

interface Review {
  id: number;
  state: string;
  user: {
    login: string;
  };
}

interface PRData {
  prInfo: PRInfo;
  checkRuns: CheckRun[];
  reviews: Review[];
}

interface StatusSummary {
  status: string;
  description: string;
  color: string;
  blockedByKilo?: CheckRun;
}

export function PRGateExplainer() {
  const [prNumber, setPrNumber] = useState<string>('');
  const [prData, setPrData] = useState<PRData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPRStatus = async (e: JSX.TargetedEvent<HTMLFormElement, Event>) => {
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

      const prInfo: PRInfo = await prRes.json();

      const reviews: Review[] = await reviewsRes.json();

      const lastCommitSha = prInfo.head.sha;
      const checkRunsRes = await fetch(`https://api.github.com/repos/${repo}/commits/${lastCommitSha}/check-runs`);
      const checkRunsData: { check_runs: CheckRun[] } = await checkRunsRes.json();

      setPrData({ prInfo, checkRuns: checkRunsData.check_runs, reviews });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const summarizeStatus = (prInfo: PRInfo, checkRuns: CheckRun[]): StatusSummary => {
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

    if (failedChecks.length> 0) {
        status = 'Blocked';
        color = 'text-danger';
        if (blockedByKilo) {
            description = `CI ${failedChecks.length> 1 ? 'and Kilo failed' : 'green, Kilo ACTION_REQUIRED'} → merge blocked by external review gate.`;
        } else {
            description = `${failedChecks.length} check(s) failed.`;
        }
    } else if (pendingChecks.length> 0) {
        status = 'Pending';
        color = 'text-accent';
        description = `${pendingChecks.length} check(s) still in progress.`;
    }

    return { status, description, color, blockedByKilo: blockedByKilo || failedChecks[0] };
  };

  return (
    <article>
      <h2>PR Readiness Gate Explainer</h2>
      <form onSubmit={fetchPRStatus}>
        <input
          type="number" placeholder="Enter PR Number (e.g., 425)"
          value={prNumber}
          onChange={(e: JSX.TargetedEvent<HTMLInputElement>) => setPrNumber(e.currentTarget.value)}
        />
        <button type="submit" disabled={loading || !prNumber}>
          {loading ? 'Checking...' : 'Check PR'}
        </button>
      </form>

      {error && <div className="text-danger">{error}</div>}

      {prData && (
        <div>
          <div>
             {(() => {
                const summary = summarizeStatus(prData.prInfo, prData.checkRuns);
                return (
                    <div>
                        <div>
                             <h3>PR #{prData.prInfo.number}: {prData.prInfo.title}</h3>
                             <span className={summary.color}>
                                {summary.status}
                             </span>
                        </div>
                        <p>{summary.description}</p>

                        {summary.blockedByKilo && (
                            <div>
                                <strong>Blocker: </strong>
                                <a href={summary.blockedByKilo.html_url || '#'} target="_blank" rel="noopener noreferrer" className="text-accent">
                                    {summary.blockedByKilo.name}
                                </a>
                            </div>
                        )}
                    </div>
                )
             })()}
          </div>

          <div className="grid">
             <div>
                <h4>Completed Checks</h4>
                <ul>
                    {prData.checkRuns.filter(c => c.status === 'completed').map(c => (
                        <li key={c.id}>
                            <span  title={c.name}>{c.name}</span>
                            <span className={c.conclusion === 'success' ? 'text-success' : (c.conclusion === 'skipped' || c.conclusion === 'neutral' ? undefined : 'text-danger')}>
                                {c.conclusion === 'success' ? '✓' : (c.conclusion === 'skipped' || c.conclusion === 'neutral' ? '-' : '✗')} {c.conclusion}
                            </span>
                        </li>
                    ))}
                    {prData.checkRuns.filter(c => c.status === 'completed').length === 0 && <li>No completed checks.</li>}
                </ul>
             </div>

             <div>
                <h4>Pending Checks</h4>
                <ul>
                    {prData.checkRuns.filter(c => c.status !== 'completed').map(c => (
                        <li key={c.id}>
                            <span  title={c.name}>{c.name}</span>
                            <span className="text-accent">In Progress...</span>
                        </li>
                    ))}
                    {prData.checkRuns.filter(c => c.status !== 'completed').length === 0 && <li>No pending checks.</li>}
                </ul>
             </div>
          </div>
        </div>
      )}
    </article>
  );
}
