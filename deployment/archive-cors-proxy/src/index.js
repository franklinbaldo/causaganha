const ALLOWED_METHODS = new Set(["GET", "HEAD"]);
const ITEM_PATTERN = /^djen-[a-z0-9-]+$/i;
const DOWNLOAD_PATH_PATTERN = /^\/download\/([^/]+)\/([^/]+)$/;
const UPSTREAM_BASE = "https://archive.org";

const STRIP_RESPONSE_HEADERS = new Set([
  "connection",
  "content-length",
  "keep-alive",
  "transfer-encoding",
  "upgrade",
]);

const CORS_HEADERS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, HEAD, OPTIONS",
  "access-control-allow-headers": "range",
  "access-control-expose-headers": "accept-ranges, content-range, content-length, content-type, etag",
  "access-control-max-age": "86400",
};

export function parseDownloadPath(pathname) {
  const match = DOWNLOAD_PATH_PATTERN.exec(pathname);
  if (!match) return null;

  const [, item, file] = match;
  if (!ITEM_PATTERN.test(item)) return null;
  if (!file.toLowerCase().endsWith(".parquet")) return null;

  return { item, file };
}

function withCors(headers = {}) {
  return { ...CORS_HEADERS, ...headers };
}

function plainText(message, status, extraHeaders = {}) {
  return new Response(message, {
    status,
    headers: withCors({
      "cache-control": "no-store",
      "content-type": "text/plain; charset=utf-8",
      ...extraHeaders,
    }),
  });
}

export async function handleRequest(request, env, fetchImpl = fetch) {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: withCors() });
  }

  if (!ALLOWED_METHODS.has(request.method)) {
    return plainText("method not allowed", 405, { allow: "GET, HEAD, OPTIONS" });
  }

  const url = new URL(request.url);
  const parsed = parseDownloadPath(url.pathname);
  if (!parsed) {
    return plainText("not found", 404);
  }

  const upstreamHeaders = new Headers();
  const range = request.headers.get("range");
  if (range) upstreamHeaders.set("range", range);

  try {
    const upstream = await fetchImpl(`${UPSTREAM_BASE}/download/${parsed.item}/${parsed.file}`, {
      method: request.method,
      headers: upstreamHeaders,
      redirect: "follow",
    });

    const responseHeaders = new Headers();
    for (const [name, value] of upstream.headers) {
      if (!STRIP_RESPONSE_HEADERS.has(name.toLowerCase())) {
        responseHeaders.set(name, value);
      }
    }
    for (const [name, value] of Object.entries(CORS_HEADERS)) {
      responseHeaders.set(name, value);
    }
    responseHeaders.set("cache-control", "public, max-age=3600");

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error(
      JSON.stringify({
        event: "archive_cors_proxy_upstream_error",
        item: parsed.item,
        file: parsed.file,
        error: error instanceof Error ? error.name : "UnknownError",
      }),
    );
    return plainText("upstream error", 502);
  }
}

export default {
  fetch(request, env) {
    return handleRequest(request, env);
  },
};
