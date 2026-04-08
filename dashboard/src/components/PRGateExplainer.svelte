<script lang="ts">
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

  let prNumber = $state<string>('');
  let prData = $state<PRData | null>(null);
  let loading = $state<boolean>(false);
  let error = $state<string | null>(null);

  const summary = $derived(
    prData ? summarizeStatus(prData.prInfo, prData.checkRuns) : null
  );

  const completedChecks = $derived(
    prData ? prData.checkRuns.filter(c => c.status === 'completed') : []
  );

  const pendingChecks = $derived(
    prData ? prData.checkRuns.filter(c => c.status !== 'completed') : []
  );

  async function fetchPRStatus(e: SubmitEvent) {
    e.preventDefault();
    if (!prNumber) return;

    loading = true;
    error = null;

    try {
      const repo = "franklinbaldo/causaganha";

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

      prData = { prInfo, checkRuns: checkRunsData.check_runs, reviews };
    } catch (err: unknown) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      loading = false;
    }
  }

  function summarizeStatus(prInfo: PRInfo, checkRuns: CheckRun[]): StatusSummary {
    const isMerged = prInfo.merged;
    const isClosed = prInfo.state === 'closed';

    if (isMerged) return { status: 'Merged', description: 'This PR is already merged.', color: 'text-success' };
    if (isClosed) return { status: 'Closed', description: 'This PR is closed without merging.', color: 'text-error' };

    const pendingChecks = checkRuns.filter(c => c.status !== 'completed');
    const failedChecks = checkRuns.filter(c => c.status === 'completed' && c.conclusion !== 'success' && c.conclusion !== 'neutral' && c.conclusion !== 'skipped');

    const blockedByKilo = failedChecks.find(c => c.name.toLowerCase().includes('kilo') || (c.output && c.output.title && c.output.title.toLowerCase().includes('kilo')));

    let status = 'Mergeable';
    let description = 'All checks passed and PR is ready to merge.';
    let color = 'text-success';

    if (failedChecks.length > 0) {
      status = 'Blocked';
      color = 'text-error';
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
  }
</script>

<div class="card bg-base-100 shadow-sm border border-base-300"><div class="card-body">
  <h2>PR Readiness Gate Explainer</h2>
  <form onsubmit={fetchPRStatus}>
    <input
      class="input input-bordered"
      type="number" placeholder="Enter PR Number (e.g., 425)"
      value={prNumber}
      oninput={(e: Event & { currentTarget: HTMLInputElement }) => prNumber = e.currentTarget.value}
    />
    <button type="submit" disabled={loading || !prNumber}>
      {loading ? 'Checking...' : 'Check PR'}
    </button>
  </form>

  {#if error}
    <div class="text-error">{error}</div>
  {/if}

  {#if prData && summary}
    <div>
      <div>
        <div>
          <div>
            <h3>PR #{prData.prInfo.number}: {prData.prInfo.title}</h3>
            <span class={summary.color}>
              {summary.status}
            </span>
          </div>
          <p>{summary.description}</p>

          {#if summary.blockedByKilo}
            <div>
              <strong>Blocker: </strong>
              <a href={summary.blockedByKilo.html_url || '#'} target="_blank" rel="noopener noreferrer" class="text-accent">
                {summary.blockedByKilo.name}
              </a>
            </div>
          {/if}
        </div>
      </div>

      <div class="grid">
        <div>
          <h4>Completed Checks</h4>
          <ul>
            {#each completedChecks as c (c.id)}
              <li>
                <span title={c.name}>{c.name}</span>
                <span class={c.conclusion === 'success' ? 'text-success' : (c.conclusion === 'skipped' || c.conclusion === 'neutral' ? undefined : 'text-error')}>
                  {c.conclusion === 'success' ? '✓' : (c.conclusion === 'skipped' || c.conclusion === 'neutral' ? '-' : '✗')} {c.conclusion}
                </span>
              </li>
            {/each}
            {#if completedChecks.length === 0}
              <li>No completed checks.</li>
            {/if}
          </ul>
        </div>

        <div>
          <h4>Pending Checks</h4>
          <ul>
            {#each pendingChecks as c (c.id)}
              <li>
                <span title={c.name}>{c.name}</span>
                <span class="text-accent">In Progress...</span>
              </li>
            {/each}
            {#if pendingChecks.length === 0}
              <li>No pending checks.</li>
            {/if}
          </ul>
        </div>
      </div>
    </div>
  {/if}
</div></div>
