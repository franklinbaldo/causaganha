/**
 * Typed DJEN HTTP client.
 *
 * This module owns the dual-base-URL strategy used to work around the
 * DJEN public API's geo-fence: requests try the direct CNJ endpoint first,
 * then fall back to the São Paulo Cloud Run proxy deployed from
 * `deployment/djen_proxy.go`. The outcome is remembered per browsing session
 * so non-Brazilian users do not pay the 10-second public-URL timeout on every
 * subsequent request.
 *
 * IMPORTANT: the proxy at `deployment/djen_proxy.go` whitelists path prefixes
 * `/api/`, `/swagger/`, `/comunicacao`, `/login`. All 7 spec endpoints are
 * under `/api/v1/`, so they are covered. If a new path is added to
 * `djen.yml` outside `/api/`, update the proxy whitelist in the same PR.
 */

import createClient, { type Client, type Middleware } from "openapi-fetch";
import type { paths } from "./djen-types.gen";
import { getApiV1ComunicacaoResponse } from "./djen-zod.gen";

// ---------- base URLs ------------------------------------------------------

export const DJEN_PUBLIC_BASE = "https://comunicaapi.pje.jus.br";
export const DJEN_PROXY_BASE = "https://djen-proxy-mhgmawcn3a-rj.a.run.app";

// ---------- types exposed to callers --------------------------------------

export type DjenPaths = paths;

/**
 * Query parameters for `GET /api/v1/comunicacao`.
 *
 * Derived from the OpenAPI spec and then extended with `texto`, which the
 * live CNJ API demonstrably accepts (and the frontend depends on) even though
 * the upstream `djen.yml` does not declare it as a query parameter. Treat any
 * extension here as "spec bug, verified against the live service".
 */
export type DjenComunicacaoQuery = NonNullable<
  paths["/api/v1/comunicacao"]["get"]["parameters"]["query"]
> & {
  /** Full-text search token. Accepted by the live API; missing from djen.yml. */
  texto?: string;
};

export type DjenComunicacaoItem = NonNullable<
  NonNullable<
    paths["/api/v1/comunicacao"]["get"]["responses"]["200"]["content"]["application/json"]["items"]
  >
>[number];

export type DjenTribunal = NonNullable<
  paths["/api/v1/comunicacao/tribunal"]["get"]["responses"]["200"]["content"]["application/json"]
>[number];

export type DjenCaderno = NonNullable<
  paths["/api/v1/caderno/{sigla_tribunal}/{data}/{meio}"]["get"]["responses"]["200"]["content"]["application/json"]
>;

export interface DjenRateLimit {
  limit: number | null;
  remaining: number | null;
  resetAt: number | null;
}

export type DjenCallSource = "direct" | "proxy";

export interface DjenCallResult<T> {
  data: T;
  rateLimit: DjenRateLimit;
  source: DjenCallSource;
  usedFallback: boolean;
}

// ---------- error classes --------------------------------------------------

export class DjenValidationError extends Error {
  issues: string[];
  constructor(issues: string[]) {
    super(`Consulta DJEN inválida: ${issues.join("; ")}`);
    this.name = "DjenValidationError";
    this.issues = issues;
  }
}

export class DjenRateLimitError extends Error {
  retryAfterSec: number;
  constructor(retryAfterSec: number) {
    super(`Limite de requisições atingido. Aguarde ${retryAfterSec}s.`);
    this.name = "DjenRateLimitError";
    this.retryAfterSec = retryAfterSec;
  }
}

/**
 * Thrown when a request fails with an HTTP status that isn't 429 (rate-limited)
 * and isn't a geo-block shape we should silently route through the proxy.
 * Callers can branch on `status` to display the real error rather than
 * masking backend issues behind the proxy fallback.
 */
export class DjenHttpError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown, message?: string) {
    super(message ?? `HTTP ${status}`);
    this.name = "DjenHttpError";
    this.status = status;
    this.body = body;
  }
}

// ---------- rate-limit middleware -----------------------------------------

const rateLimitBySignature = new Map<string, DjenRateLimit>();

function signatureFor(path: string, init: RequestInit | undefined): string {
  const method = (init?.method ?? "GET").toUpperCase();
  return `${method} ${path}`;
}

function parseRateLimitHeaders(headers: Headers): DjenRateLimit {
  const limitRaw = headers.get("x-ratelimit-limit");
  const remainingRaw = headers.get("x-ratelimit-remaining");
  const retryAfterRaw = headers.get("retry-after");

  const limit = limitRaw !== null ? Number(limitRaw) : NaN;
  const remaining = remainingRaw !== null ? Number(remainingRaw) : NaN;
  const retryAfter = retryAfterRaw !== null ? Number(retryAfterRaw) : NaN;

  return {
    limit: Number.isFinite(limit) ? limit : null,
    remaining: Number.isFinite(remaining) ? remaining : null,
    resetAt: Number.isFinite(retryAfter) ? Date.now() + retryAfter * 1000 : null,
  };
}

