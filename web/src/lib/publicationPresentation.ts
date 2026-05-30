import type { DjenPublication } from "./djen";

export interface HighlightTerm {
  text: string;
  type: "party" | "lawyer" | "search";
}

export interface HighlightSegment {
  token: string;
  type?: HighlightTerm["type"];
}

export interface MetaChip {
  label: string;
  value: string;
  tone?: "default" | "accent" | "success" | "warning" | "danger";
}

export function formatProcessNumber(raw: string | undefined | null): string | null {
  if (!raw) return null;
  if (raw.includes("-")) return raw;
  const digits = raw.replace(/\D/g, "");
  if (digits.length === 20) {
    return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9, 13)}.${digits.slice(13, 14)}.${digits.slice(14, 16)}.${digits.slice(16, 20)}`;
  }
  return raw;
}

export function parseText(text: string | undefined | null): string[] {
  if (!text) return [];
  const markers =
    /(?=(?:Processo\s*:|Classe\s*:|INTIMA(?:ÇÃO|CAO)|CITA(?:ÇÃO|CAO)|DESPACHO|DECIS(?:ÃO|AO)|SENTEN(?:ÇA|CA)|EDITAL|Designada\s+AUDI(?:ÊNCIA|ENCIA)|DATA\s+E\s+HORA))/gi;
  const parts = text
    .split(markers)
    .map((part) => part.trim())
    .filter(Boolean);
  return parts.length > 1 ? parts : [text];
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function highlightText(part: string, terms: HighlightTerm[]): HighlightSegment[] {
  const cleanedTerms = terms
    .map((term) => ({ ...term, text: term.text.trim() }))
    .filter((term) => term.text.length > 1);

  if (cleanedTerms.length === 0) {
    return [{ token: part }];
  }

  const sortedTerms = [...cleanedTerms].sort((a, b) => b.text.length - a.text.length);
  const termMap = new Map<string, HighlightTerm["type"]>();
  sortedTerms.forEach((term) => termMap.set(term.text.toLowerCase(), term.type));

  const pattern = sortedTerms.map((term) => escapeRegExp(term.text)).join("|");
  const regex = new RegExp(`(${pattern})`, "gi");

  return part.split(regex).map((token) => {
    const type = termMap.get(token.toLowerCase());
    return type ? { token, type } : { token };
  });
}

export function buildEntityTerms(pub: DjenPublication): HighlightTerm[] {
  const terms: HighlightTerm[] = [];

  pub.destinatarios?.forEach((destinatario) => {
    if (destinatario.nome && destinatario.nome.length > 3) {
      terms.push({ text: destinatario.nome, type: "party" });
    }
  });

  pub.destinatarioadvogados?.forEach((entry) => {
    if (entry.advogado?.nome && entry.advogado.nome.length > 3) {
      terms.push({ text: entry.advogado.nome, type: "lawyer" });
    }
  });

  return terms;
}

export function buildSearchTerms(values: Array<string | undefined | null>): HighlightTerm[] {
  const seen = new Set<string>();
  const terms: HighlightTerm[] = [];

  values.forEach((value) => {
    const text = value?.trim();
    if (!text || text.length <= 1) return;
    const key = text.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    terms.push({ text, type: "search" });
  });

  return terms;
}

export function previewText(text: string | undefined, limit = 320): string | null {
  if (!text) return null;
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (cleaned.length <= limit) return cleaned;
  return `${cleaned.slice(0, limit).trimEnd()}...`;
}

export function htmlToPreviewText(html: string | undefined, limit = 320): string | null {
  if (!html) return null;

  const text = html
    .replace(/<br\s*\/?>/gi, " ")
    .replace(/<\/(p|div|li|tr|td|th|h[1-6])>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'");

  return previewText(text, limit);
}

function summarizeMedium(pub: DjenPublication): string | null {
  if (pub.meiocompleto) return pub.meiocompleto;
  if (pub.meio === "D") return "Diário Eletrônico";
  if (pub.meio === "E") return "Edital";
  return null;
}

function summarizeStatus(pub: DjenPublication): MetaChip | null {
  if (pub.ativo === false || pub.motivo_cancelamento) {
    return { label: "Status", value: "Cancelada", tone: "danger" };
  }
  if (pub.status === "P") {
    return { label: "Status", value: "Publicada", tone: "success" };
  }
  if (pub.status) {
    return { label: "Status", value: pub.status, tone: "warning" };
  }
  if (pub.ativo === true) {
    return { label: "Status", value: "Ativa", tone: "success" };
  }
  return null;
}

export function buildMetaChips(pub: DjenPublication): MetaChip[] {
  const chips: MetaChip[] = [];
  const statusChip = summarizeStatus(pub);
  const medium = summarizeMedium(pub);

  if (statusChip) chips.push(statusChip);
  if (pub.siglaTribunal) chips.push({ label: "Tribunal", value: pub.siglaTribunal });
  if (medium) chips.push({ label: "Meio", value: medium, tone: "accent" });
  if (pub.nomeClasse) chips.push({ label: "Classe", value: pub.nomeClasse });
  if (pub.tipoDocumento) chips.push({ label: "Documento", value: pub.tipoDocumento });
  if (pub.numeroComunicacao != null) {
    chips.push({ label: "Comunicação", value: String(pub.numeroComunicacao) });
  }

  return chips;
}

export function buildIdentityRows(pub: DjenPublication): MetaChip[] {
  const rows: MetaChip[] = [];

  if (pub.data_disponibilizacao) {
    rows.push({ label: "Disponibilização", value: pub.data_disponibilizacao });
  }
  if (pub.codigoClasse) {
    rows.push({ label: "Código da classe", value: pub.codigoClasse });
  }
  if (pub.hash) {
    rows.push({ label: "Hash", value: pub.hash.slice(0, 16) });
  }
  if (pub.numeroprocessocommascara && pub.numeroprocessocommascara !== pub.numero_processo) {
    rows.push({ label: "Processo mascarado", value: pub.numeroprocessocommascara });
  }

  return rows;
}

export function uniquePartyNames(pub: DjenPublication): string[] {
  const seen = new Set<string>();
  const names: string[] = [];

  pub.destinatarios?.forEach((destinatario) => {
    if (!destinatario.nome) return;
    const key = destinatario.nome.trim().toLowerCase();
    if (!key || seen.has(key)) return;
    seen.add(key);
    names.push(destinatario.nome);
  });

  return names;
}

export function uniqueLawyers(pub: DjenPublication): string[] {
  const seen = new Set<string>();
  const lawyers: string[] = [];

  pub.destinatarioadvogados?.forEach((entry) => {
    const advogado = entry.advogado;
    if (!advogado?.nome) return;
    const oab = advogado.numero_oab ? `OAB ${advogado.uf_oab ?? ""} ${advogado.numero_oab}`.trim() : null;
    const label = oab ? `${advogado.nome} (${oab})` : advogado.nome;
    const key = label.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    lawyers.push(label);
  });

  return lawyers;
}
