import { useState } from 'preact/compat';

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
  if (raw.includes('-')) return raw;
  const digits = raw.replace(/\D/g, '');
  if (digits.length === 20) {
    return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9, 13)}.${digits.slice(13, 14)}.${digits.slice(14, 16)}.${digits.slice(16, 20)}`;
  }
  return raw;
}

/**
 * Parse publication text into structured paragraphs.
 */
function parseText(text: string | undefined | null): string[] {
  if (!text) return [];
  const markers = /(?=(?:Processo\s*:|Classe\s*:|INTIMA[CÇ][AÃ]O|CITA[CÇ][AÃ]O|DESPACHO|DECIS[AÃ]O|SENTEN[CÇ]A|EDITAL|Designada\s+AUDI[EÊ]NCIA|DATA\s+E\s+HORA))/gi;
  const parts = text.split(markers).map(p => p.trim()).filter(Boolean);
  return parts.length > 1 ? parts : [text];
}

function ShareIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
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
      className="outline secondary"
      onClick={handleClick}
      title="Copiar link"
      style={{ fontSize: 'var(--font-size-xs)', padding: '0.4rem 0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
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
      className="secondary outline"
      onClick={onClick}
      disabled={disabled}
      style={{ fontSize: 'var(--font-size-xs)', padding: '0.4rem 0.75rem' }}
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
      <article id={`pub-${seq}`} style={{ padding: 'var(--space-md)' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--color-border-muted)', paddingBottom: 'var(--space-sm)', marginBottom: 'var(--space-sm)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 'var(--font-size-xs)', color: 'var(--color-content-tertiary)' }}>#{seq}</span>
            {processNumber && (
              <span className="text-accent" style={{ fontSize: 'var(--font-size-sm)', fontWeight: '600' }}>{processNumber}</span>
            )}
            {pub.tipoComunicacao && (
              <span className="badge">{pub.tipoComunicacao}</span>
            )}
          </div>
          <ShareButton dateStr={dateStr} page={page} seq={seq} />
        </header>
        {pub.nomeOrgao && (
          <small style={{ color: 'var(--color-content-tertiary)', fontSize: 'var(--font-size-xs)', display: 'block', marginBottom: 'var(--space-sm)' }}>{pub.nomeOrgao}</small>
        )}
        {pub.texto && (
          <p style={{ fontSize: 'var(--font-size-sm)', lineHeight: '1.6', color: 'var(--color-content-secondary)' }}>
            {pub.texto.length > 500 ? pub.texto.substring(0, 500) + '...' : pub.texto}
          </p>
        )}
        {pub.destinatarios?.length > 0 && (
          <div style={{ display: 'flex', gap: 'var(--space-xs)', flexWrap: 'wrap' }}>
            {pub.destinatarios.map((d, j) => (
              <span key={j} className="badge">{d.nome}</span>
            ))}
          </div>
        )}
        {pub.destinatarioadvogados?.length > 0 && (
          <div style={{ display: 'flex', gap: 'var(--space-xs)', flexWrap: 'wrap', marginTop: 'var(--space-xs)' }}>
            {pub.destinatarioadvogados.map((da, j) => (
              <span key={j} style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-content-tertiary)' }}>
                {da.advogado?.nome} {da.advogado?.numero_oab && `(OAB ${da.advogado.uf_oab} ${da.advogado.numero_oab})`}
              </span>
            ))}
          </div>
        )}
      </article>
    );
  }

  // Full / featured view
  const textParts = parseText(pub.texto);

  return (
    <article id={`pub-${seq}`} style={{ padding: 'var(--space-lg)' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--color-border-muted)', paddingBottom: 'var(--space-sm)', marginBottom: 'var(--space-md)', flexWrap: 'wrap', gap: 'var(--space-sm)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 'var(--font-size-xs)', fontWeight: '600', color: 'var(--color-content-tertiary)' }}>#{seq}</span>
          {pub.tipoComunicacao && (
            <span className="badge">{pub.tipoComunicacao}</span>
          )}
          <small style={{ color: 'var(--color-content-tertiary)', fontSize: 'var(--font-size-xs)' }}>{dateStr}</small>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-xs)', alignItems: 'center' }}>
          {onNavigate && (
            <>
              <NavButton label="Anterior" onClick={() => onNavigate(seq - 1)} disabled={seq <= 1} />
              <NavButton label="Próxima" onClick={() => onNavigate(seq + 1)} disabled={totalSeq != null && seq >= totalSeq} />
            </>
          )}
          <ShareButton dateStr={dateStr} page={page} seq={seq} label="Compartilhar" />
        </div>
      </header>

      {processNumber && (
        <div className="text-accent" style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', fontFamily: "'JetBrains Mono', monospace", marginBottom: 'var(--space-sm)' }}>{processNumber}</div>
      )}
      {pub.nomeOrgao && (
        <small style={{ display: 'block', color: 'var(--color-content-tertiary)', fontSize: 'var(--font-size-xs)', marginBottom: 'var(--space-md)' }}>{pub.nomeOrgao}</small>
      )}

      {textParts.length > 0 && (
        <div style={{ borderTop: '1px solid var(--color-border-muted)', paddingTop: 'var(--space-md)' }}>
          {textParts.map((part, i) => (
            <p key={i} style={{ fontSize: 'var(--font-size-sm)', lineHeight: '1.7', color: 'var(--color-content-secondary)' }}>
              {part}
            </p>
          ))}
        </div>
      )}

      {pub.destinatarios?.length > 0 && (
        <footer style={{ borderTop: '1px solid var(--color-border-muted)', paddingTop: 'var(--space-md)', marginTop: 'var(--space-sm)' }}>
          <strong style={{ fontSize: 'var(--font-size-xs)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-content-tertiary)', display: 'block', marginBottom: 'var(--space-xs)' }}>Destinatários</strong>
          <div style={{ display: 'flex', gap: 'var(--space-xs)', flexWrap: 'wrap' }}>
            {pub.destinatarios.map((d, j) => (
              <span key={j} className="badge">{d.nome}</span>
            ))}
          </div>
        </footer>
      )}
      {pub.destinatarioadvogados?.length > 0 && (
        <footer style={{ borderTop: '1px solid var(--color-border-muted)', paddingTop: 'var(--space-md)', marginTop: 'var(--space-sm)' }}>
          <strong style={{ fontSize: 'var(--font-size-xs)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-content-tertiary)', display: 'block', marginBottom: 'var(--space-xs)' }}>Advogados</strong>
          <div style={{ display: 'flex', gap: 'var(--space-xs)', flexWrap: 'wrap' }}>
            {pub.destinatarioadvogados.map((da, j) => (
              <span key={j} style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-content-secondary)' }}>
                {da.advogado?.nome} {da.advogado?.numero_oab && `(OAB ${da.advogado.uf_oab} ${da.advogado.numero_oab})`}
              </span>
            ))}
          </div>
        </footer>
      )}
    </article>
  );
}