const rateLimitMiddleware: Middleware = {
  async onResponse({ request, response }) {
    rateLimitBySignature.set(
      signatureFor(new URL(request.url).pathname, { method: request.method }),
      parseRateLimitHeaders(response.headers),
    );
    return undefined;
  },
};

// ---------- openapi-fetch clients -----------------------------------------

// Always go through a late-bound fetch delegator so that tests (which mock
// `globalThis.fetch` after module import) and polyfilled environments see
// the latest `globalThis.fetch`. `openapi-fetch` otherwise snapshots the
// reference at `createClient()` time, which would break the BDD steps that
// replace `global.fetch` on a per-scenario basis.
const lateBoundFetch: typeof fetch = (input, init) => globalThis.fetch(input, init);

export const djenPublic: Client<paths> = createClient<paths>({
  baseUrl: DJEN_PUBLIC_BASE,
  fetch: lateBoundFetch,
});
export const djenProxy: Client<paths> = createClient<paths>({
  baseUrl: DJEN_PROXY_BASE,
  fetch: lateBoundFetch,
});
djenPublic.use(rateLimitMiddleware);
djenProxy.use(rateLimitMiddleware);

// ---------- geo-fence state machine ---------------------------------------

export type GeoState = "unknown" | "direct-ok" | "proxy-only";

const SESSION_KEY = "djen:geo-state";

function readSessionGeoState(): GeoState {
  try {
    if (typeof sessionStorage === "undefined") return "unknown";
    const value = sessionStorage.getItem(SESSION_KEY);
    if (value === "direct-ok" || value === "proxy-only" || value === "unknown") {
      return value;
    }
  } catch {
    /* ignore (private mode, SSR) */
  }
  return "unknown";
}

let geoState: GeoState = readSessionGeoState();

function setGeoState(next: GeoState): void {
  geoState = next;
  try {
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.setItem(SESSION_KEY, next);
    }
  } catch {
    /* ignore */
  }
}

/** Reset the geo-state back to "unknown". Intended for tests and debugging. */
export function _resetGeoState(): void {
  geoState = "unknown";
  try {
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.removeItem(SESSION_KEY);
    }
  } catch {
    /* ignore */
  }
}

/** Read-only accessor for the current geo-state. Useful in tests and UI badges. */
export function _getGeoState(): GeoState {
  return geoState;
}

// ---------- failure classification ----------------------------------------

/**
 * Classify a raw error from `openapi-fetch` / `fetch` as a geo-block shape
 * that should trigger the proxy fallback.
 *
 * Geo-block shapes:
 *   - TypeError from fetch (CORS, network unreachable, DNS failure)
 *   - HTTP 403, 451 (explicit blocks)
 *   - Our own timeout via AbortSignal.timeout
 *
 * Non-geo-block shapes (propagate to caller):
 *   - HTTP 5xx (real backend errors on the public side)
 *   - HTTP 422 (business errors — caller's fault)
 *   - HTTP 429 (rate-limited — dedicated error type)
 *   - User abort signals
 */
function isGeoBlockShape(err: unknown): boolean {
  if (err instanceof DjenHttpError) {
    return err.status === 403 || err.status === 451;
  }
  if (err instanceof TypeError) {
    // fetch network errors surface as TypeError
    return true;
  }
  if (err instanceof Error) {
    // Our own AbortSignal.timeout() throws a DOMException "TimeoutError"
    if (err.name === "TimeoutError") return true;
  }
  return false;
}

// ---------- core request dispatch -----------------------------------------

type AnyClient = Client<paths>;

type CallOpts = {
  signal?: AbortSignal;
  /** Per-request timeout in milliseconds. Defaults to 10 000. */
  timeoutMs?: number;
};

const DEFAULT_TIMEOUT_MS = 10_000;

function mergeAbortSignals(
  external: AbortSignal | undefined,
  timeoutMs: number,
): { signal: AbortSignal; cleanup: () => void } {
  const controller = new AbortController();
  const onAbort = () => controller.abort(external?.reason);
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  if (external) {
    if (external.aborted) {
      controller.abort(external.reason);
    } else {
      external.addEventListener("abort", onAbort, { once: true });
    }
  }

  timeoutId = setTimeout(() => {
    const err = new DOMException(
      `DJEN request timed out after ${timeoutMs}ms`,
      "TimeoutError",
    );
    controller.abort(err);
  }, timeoutMs);

  return {
    signal: controller.signal,
    cleanup: () => {
      if (timeoutId !== null) clearTimeout(timeoutId);
      if (external) external.removeEventListener("abort", onAbort);
    },
  };
}

interface OpenapiFetchResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

