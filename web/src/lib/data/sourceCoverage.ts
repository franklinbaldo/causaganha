import type {
  DatajudTotals,
  JurisTotals,
  SiteStatus,
  StjTotals,
} from './contracts';
import {
  evaluateSourceFreshness,
  freshnessDisplayLabel,
} from './siteStatus';

export type SourceRole = 'Arquivo' | 'Estado' | 'Teor';

export interface SourceCoverageInput {
  siteStatus: SiteStatus;
  datajud: DatajudTotals | null;
  juris: JurisTotals | null;
  stj: StjTotals | null;
  now?: number;
}

export interface SourceCoverageItem {
  id: 'djen' | 'datajud' | 'tjro_juris' | 'stj';
  role: SourceRole;
  name: string;
  description: string;
  coverage: string;
  freshness: string;
  limitation: string;
  href: string;
}

const formatDate = (value: string | null): string => value ?? 'não publicada';
const formatNumber = (value: number): string => value.toLocaleString('pt-BR');

export function buildSourceCoverage({
  siteStatus,
  datajud,
  juris,
  stj,
  now = Date.now(),
}: SourceCoverageInput): SourceCoverageItem[] {
  const djen = siteStatus.sources.djen;
  const djenFreshness = freshnessDisplayLabel(evaluateSourceFreshness(djen, now));

  return [
    {
      id: 'djen',
      role: 'Arquivo',
      name: 'DJEN',
      description: 'Publicações preservadas e cobertura do acervo.',
      coverage:
        `${formatNumber(djen.zips_archived)} cadernos preservados · ` +
        `${formatDate(djen.earliest_upload_date)} — ${formatDate(djen.latest_upload_date)} · ` +
        `${djen.coverage_pct === null ? 'cobertura não publicada' : `${djen.coverage_pct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}% de cobertura`}`,
      freshness: djenFreshness,
      limitation: 'Arquivo histórico: preservação não substitui o estado processual atual.',
      href: 'publicacoes',
    },
    {
      id: 'datajud',
      role: 'Estado',
      name: 'DataJud',
      description: 'Capa, classe, assuntos e movimentos processuais.',
      coverage: datajud
        ? `${formatNumber(datajud.total_processos)} processos · ${formatNumber(datajud.total_tribunais)} tribunais`
        : 'Cobertura não publicada neste build.',
      freshness: datajud?.ultima_atualizacao
        ? `Atualização publicada: ${datajud.ultima_atualizacao}`
        : 'Atualização não publicada.',
      limitation: 'Metadados e movimentos não devem ser tratados como teor da decisão.',
      href: 'processo',
    },
    {
      id: 'tjro_juris',
      role: 'Teor',
      name: 'TJRO JURIS',
      description: 'Decisões e documentos quando presentes no corpus.',
      coverage: juris
        ? `${formatNumber(juris.total_documentos)} documentos · ${formatNumber(juris.total_orgaos)} órgãos`
        : 'Cobertura não publicada neste build.',
      freshness: juris?.data_mais_recente
        ? `Documento mais recente: ${juris.data_mais_recente}`
        : 'Atualização não publicada.',
      limitation: 'Cobertura limitada ao corpus publicado pelo TJRO JURIS.',
      href: 'processo',
    },
    {
      id: 'stj',
      role: 'Teor',
      name: 'STJ',
      description: 'Acórdãos e metadados ligados ao processo quando disponíveis.',
      coverage: stj
        ? `${formatNumber(stj.total)} registros · ${formatNumber(stj.total_temas)} temas`
        : 'Cobertura não publicada neste build.',
      freshness: stj?.ultima_decisao
        ? `Decisão mais recente: ${stj.ultima_decisao}`
        : 'Atualização não publicada.',
      limitation: 'Só aparece quando há correspondência publicada no corpus do STJ.',
      href: 'processo',
    },
  ];
}
