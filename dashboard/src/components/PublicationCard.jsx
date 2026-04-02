import { useState } from 'preact/compat';

function copyToClipboard(text) {
  navigator.clipboard?.writeText(text);
}

export function PublicationCard({ pub, seq, dateStr, page, compact = false }) {
  const [copied, setCopied] = useState(false);

  const handleShare = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const base = window.location.pathname;
    const hash = `${dateStr}/${page || 1}/${seq}`;
    const url = `${window.location.origin}${base}#${hash}`;
    copyToClipboard(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (compact) {
    return (
      <div id={`pub-${seq}`} className="card p-4 transition-all duration-300">
        <div className="flex items-start justify-between gap-2 mb-1">
          <div className="flex-1 min-w-0 flex items-center gap-2">
            <span className="text-[9px] text-gray-300 dark:text-gray-600 font-mono">{seq}</span>
            {pub.numero_processo && (
              <span className="font-mono text-sm text-accent font-medium">{pub.numero_processo}</span>
            )}
            {pub.tipoComunicacao && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-gray-100 dark:bg-slate-800 text-gray-500">
                {pub.tipoComunicacao}
              </span>
            )}
          </div>
          <button onClick={handleShare} className="text-[10px] text-gray-400 hover:text-accent transition-colors">
            {copied ? 'Copiado!' : 'Link'}
          </button>
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
          <div className="flex flex-wrap gap-1 mt-2">
            {pub.destinatarios.map((d, j) => (
              <span key={j} className="text-[10px] bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded">
                {d.nome}
              </span>
            ))}
          </div>
        )}
        {pub.destinatarioadvogados?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {pub.destinatarioadvogados.map((da, j) => (
              <span key={j} className="text-[10px] bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 px-1.5 py-0.5 rounded">
                {da.advogado?.nome} {da.advogado?.numero_oab && `(OAB ${da.advogado.uf_oab} ${da.advogado.numero_oab})`}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Full / featured view
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
        <button onClick={handleShare} className="text-[10px] text-gray-400 hover:text-accent transition-colors">
          {copied ? 'Copiado!' : 'Compartilhar'}
        </button>
      </div>
      {pub.numero_processo && (
        <div className="font-mono text-accent font-bold mb-2">{pub.numero_processo}</div>
      )}
      {pub.nomeOrgao && (
        <div className="text-sm text-gray-600 dark:text-gray-400 mb-3">{pub.nomeOrgao}</div>
      )}
      {pub.texto && (
        <div className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-line mb-3">
          {pub.texto}
        </div>
      )}
      {pub.destinatarios?.length > 0 && (
        <div className="mb-2">
          <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">Destinatarios</div>
          <div className="flex flex-wrap gap-1">
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
          <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">Advogados</div>
          <div className="flex flex-wrap gap-1">
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
