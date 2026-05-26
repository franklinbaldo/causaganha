<script lang="ts">
  import { fetchWithRetry } from '../lib/fetchData';

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
        fetchWithRetry(`https://api.github.com/repos/${repo}/pulls/${prNumber}`),
        fetchWithRetry(`https://api.github.com/repos/${repo}/pulls/${prNumber}/reviews`)
      ]);

      if (!prRes.ok) throw new Error("Falha ao obter detalhes do PR. Verifique se o número está correto.");

      const prInfo: PRInfo = await prRes.json();
      const reviews: Review[] = await reviewsRes.json();

      const lastCommitSha = prInfo.head.sha;
      const checkRunsRes = await fetchWithRetry(`https://api.github.com/repos/${repo}/commits/${lastCommitSha}/check-runs`);
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

    if (isMerged) return { status: 'Mesclado', description: 'Este PR já foi mesclado.', color: 'status-success' };
    if (isClosed) return { status: 'Fechado', description: 'Este PR foi fechado sem ser mesclado.', color: 'status-error' };

    const pendingChecks = checkRuns.filter(c => c.status !== 'completed');
    const failedChecks = checkRuns.filter(c => c.status === 'completed' && c.conclusion !== 'success' && c.conclusion !== 'neutral' && c.conclusion !== 'skipped');

    const blockedByKilo = failedChecks.find(c => c.name.toLowerCase().includes('kilo') || (c.output && c.output.title && c.output.title.toLowerCase().includes('kilo')));

    let status = 'Pronto para merge';
    let description = 'Todas as verificações passaram. O PR está pronto para ser mesclado.';
    let color = 'status-success';

    if (failedChecks.length > 0) {
      status = 'Bloqueado';
      color = 'status-error';
      if (blockedByKilo) {
        description = `${failedChecks.length > 1 ? 'CI e Kilo falharam' : 'CI verde, Kilo ACTION_REQUIRED'} → merge bloqueado por revisão externa.`;
      } else {
        description = `${failedChecks.length} verificação(ões) falharam.`;
      }
    } else if (pendingChecks.length > 0) {
      status = 'Pendente';
      color = 'status-accent';
      description = `${pendingChecks.length} verificação(ões) em andamento.`;
    }

    return { status, description, color, blockedByKilo: blockedByKilo || failedChecks[0] };
  }
</script>

<article id="pr-gate-explainer">
  <h2>Diagnóstico de prontidão do PR</h2>
  <form onsubmit={fetchPRStatus}>
    <input
      type="number"
      placeholder="Número do PR (ex.: 425)"
      aria-label="Número do PR"
      autocomplete="off"
      inputmode="numeric"
      min="1"
      value={prNumber}
      oninput={(e: Event & { currentTarget: HTMLInputElement }) => prNumber = e.currentTarget.value}
    />
    <button type="submit" disabled={loading || !prNumber} aria-busy={loading}>
      {loading ? 'Verificando...' : 'Verificar PR'}
    </button>
  </form>

  {#if error}
    <aside role="alert" class="status-error">{error}</aside>
  {/if}

  {#if prData && summary}
    <div>
      <div>
        <div>
          <div>
            <h3>PR #{prData.prInfo.number}: {prData.prInfo.title}</h3>
            <mark class={summary.color}>
              {summary.status}
            </mark>
          </div>
          <p>{summary.description}</p>

          {#if summary.blockedByKilo}
            <div>
              <strong>Bloqueio: </strong>
              <a href={summary.blockedByKilo.html_url} target="_blank" rel="noopener noreferrer" class="link-accent">
                {summary.blockedByKilo.name}
              </a>
            </div>
          {/if}
        </div>
      </div>

      <div class="checks-grid">
        <div>
          <h4>Verificações concluídas</h4>
          <ul>
            {#each completedChecks as c (c.id)}
              <li>
                <span title={c.name}>{c.name}</span>
                <mark class={c.conclusion === 'success' ? 'status-success' : (c.conclusion === 'skipped' || c.conclusion === 'neutral' ? undefined : 'status-error')}>
                  {c.conclusion === 'success' ? '✓' : (c.conclusion === 'skipped' || c.conclusion === 'neutral' ? '-' : '✗')} {c.conclusion}
                </mark>
              </li>
            {/each}
            {#if completedChecks.length === 0}
              <li>Nenhuma verificação concluída.</li>
            {/if}
          </ul>
        </div>

        <div>
          <h4>Verificações pendentes</h4>
          <ul>
            {#each pendingChecks as c (c.id)}
              <li>
                <span title={c.name}>{c.name}</span>
                <mark class="status-accent">Em andamento...</mark>
              </li>
            {/each}
            {#if pendingChecks.length === 0}
              <li>Nenhuma verificação pendente.</li>
            {/if}
          </ul>
        </div>
      </div>
    </div>
  {/if}
</article>

<style>
  mark.status-success {
    background: color-mix(in srgb, var(--color-success) 15%, transparent);
    color: var(--color-success);
  }

  mark.status-error, aside.status-error {
    background: color-mix(in srgb, var(--color-error) 12%, transparent);
    color: var(--color-error);
    border: 1px solid var(--color-error);
    border-radius: var(--pico-border-radius);
    padding: 0.5rem 0.75rem;
    display: block;
  }

  mark.status-accent {
    background: color-mix(in srgb, var(--color-accent) 15%, transparent);
    color: var(--color-accent);
  }

  .link-accent {
    color: var(--color-accent);
    text-decoration: underline;
  }

  .checks-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  @media (max-width: 767px) {
    .checks-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
