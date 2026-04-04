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
      className="outline secondary text-xs px-sm py-xs d-inline-flex align-center gap-xs"
      onClick={handleClick}
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
      className="secondary outline text-xs px-sm py-xs"
      onClick={onClick}
      disabled={disabled}
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
  const [isReaderMode, setIsReaderMode] = useState(false);
  const processNumber = formatProcessNumber(pub.numero_processo);

  if (compact) {
    return (
      <article id={`pub-${seq}`} className="p-md">
        <header className="flex-between align-center border-bottom pb-sm mb-sm flex-wrap gap-sm">
          <div className="flex flex-column gap-xs">
            <div className="flex align-center gap-sm flex-wrap">
              <span className="font-mono text-xs text-muted">#{seq}</span>
              {pub.tipoComunicacao && (
                <span className="badge">{pub.tipoComunicacao}</span>
              )}
            </div>
            {processNumber && (
              <span className="text-accent text-md font-semibold font-mono">{processNumber}</span>
            )}
          </div>
          <ShareButton dateStr={dateStr} page={page} seq={seq} />
        </header>
        {pub.nomeOrgao && (
          <small className="text-primary font-medium text-xs d-block mb-sm">{pub.nomeOrgao}</small>
        )}
        {pub.texto && (
          <p className="text-sm text-secondary" style={{ lineHeight: '1.6' }}>
            {pub.texto.length > 300 ? pub.texto.substring(0, 300) + '...' : pub.texto}
          </p>
        )}
        {pub.destinatarios?.length > 0 && (
          <div className="flex flex-wrap gap-xs">
            {pub.destinatarios.map((d, j) => (
              <span key={j} className="badge">{d.nome}</span>
            ))}
          </div>
        )}
        {pub.destinatarioadvogados?.length > 0 && (
          <div className="flex flex-wrap gap-xs mt-xs">
            {pub.destinatarioadvogados.map((da, j) => (
              <span key={j} className="text-xs text-muted">
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

  if (isReaderMode) {
    return (
      <article id={`pub-${seq}`} className="reader-mode p-lg">
        <header className="flex-between flex-wrap gap-sm border-bottom pb-sm mb-md align-center">
          <div className="flex align-center flex-wrap gap-sm">
            <span className="font-mono text-xs font-semibold text-muted">#{seq}</span>
            <span className="badge">Modo Leitura</span>
            <small className="text-muted text-xs">{dateStr}</small>
          </div>
          <div role="group" aria-label="Ações de navegação e leitura" className="flex align-center gap-xs">
            <button
              className="outline secondary text-xs px-sm py-xs d-inline-flex align-center gap-xs touch-target-24"
              onClick={() => setIsReaderMode(false)}
              title="Sair do Modo Leitura"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Voltar
            </button>
            <ShareButton dateStr={dateStr} page={page} seq={seq} label="Compartilhar" />
          </div>
        </header>

        {processNumber && (
          <h2 className="text-accent text-xl font-semibold font-mono mb-xs">{processNumber}</h2>
        )}
        {pub.nomeOrgao && (
          <p className="text-muted text-sm mb-lg">{pub.nomeOrgao}</p>
        )}

        <div className="ai-summary-placeholder p-md mb-lg border rounded bg-surface-overlay">
          <div className="flex align-center gap-sm mb-xs">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="var(--accent-gold)" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <strong className="text-sm uppercase tracking-wide text-accent">Resumo com IA (Em breve)</strong>
          </div>
          <p className="text-sm text-secondary m-0">
            Esta seção fornecerá um resumo em linguagem clara da decisão e seu resultado.
          </p>
        </div>

        <div className="reader-content pt-md">
          {textParts.length > 0 && (
            <div className="reader-text">
              {textParts.map((part, i) => {
                // Build a list of highlight terms
                const terms: { text: string; type: 'party' | 'lawyer' }[] = [];
                if (pub.destinatarios) {
                  pub.destinatarios.forEach(d => {
                    if (d.nome && d.nome.length > 3) {
                      terms.push({ text: d.nome, type: 'party' });
                    }
                  });
                }
                if (pub.destinatarioadvogados) {
                  pub.destinatarioadvogados.forEach(da => {
                    if (da.advogado?.nome && da.advogado.nome.length > 3) {
                      terms.push({ text: da.advogado.nome, type: 'lawyer' });
                    }
                  });
                }

                if (terms.length === 0) {
                  return <p key={i} className="text-md text-primary" style={{ lineHeight: '1.8', marginBottom: '1.5em' }}>{part}</p>;
                }

                // Escape regex special characters safely
                const escapeRegExp = (string: string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

                // Sort terms by length descending to match longest phrases first
                terms.sort((a, b) => b.text.length - a.text.length);

                const termMap = new Map<string, 'party' | 'lawyer'>();
                terms.forEach(t => termMap.set(t.text.toLowerCase(), t.type));

                const pattern = terms.map(t => escapeRegExp(t.text)).join('|');
                const regex = new RegExp(`(${pattern})`, 'gi');

                const tokens = part.split(regex);

                return (
                  <p key={i} className="text-md text-primary" style={{ lineHeight: '1.8', marginBottom: '1.5em' }}>
                    {tokens.map((token, j) => {
                      const type = termMap.get(token.toLowerCase());
                      if (type) {
                        return <mark key={j} className={type === 'party' ? 'entity-party' : 'entity-lawyer'}>{token}</mark>;
                      }
                      return token;
                    })}
                  </p>
                );
              })}
            </div>
          )}
        </div>
      </article>
    );
  }

  return (
    <article id={`pub-${seq}`} className="p-lg">
      <header className="flex-between flex-wrap gap-sm border-bottom pb-sm mb-md align-center">
        <div className="flex align-center flex-wrap gap-sm">
          <span className="font-mono text-xs font-semibold text-muted">#{seq}</span>
          {pub.tipoComunicacao && (
            <span className="badge">{pub.tipoComunicacao}</span>
          )}
          <small className="text-muted text-xs">{dateStr}</small>
        </div>
        <div role="group" aria-label="Ações de navegação e leitura" className="flex align-center gap-xs flex-wrap">
          <button
            className="outline primary text-xs px-sm py-xs d-inline-flex align-center gap-xs touch-target-24"
            onClick={() => setIsReaderMode(true)}
            title="Abrir Modo Leitura"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            Modo Leitura
          </button>
          <div role="group" aria-label="Ações de navegação" className="flex align-center gap-xs">
            {onNavigate && (
              <>
                <NavButton label="Anterior" onClick={() => onNavigate(seq - 1)} disabled={seq <= 1} />
                <NavButton label="Próxima" onClick={() => onNavigate(seq + 1)} disabled={totalSeq != null && seq >= totalSeq} />
              </>
            )}
            <ShareButton dateStr={dateStr} page={page} seq={seq} label="Compartilhar" />
          </div>
        </div>
      </header>

      {processNumber && (
        <div className="text-accent text-md font-semibold font-mono mb-sm">{processNumber}</div>
      )}
      {pub.nomeOrgao && (
        <small className="d-block text-muted text-xs mb-md">{pub.nomeOrgao}</small>
      )}

      {textParts.length > 0 && (
        <div className="border-top pt-md">
          {textParts.map((part, i) => (
            <p key={i} className="text-sm text-secondary" style={{ lineHeight: '1.7' }}>
              {part}
            </p>
          ))}
        </div>
      )}

      {pub.destinatarios?.length > 0 && (
        <footer className="border-top pt-md mt-sm">
          <strong className="text-xs uppercase tracking-wide text-muted d-block mb-xs">Destinatários</strong>
          <div className="flex flex-wrap gap-xs">
            {pub.destinatarios.map((d, j) => (
              <span key={j} className="badge">{d.nome}</span>
            ))}
          </div>
        </footer>
      )}
      {pub.destinatarioadvogados?.length > 0 && (
        <footer className="border-top pt-md mt-sm">
          <strong className="text-xs uppercase tracking-wide text-muted d-block mb-xs">Advogados</strong>
          <div className="flex flex-wrap gap-xs">
            {pub.destinatarioadvogados.map((da, j) => (
              <span key={j} className="text-sm text-secondary">
                {da.advogado?.nome} {da.advogado?.numero_oab && `(OAB ${da.advogado.uf_oab} ${da.advogado.numero_oab})`}
              </span>
            ))}
          </div>
        </footer>
      )}
    </article>
  );
}
