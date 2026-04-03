import { useState } from 'preact/compat';
import type { ComponentChildren } from 'preact';

interface Publication {
  id?: string;
  numero_processo?: string;
  tipoComunicacao?: string;
  nomeOrgao?: string;
  texto?: string;
  destinatarios?: { nome: string }[];
  destinatarioadvogados?: { advogado?: { nome?: string; numero_oab?: string; uf_oab?: string } }[];
}

/**
 * Format a raw process number into the standard CNJ pattern.
 * Input:  "7019279602020822001" or "70192796020208220001"
 * Output: "7019279-60.2020.8.22.0001"
 * Pattern: NNNNNNN-DD.AAAA.J.TR.OOOO
 */
function formatProcessNumber(raw: string | undefined | null): string | null {
  if (!raw) return null;
  // Already formatted
  if (raw.includes('-')) return raw;
  // Remove non-digits
  const digits = raw.replace(/\D/g, '');
  if (digits.length === 20) {
    return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9, 13)}.${digits.slice(13, 14)}.${digits.slice(14, 16)}.${digits.slice(16, 20)}`;
  }
  return raw;
}

/**
 * Parse publication text into structured paragraphs.
 * Breaks before common markers like "Processo:", "Classe:", "INTIMACAO", etc.
 */
function parseText(text: string | undefined | null): string[] {
  if (!text) return [];
  // Split on common legal document markers
  const markers = /(?=(?:Processo\s*:|Classe\s*:|INTIMA[CÇ][AÃ]O|CITA[CÇ][AÃ]O|DESPACHO|DECIS[AÃ]O|SENTEN[CÇ]A|EDITAL|Designada\s+AUDI[EÊ]NCIA|DATA\s+E\s+HORA))/gi;
  const parts = text.split(markers).map(p => p.trim()).filter(Boolean);
  return parts.length > 1 ? parts : [text];
}

function ShareIcon() {
  return (
    <svg className="w-3.5 h-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
    </svg>
  );
}

interface ShareButtonProps {
  dateStr: string;
  page?: number;
  seq?: number;
  label?: string;
}

function ShareButton({ dateStr, page, seq, label }: ShareButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleClick = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const base = window.location.pathname;
    let hash = dateStr;
    if (page) hash += `/${page}`;
    if (seq) hash += `/${seq}`;
    const url = `${window.location.origin}${base}#${hash}`;
    navigator.clipboard?.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-accent transition-colors px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-slate-800"
      title="Copiar link"
    >
      <ShareIcon />
      {copied ? 'Copiado!' : (label || 'Link')}
    </button>
  );
}

interface NavButtonProps {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}

function NavButton({ label, onClick, disabled }: NavButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="text-xs text-gray-400 hover:text-accent transition-colors disabled:opacity-30 disabled:cursor-default px-2 py-1"
    >
      {label}
    </button>
  );
}

interface PublicationCardProps {
  pub: Publication;
  seq: number;
  dateStr: string;
  page?: number;
  compact?: boolean;
  totalSeq?: number;
  onNavigate?: (newSeq: number) => void;
}

export function PublicationCard({ pub, seq, dateStr, page, compact = false, totalSeq, onNavigate }: PublicationCardProps) {
  const processNumber = formatProcessNumber(pub.numero_processo);

  if (compact) {
    return (
      <div id={`pub-${seq}`} className="card p-4 transition-all duration-300">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex-1 min-w-0 flex items-center gap-2.5">
            <span className="text-xs text-gray-300 dark:text-gray-600 font-mono">{seq}</span>
            {processNumber && (
              <span className="font-mono text-sm text-accent font-medium">{processNumber}</span>
            )}
            {pub.tipoComunicacao && (
              <span className="text-xs font-bold px-2 py-1 rounded bg-gray-100 dark:bg-slate-800 text-gray-500 leading-none">
                {pub.tipoComunicacao}
              </span>
            )}
          </div>
          <ShareButton dateStr={dateStr} page={page} seq={seq} />
        </div>
        {pub.nomeOrgao && (
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">{pub.nomeOrgao}</div>
        )}
        {pub.texto && (
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            {pub.texto.length > 500 ? pub.texto.substring(0, 500) + '...' : pub.texto}
          </p>
        )}
        {pub.destinatarios?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2.5">
            {pub.destinatarios.map((d, j) => (
              <span key={j} className="text-xs bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 px-2 py-1 rounded leading-none">
                {d.nome}
              </span>
            ))}
          </div>
        )}
        {pub.destinatarioadvogados?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {pub.destinatarioadvogados.map((da, j) => (
              <span key={j} className="text-xs bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 px-2 py-1 rounded leading-none">
                {da.advogado?.nome} {da.advogado?.numero_oab && `(OAB ${da.advogado.uf_oab} ${da.advogado.numero_oab})`}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Full / featured view
  const textParts = parseText(pub.texto);

  return (
    <div id={`pub-${seq}`} className="card p-6 border-2 border-accent bg-accent/5 dark:bg-accent/10">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold px-2 py-1 rounded bg-accent text-white">
            #{seq}
          </span>
          {pub.tipoComunicacao && (
            <span className="text-xs font-bold px-2 py-1 rounded bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-400">
              {pub.tipoComunicacao}
            </span>
          )}
          <span className="text-xs text-gray-400 font-mono">{dateStr}</span>
        </div>
        <div className="flex items-center gap-1">
          {onNavigate && (
            <>
              <NavButton label="Anterior" onClick={() => onNavigate(seq - 1)} disabled={seq <= 1} />
              <NavButton label="Proxima" onClick={() => onNavigate(seq + 1)} disabled={totalSeq != null && seq >= totalSeq} />
            </>
          )}
          <ShareButton dateStr={dateStr} page={page} seq={seq} label="Compartilhar" />
        </div>
      </div>

      {processNumber && (
        <div className="font-mono text-accent font-bold mb-2 text-lg">{processNumber}</div>
      )}
      {pub.nomeOrgao && (
        <div className="text-sm text-gray-600 dark:text-gray-400 mb-3">{pub.nomeOrgao}</div>
      )}

      {textParts.length > 0 && (
        <div className="space-y-3 mb-4">
          {textParts.map((part, i) => (
            <p key={i} className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
              {part}
            </p>
          ))}
        </div>
      )}

      {pub.destinatarios?.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 uppercase font-bold mb-1.5">Destinatarios</div>
          <div className="flex flex-wrap gap-1.5">
            {pub.destinatarios.map((d, j) => (
              <span key={j} className="text-xs bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded">
                {d.nome}
              </span>
            ))}
          </div>
        </div>
      )}
      {pub.destinatarioadvogados?.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 uppercase font-bold mb-1.5">Advogados</div>
          <div className="flex flex-wrap gap-1.5">
            {pub.destinatarioadvogados.map((da, j) => (
              <span key={j} className="text-xs bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 px-2 py-0.5 rounded">
                {da.advogado?.nome} {da.advogado?.numero_oab && `(OAB ${da.advogado.uf_oab} ${da.advogado.numero_oab})`}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
