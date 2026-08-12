const ALLOWED_HOST_SUFFIXES = [".stj.jus.br", ".tjro.jus.br"];
const ALLOWED_METHODS = new Set(["GET", "HEAD", "POST"]);
const STRIP_REQUEST_HEADERS = new Set([
  "connection",
  "content-length",
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
const STRIP_RESPONSE_HEADERS = new Set([
  "connection",
  "content-length",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

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

export async function handleRequest(request, env, fetchImpl = fetch) {
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

  const upstreamHeaders = new Headers();
  for (const [name, value] of request.headers) {
    if (!shouldStripRequestHeader(name)) upstreamHeaders.set(name, value);
  }

  try {
    const upstream = await fetchImpl(target.toString(), {
      method: request.method,
      headers: upstreamHeaders,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "manual",
    });

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

    return new Response(upstream.body, {
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
