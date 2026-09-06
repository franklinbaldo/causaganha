import { parseFonteIndisponivelAviso, type Fonte, type ProcessoResultado } from './processoCnj';

export const CONSULTATION_SNAPSHOT_VERSION = 1;

interface DjenSnapshotFields {
  nPublicacoes: number | null;
  ultimaPub: string | null;
}

interface JurisSnapshotFields {
  dataJulgamento: string | null;
  nDocumentos: number | null;
  url: string | null;
}

interface StjSnapshotFields {
  dataDecisao: string | null;
  id: string | null;
}

interface DatajudSnapshotFields {
  ultimaAtualizacao: string | null;
  grau: string | null;
}

/**
 * Resumo mínimo e versionado do núcleo público de um processo (#1105),
 * guardado localmente por consulta salva (#1133) para responder "mudou desde
 * a última vez?" sem depender de conta ou backend novo.
 *
 * Um campo por fonte é `null` sempre que essa fonte não carregou com sucesso
 * nesta captura — seja porque nunca esteve no índice, seja porque está
 * `indisponível` agora (ver `fontesIndisponiveis`). Isso é deliberado: só
 * comparamos leituras reais entre si, nunca uma leitura real contra uma
 * ausência transitória (ver compareConsultationSnapshots).
 */
export interface ConsultationSnapshot {
  version: typeof CONSULTATION_SNAPSHOT_VERSION;
  capturedAt: string;
  encontrado: boolean;
  datasetGeradoEm: string | null;
  fontesPresentes: Fonte[];
  fontesIndisponiveis: Fonte[];
  djen: DjenSnapshotFields | null;
  juris: JurisSnapshotFields | null;
  stj: StjSnapshotFields | null;
  datajud: DatajudSnapshotFields | null;
}

/** Constrói o snapshot comparável a partir do resultado vivo de buscarProcesso(). */
export function buildConsultationSnapshot(resultado: ProcessoResultado, capturedAt: string): ConsultationSnapshot {
  const fontesIndisponiveis = Array.from(
    new Set(resultado.avisos.map(parseFonteIndisponivelAviso).filter((fonte): fonte is Fonte => fonte !== null)),
  );
  const indisponivel = (fonte: Fonte) => fontesIndisponiveis.includes(fonte);

  return {
    version: CONSULTATION_SNAPSHOT_VERSION,
    capturedAt,
    encontrado: resultado.encontrado,
    datasetGeradoEm: resultado.datasetGeradoEm,
    fontesPresentes: resultado.fontes,
    fontesIndisponiveis,
    djen:
      resultado.djen.present && !indisponivel('djen')
        ? { nPublicacoes: resultado.djen.nPublicacoes, ultimaPub: resultado.djen.ultimaPub }
        : null,
    juris:
      resultado.juris.present && !indisponivel('juris')
        ? {
            dataJulgamento: resultado.juris.dataJulgamento,
            nDocumentos: resultado.juris.nDocumentos,
            url: resultado.juris.url,
          }
        : null,
    stj:
      resultado.stj.present && !indisponivel('stj')
        ? { dataDecisao: resultado.stj.dataDecisao, id: resultado.stj.id }
        : null,
    datajud:
      resultado.datajud.present && !indisponivel('datajud')
        ? { ultimaAtualizacao: resultado.datajud.ultimaAtualizacao, grau: resultado.datajud.grau }
        : null,
  };
}

export type ConsultationChangeStatus = 'sem_historico' | 'sem_mudanca' | 'mudou' | 'nao_comparavel';

export interface ConsultationComparison {
  status: ConsultationChangeStatus;
  /** Campos com diferença observável, ex.: "djen.nPublicacoes", "fontesPresentes". */
  changedFields: string[];
  /** Fontes indisponíveis nesta captura (repassado do snapshot atual, para a UI explicar o estado). */
  fontesIndisponiveis: Fonte[];
  /** Fontes que tinham valor comparável na captura anterior mas não têm agora — nunca contam como "mudou". */
  unstableFontes: Fonte[];
}

const SOURCE_KEYS = ['djen', 'juris', 'stj', 'datajud'] as const;

/**
 * Compara duas capturas do mesmo processo. Só declara "mudou" quando duas
 * leituras reais e comparáveis divergem; uma fonte apenas indisponível na
 * captura atual nunca é lida como "removida" (#1133 critério de aceite).
 */
export function compareConsultationSnapshots(
  previous: ConsultationSnapshot | null,
  current: ConsultationSnapshot,
): ConsultationComparison {
  if (!previous) {
    return { status: 'sem_historico', changedFields: [], fontesIndisponiveis: current.fontesIndisponiveis, unstableFontes: [] };
  }

  const changedFields: string[] = [];
  const unstableFontes: Fonte[] = [];
  let comparableSourceCount = 0;
  let baselineSourceCount = 0;

  const novasFontes = current.fontesPresentes.filter((fonte) => !previous.fontesPresentes.includes(fonte));
  if (novasFontes.length > 0) changedFields.push('fontesPresentes');

  for (const source of SOURCE_KEYS) {
    const previousFields = previous[source] as Record<string, unknown> | null;
    const currentFields = current[source] as Record<string, unknown> | null;
    if (previousFields !== null) baselineSourceCount += 1;

    if (previousFields === null || currentFields === null) {
      if (previousFields !== null && currentFields === null) unstableFontes.push(source);
      continue;
    }

    comparableSourceCount += 1;
    for (const field of Object.keys(previousFields)) {
      if (previousFields[field] !== currentFields[field]) {
        changedFields.push(`${source}.${field}`);
      }
    }
  }

  let status: ConsultationChangeStatus;
  if (changedFields.length > 0) {
    status = 'mudou';
  } else if (baselineSourceCount > 0 && comparableSourceCount === 0) {
    status = 'nao_comparavel';
  } else {
    status = 'sem_mudanca';
  }

  return { status, changedFields, fontesIndisponiveis: current.fontesIndisponiveis, unstableFontes };
}
