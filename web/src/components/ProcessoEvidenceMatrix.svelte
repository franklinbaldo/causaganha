<script lang="ts">
  import { FONTE_LABELS, type EvidenceMatrixRow, type EvidenceStatus, type Fonte, type Papel } from '../lib/processoCnj';

  let { rows }: { rows: EvidenceMatrixRow[] } = $props();

  const PAPEL_LABELS: Record<Papel, string> = {
    arquivo: 'Arquivo',
    estado: 'Estado',
    teor: 'Teor',
  };

  const STATUS_LABELS: Record<EvidenceStatus, string> = {
    presente: 'Presente',
    ausente: 'Sem registro',
    indisponivel: 'Indisponível',
  };

  const STATUS_TONE: Record<EvidenceStatus, string> = {
    presente: 'success',
    ausente: 'muted',
    indisponivel: 'error',
  };

  // Cada fonte leva ao bloco de detalhe já existente no dossiê;
  // JURIS e STJ compartilham a mesma seção de documentos.
  const FONTE_ANCHOR: Record<Fonte, string> = {
    djen: '#djen-title',
    datajud: '#datajud-title',
    juris: '#documentos-title',
    stj: '#documentos-title',
  };
</script>

<section class="processo-evidence-matrix" aria-labelledby="evidencias-title">
  <h3 id="evidencias-title">Resumo de evidências por fonte</h3>
  <ul class="processo-evidence-matrix__list">
    {#each rows as row (row.fonte)}
      <li>
        <a class="badge processo-evidence-matrix__item" data-tone={STATUS_TONE[row.status]} href={FONTE_ANCHOR[row.fonte]}>
          <span class="processo-evidence-matrix__papel">{PAPEL_LABELS[row.papel]}</span>
          <span class="processo-evidence-matrix__fonte">{FONTE_LABELS[row.fonte]}</span>
          <span class="processo-evidence-matrix__status">{STATUS_LABELS[row.status]}</span>
        </a>
      </li>
    {/each}
  </ul>
</section>

<style>
  .processo-evidence-matrix {
    margin-block: var(--space-4, 1rem);
  }

  .processo-evidence-matrix__list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2, 0.5rem);
    list-style: none;
    margin: var(--space-2, 0.5rem) 0 0;
    padding: 0;
  }

  .processo-evidence-matrix__item {
    display: inline-flex;
    align-items: baseline;
    gap: 0.35em;
    text-decoration: none;
  }

  .processo-evidence-matrix__papel {
    font-size: 0.75em;
    opacity: 0.75;
  }

  .processo-evidence-matrix__fonte {
    font-weight: 700;
  }
</style>
