/**
 * "Copiar referência" (issue #1135): produz um bloco de texto puro, curto e
 * estável a partir da proveniência já exibida no dossiê /processo — para
 * reuso em petições, notas técnicas e compartilhamento entre pessoas/agentes.
 *
 * Regra central: nunca inventar um campo ausente. Uma linha só aparece
 * quando o dado correspondente existe; a URL de origem preservada/oficial
 * fica sempre distinguível da URL da própria página do CausaGanha, que é
 * apenas contexto secundário.
 */

export interface ProcessoReferenceInput {
  nrProcessoMascara: string;
  fontesPresentes: string[];
  datasetGeradoEm: string | null;
  origemUrl: string;
  causaganhaUrl: string;
}

export function buildProcessoReferenceText(input: ProcessoReferenceInput): string {
  const lines = [
    `CausaGanha — dossiê do processo ${input.nrProcessoMascara}`,
    `Fontes com registro: ${input.fontesPresentes.length > 0 ? input.fontesPresentes.join(', ') : 'nenhuma fonte com registro neste snapshot'}`,
  ];
  if (input.datasetGeradoEm) {
    lines.push(`Dataset gerado em: ${input.datasetGeradoEm}`);
  }
  lines.push(`Origem preservada (índice processual reconciliado): ${input.origemUrl}`);
  lines.push(`Referência CausaGanha: ${input.causaganhaUrl}`);
  return lines.join('\n');
}

export interface DocumentoReferenceInput {
  fonteLabel: string;
  nrProcessoMascara: string;
  tipo: string | null;
  data: string | null;
  url: string;
  causaganhaUrl: string;
}

export function buildDocumentoReferenceText(input: DocumentoReferenceInput): string {
  const lines = [
    `CausaGanha — ${input.tipo ?? 'documento'} (${input.fonteLabel}) do processo ${input.nrProcessoMascara}`,
  ];
  if (input.data) {
    lines.push(`Data: ${input.data}`);
  }
  lines.push(`Origem: ${input.url}`);
  lines.push(`Referência CausaGanha: ${input.causaganhaUrl}`);
  return lines.join('\n');
}
