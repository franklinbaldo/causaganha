function withTrailingSlash(base: string): string {
  return base.endsWith('/') ? base : `${base}/`;
}

export function buildProcessoPermalink(base: string, cnj: string): string {
  const root = withTrailingSlash(base);
  const params = new URLSearchParams({ cnj });
  return `${root}processo?${params.toString()}`;
}

export function buildPublicacoesCnjUrl(base: string, cnj: string): string {
  const root = withTrailingSlash(base);
  const params = new URLSearchParams({ numeroProcesso: cnj });
  return `${root}publicacoes?${params.toString()}`;
}

export function absoluteUrl(relativeOrAbsolute: string, origin: string): string {
  return new URL(relativeOrAbsolute, origin).toString();
}