async function unwrap<T>(
  promise: Promise<OpenapiFetchResult<T>>,
  signatureKey: string,
): Promise<{ data: T; rateLimit: DjenRateLimit }> {
  const { data, error, response } = await promise;

  if (response.status === 429) {
    const retryHeader = Number(response.headers.get("retry-after"));
    const retryAfterSec =
      Number.isFinite(retryHeader) && retryHeader > 0 ? retryHeader : 60;
    throw new DjenRateLimitError(Math.max(60, retryAfterSec));
  }

  if (error !== undefined || !response.ok) {
    throw new DjenHttpError(
      response.status,
      error,
      `DJEN request failed: HTTP ${response.status}`,
    );
  }

  const rateLimit =
    rateLimitBySignature.get(signatureKey) ??
    parseRateLimitHeaders(response.headers);

  return { data: data as T, rateLimit };
}

function pickClient(preferred: "direct" | "proxy"): {
  client: AnyClient;
  source: DjenCallSource;
} {
  if (geoState === "proxy-only") return { client: djenProxy, source: "proxy" };
  if (preferred === "proxy") return { client: djenProxy, source: "proxy" };
  return { client: djenPublic, source: "direct" };
}

/**
 * Execute a call against a single client, wrapping the openapi-fetch result
 * into our `DjenCallResult` shape and tagging it with the source.
 */
async function callOne<T>(
  client: AnyClient,
  source: DjenCallSource,
  signatureKey: string,
  run: (client: AnyClient, signal: AbortSignal) => Promise<OpenapiFetchResult<T>>,
  opts: CallOpts,
): Promise<DjenCallResult<T>> {
  const { signal, cleanup } = mergeAbortSignals(
    opts.signal,
    opts.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );
  try {
    const { data, rateLimit } = await unwrap(run(client, signal), signatureKey);
    return {
      data,
      rateLimit,
      source,
      usedFallback: source === "proxy",
    };
  } finally {
    cleanup();
  }
}

/**
 * Dispatch a request with geo-fence awareness:
 *   - If state is "proxy-only", go straight to the proxy.
 *   - Otherwise try direct; on geo-block-shaped failures, fall back to proxy
 *     and promote the state to "proxy-only" for the rest of the session.
 *   - Never fall back on 429, 5xx, 422, or user abort.
 */
export async function djenCall<T>(
  signatureKey: string,
  run: (client: AnyClient, signal: AbortSignal) => Promise<OpenapiFetchResult<T>>,
  opts: CallOpts = {},
): Promise<DjenCallResult<T>> {
  // Fast path: we already learned public is blocked.
  if (geoState === "proxy-only") {
    return callOne(djenProxy, "proxy", signatureKey, run, opts);
  }

  try {
    const result = await callOne(djenPublic, "direct", signatureKey, run, opts);
    if (geoState === "unknown") setGeoState("direct-ok");
    return result;
  } catch (err) {
    if (err instanceof DjenRateLimitError) throw err;
    if (opts.signal?.aborted) throw err;
    if ((err as Error)?.name === "AbortError") throw err;
    if (!isGeoBlockShape(err)) throw err;

    const result = await callOne(djenProxy, "proxy", signatureKey, run, opts);
    setGeoState("proxy-only");
    return result;
  }
}

// ---------- typed endpoint wrappers ---------------------------------------

export interface DjenSearchPayload {
  items: DjenComunicacaoItem[];
  count: number;
}

/**
 * GET /api/v1/comunicacao — the one endpoint the frontend actively uses today.
 *
 * The spec declares a `{ status, message, count, items }` envelope, but the
 * live API is known to sometimes return a bare array. This wrapper flattens
 * both shapes into `{ items, count }` so callers don't have to care.
 */
export async function searchComunicacoes(
  query: DjenComunicacaoQuery,
  opts: CallOpts = {},
): Promise<DjenCallResult<DjenSearchPayload>> {
  return djenCall<DjenSearchPayload>(
    "GET /api/v1/comunicacao",
    async (client, signal) => {
      // `DjenComunicacaoQuery` is an intersection with our local `texto`
      // extension — cast to the generated type so openapi-fetch accepts it
      // while we still forward every field (including `texto`) verbatim.
      const res = await client.GET("/api/v1/comunicacao", {
        params: {
          query: query as NonNullable<
            paths["/api/v1/comunicacao"]["get"]["parameters"]["query"]
          >,
        },
        signal,
      });
      const body = res.data as
        | { items?: DjenComunicacaoItem[]; count?: number }
        | DjenComunicacaoItem[]
        | undefined;

      // Runtime schema validation — non-throwing. Logs mismatches between the
      // live API response and the spec declared in djen.yml so deviations are
      // visible in the browser console without breaking existing behaviour.
      if (!Array.isArray(body) && body !== undefined) {
        const parseResult = getApiV1ComunicacaoResponse.safeParse(body);
        if (!parseResult.success) {
          console.warn("[djen] Response schema mismatch:", parseResult.error.issues);
        }
      }

      const items: DjenComunicacaoItem[] = Array.isArray(body)
        ? body
        : (body?.items ?? []);
      const count = Array.isArray(body)
        ? items.length
        : typeof body?.count === "number"
          ? body.count
          : items.length;
      return {
        data: { items, count },
        error: res.error,
        response: res.response,
      };
    },
    opts,
  );
}

