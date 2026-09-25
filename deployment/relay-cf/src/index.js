const ALLOWED_HOST_SUFFIXES = [".stj.jus.br", ".tjro.jus.br"];
const ALLOWED_METHODS = new Set(["GET", "HEAD", "POST"]);
// authorization/cookie: no caller through this relay authenticates to
// STJ/TJRO with either (auth is x-relay-token to the Worker itself), so
// forwarding them would only leak a caller's own credentials to whatever
// host the allowlist permits (TM-02 / #1609).
const STRIP_REQUEST_HEADERS = new Set([
  "authorization",
  "connection",
  "content-length",
  "cookie",
  "forwarded",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "true-client-ip",
  "upgrade",
]);
// set-cookie: no upstream in the allowlist is a session-bearing site the
// caller should start trusting cookies from (TM-02 / #1609).
const STRIP_RESPONSE_HEADERS = new Set([
  "connection",
  "content-length",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "set-cookie",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

// TM-02 / #1609: a relay with no budget lets a stolen token or misbehaving
// upstream exhaust the Worker's memory. These are generous (real DJEN/
// STJ/TJRO payloads are small JSON/HTML documents) but bounded.
export const MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024; // 10 MiB
export const MAX_RESPONSE_BYTES = 25 * 1024 * 1024; // 25 MiB

/**
 * Reads *stream* fully, returning its bytes as a `Uint8Array` — or `null`
 * if the stream carries more than *maxBytes*, without buffering past that
 * point.
 */
export async function readBounded(stream, maxBytes) {
  if (!stream) return new Uint8Array(0);

  const reader = stream.getReader();
  const chunks = [];
  let received = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      received += value.byteLength;
      if (received > maxBytes) return null;
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }

  const body = new Uint8Array(received);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return body;
}

export function hostAllowed(hostname) {
  const normalized = hostname.toLowerCase();
  return ALLOWED_HOST_SUFFIXES.some((suffix) => normalized.endsWith(suffix));
}

export async function verifyToken(provided, expected) {
  if (!provided || !expected) return false;

  const encoder = new TextEncoder();
  const [providedHash, expectedHash] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(provided)),
    crypto.subtle.digest("SHA-256", encoder.encode(expected)),
  ]);
  return crypto.subtle.timingSafeEqual(providedHash, expectedHash);
}

function shouldStripRequestHeader(name) {
  const normalized = name.toLowerCase();
  return (
    STRIP_REQUEST_HEADERS.has(normalized) ||
    normalized.startsWith("cf-") ||
    normalized.startsWith("x-forwarded-") ||
    normalized.startsWith("x-relay-")
  );
}

function plainText(message, status, extraHeaders = {}) {
  return new Response(message, {
    status,
    headers: {
      "cache-control": "no-store",
      "content-type": "text/plain; charset=utf-8",
      ...extraHeaders,
    },
  });
}

export async function handleRequest(
  request,
  env,
  fetchImpl = fetch,
  limits = { maxRequestBytes: MAX_REQUEST_BODY_BYTES, maxResponseBytes: MAX_RESPONSE_BYTES },
) {
  const suppliedToken = request.headers.get("x-relay-token");
  if (!(await verifyToken(suppliedToken, env.RELAY_TOKEN))) {
    return plainText("unauthorized", 401);
  }

  if (!ALLOWED_METHODS.has(request.method)) {
    return plainText("method not allowed", 405, { allow: "GET, HEAD, POST" });
  }

  const targetUrl = request.headers.get("x-relay-url");
  if (!targetUrl) return plainText("missing X-Relay-Url", 400);

  let target;
  try {
    target = new URL(targetUrl);
  } catch {
    return plainText("invalid X-Relay-Url", 400);
  }

  if (
    target.protocol !== "https:" ||
    target.username ||
    target.password ||
    !hostAllowed(target.hostname)
  ) {
    return plainText("target not allowed", 403);
  }

  const requestBody = ["GET", "HEAD"].includes(request.method)
    ? undefined
    : await readBounded(request.body, limits.maxRequestBytes);
  if (requestBody === null) {
    return plainText("request body too large", 413);
  }

  const upstreamHeaders = new Headers();
  for (const [name, value] of request.headers) {
    if (!shouldStripRequestHeader(name)) upstreamHeaders.set(name, value);
  }

  try {
    const upstream = await fetchImpl(target.toString(), {
      method: request.method,
      headers: upstreamHeaders,
      body: requestBody,
      redirect: "manual",
    });

    const responseBody = await readBounded(upstream.body, limits.maxResponseBytes);
    if (responseBody === null) {
      return plainText("upstream response too large", 502);
    }

    const responseHeaders = new Headers();
    for (const [name, value] of upstream.headers) {
      if (!STRIP_RESPONSE_HEADERS.has(name.toLowerCase())) {
        responseHeaders.set(name, value);
      }
    }
    responseHeaders.set("cache-control", "no-store");

    console.log(
      JSON.stringify({
        event: "relay_upstream_response",
        host: target.hostname,
        method: request.method,
        status: upstream.status,
      }),
    );

    return new Response(responseBody, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error(
      JSON.stringify({
        event: "relay_upstream_error",
        host: target.hostname,
        method: request.method,
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