/**
 * GET /api/v1/comunicacao/tribunal — list of tribunals with metadata.
 */
export async function listTribunais(
  opts: CallOpts = {},
): Promise<DjenCallResult<DjenTribunal[]>> {
  return djenCall<DjenTribunal[]>(
    "GET /api/v1/comunicacao/tribunal",
    async (client, signal) => {
      const res = await client.GET("/api/v1/comunicacao/tribunal", { signal });
      return {
        data: (res.data ?? []) as DjenTribunal[],
        error: res.error,
        response: res.response,
      };
    },
    opts,
  );
}

/**
 * GET /api/v1/comunicacao/{hash}/certidao — download a comunicacao certificate.
 * The spec does not declare a response content type; callers get back the
 * raw Response object via the DjenCallResult to decide how to decode.
 */
export async function getCertidao(
  hash: string,
  opts: CallOpts = {},
): Promise<DjenCallResult<Response>> {
  return djenCall<Response>(
    "GET /api/v1/comunicacao/{hash}/certidao",
    async (client, signal) => {
      const res = await client.GET("/api/v1/comunicacao/{hash}/certidao", {
        params: { path: { hash } },
        signal,
        parseAs: "stream",
      });
      return {
        data: res.response.clone() as unknown as Response,
        error: res.error,
        response: res.response,
      };
    },
    opts,
  );
}

/**
 * GET /api/v1/caderno/{sigla_tribunal}/{data}/{meio} — caderno metadata.
 */
export async function getCaderno(
  params: { sigla_tribunal: string; data: string; meio: "E" | "D" },
  opts: CallOpts = {},
): Promise<DjenCallResult<DjenCaderno>> {
  return djenCall<DjenCaderno>(
    "GET /api/v1/caderno/{sigla_tribunal}/{data}/{meio}",
    async (client, signal) => {
      const res = await client.GET(
        "/api/v1/caderno/{sigla_tribunal}/{data}/{meio}",
        {
          params: { path: params },
          signal,
        },
      );
      return {
        data: (res.data ?? {}) as DjenCaderno,
        error: res.error,
        response: res.response,
      };
    },
    opts,
  );
}

/**
 * POST /api/v1/login — tribunal authentication for create/delete operations.
 * Not consumed by the public frontend today; wired up for completeness.
 */
export async function login(
  body: { login: string; senha: string },
  opts: CallOpts = {},
): Promise<
  DjenCallResult<{ access_token?: string; user?: { id?: number; nome?: string } }>
> {
  return djenCall(
    "POST /api/v1/login",
    async (client, signal) => {
      const res = await client.POST("/api/v1/login", { body, signal });
      return {
        data: res.data,
        error: res.error,
        response: res.response,
      };
    },
    opts,
  );
}

/**
 * POST /api/v1/comunicacao — tribunal-only publish endpoint. Kept for API
 * completeness; not consumed by the frontend.
 */
export async function createComunicacao(
  body: NonNullable<
    paths["/api/v1/comunicacao"]["post"]["requestBody"]
  >["content"]["application/json"],
  opts: CallOpts = {},
): Promise<
  DjenCallResult<
    NonNullable<
      paths["/api/v1/comunicacao"]["post"]["responses"]["200"]["content"]["application/json"]
    >
  >
> {
  return djenCall(
    "POST /api/v1/comunicacao",
    async (client, signal) => {
      const res = await client.POST("/api/v1/comunicacao", { body, signal });
      return {
        data: res.data,
        error: res.error,
        response: res.response,
      };
    },
    opts,
  );
}

/**
 * DELETE /api/v1/comunicacao/{id} — tribunal-only cancel endpoint.
 */
export async function deleteComunicacao(
  id: string,
  body: { motivo_cancelamento: string },
  opts: CallOpts = {},
): Promise<DjenCallResult<{ status?: string; message?: string }>> {
  return djenCall(
    "DELETE /api/v1/comunicacao/{id}",
    async (client, signal) => {
      const res = await client.DELETE("/api/v1/comunicacao/{id}", {
        params: { path: { id } },
        body,
        signal,
      });
      return {
        data: res.data,
        error: res.error,
        response: res.response,
      };
    },
    opts,
  );
}

// Re-export the internal helper used by `pickClient`; it's only exposed so
// tests can assert which client a call lands on.
export { pickClient as _pickClient };
