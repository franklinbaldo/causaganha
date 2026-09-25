import { describe, expect, it, vi } from "vitest";

import { handleRequest, hostAllowed, readBounded, verifyToken } from "../src/index.js";

const ENV = { RELAY_TOKEN: "correct horse battery staple" };

function relayRequest(target, options = {}) {
  const headers = new Headers(options.headers);
  headers.set("x-relay-token", options.token ?? ENV.RELAY_TOKEN);
  if (target !== null) headers.set("x-relay-url", target);
  return new Request("https://relay.example.test/", {
    method: options.method ?? "GET",
    headers,
    body: options.body,
  });
}

describe("relay authorization and target validation", () => {
  it("allows only subdomains of the judicial allowlist", () => {
    expect(hostAllowed("juris-back.tjro.jus.br")).toBe(true);
    expect(hostAllowed("dadosabertos.web.stj.jus.br")).toBe(true);
    expect(hostAllowed("tjro.jus.br.evil.example")).toBe(false);
    expect(hostAllowed("tjro.jus.br")).toBe(false);
  });

  it("compares both equal and unequal tokens", async () => {
    await expect(verifyToken(ENV.RELAY_TOKEN, ENV.RELAY_TOKEN)).resolves.toBe(true);
    await expect(verifyToken("wrong", ENV.RELAY_TOKEN)).resolves.toBe(false);
    await expect(verifyToken(null, ENV.RELAY_TOKEN)).resolves.toBe(false);
  });

  it("rejects a bad token before parsing the target", async () => {
    const response = await handleRequest(
      relayRequest("not a URL", { token: "wrong" }),
      ENV,
      vi.fn(),
    );
    expect(response.status).toBe(401);
  });

  it.each([
    ["http://juris-back.tjro.jus.br/", 403],
    ["https://example.com/", 403],
    ["https://tjro.jus.br.evil.example/", 403],
    ["not a URL", 400],
  ])("rejects disallowed target %s", async (target, status) => {
    const response = await handleRequest(relayRequest(target), ENV, vi.fn());
    expect(response.status).toBe(status);
  });
});

describe("relay forwarding", () => {
  it("streams an allowed POST and strips relay and proxy headers", async () => {
    const upstreamFetch = vi.fn(async (url, init) => {
      expect(url).toBe("https://juris-back.tjro.jus.br/search/varios_parametros/");
      expect(init.method).toBe("POST");
      expect(init.redirect).toBe("manual");
      expect(init.headers.get("content-type")).toBe("application/json");
      expect(init.headers.has("x-relay-token")).toBe(false);
      expect(init.headers.has("x-relay-url")).toBe(false);
      expect(init.headers.has("cf-ray")).toBe(false);
      expect(await new Response(init.body).text()).toBe('{"size":1}');
      return new Response('{"hits":[]}', {
        status: 200,
        headers: {
          "content-type": "application/json",
          "content-length": "11",
        },
      });
    });

    const response = await handleRequest(
      relayRequest("https://juris-back.tjro.jus.br/search/varios_parametros/", {
        method: "POST",
        body: '{"size":1}',
        headers: {
          "content-type": "application/json",
          "cf-ray": "not-forwarded",
        },
      }),
      ENV,
      upstreamFetch,
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("application/json");
    expect(response.headers.has("content-length")).toBe(false);
    expect(response.headers.get("cache-control")).toBe("no-store");
    await expect(response.text()).resolves.toBe('{"hits":[]}');
    expect(upstreamFetch).toHaveBeenCalledOnce();
  });

  it("strips Authorization and Cookie before forwarding upstream", async () => {
    const upstreamFetch = vi.fn(async (_url, init) => {
      expect(init.headers.has("authorization")).toBe(false);
      expect(init.headers.has("cookie")).toBe(false);
      return new Response("ok", { status: 200 });
    });

    const response = await handleRequest(
      relayRequest("https://juris-back.tjro.jus.br/search/varios_parametros/", {
        headers: {
          authorization: "Bearer stolen-token",
          cookie: "session=hijacked",
        },
      }),
      ENV,
      upstreamFetch,
    );

    expect(response.status).toBe(200);
    expect(upstreamFetch).toHaveBeenCalledOnce();
  });

  it("returns a generic 502 when the upstream fetch fails", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const response = await handleRequest(
      relayRequest("https://juris-back.tjro.jus.br/search/varios_parametros/"),
      ENV,
      vi.fn(async () => {
        throw new Error("private upstream detail");
      }),
    );

    expect(response.status).toBe(502);
    await expect(response.text()).resolves.toBe("upstream error");
    expect(errorSpy).toHaveBeenCalledOnce();
    errorSpy.mockRestore();
  });

  it("strips Set-Cookie from the upstream response", async () => {
    const upstreamFetch = vi.fn(
      async () =>
        new Response("ok", {
          status: 200,
          headers: { "set-cookie": "session=abc123" },
        }),
    );

    const response = await handleRequest(
      relayRequest("https://juris-back.tjro.jus.br/search/varios_parametros/"),
      ENV,
      upstreamFetch,
    );

    expect(response.headers.has("set-cookie")).toBe(false);
  });
});

describe("relay egress budgets (TM-02 / #1609)", () => {
  it("readBounded assembles chunks that stay within budget", async () => {
    const stream = new Response("hello").body;
    const bytes = await readBounded(stream, 100);
    expect(new TextDecoder().decode(bytes)).toBe("hello");
  });

  it("readBounded returns null once the stream exceeds budget", async () => {
    const stream = new Response("hello world").body;
    const bytes = await readBounded(stream, 5);
    expect(bytes).toBeNull();
  });

  it("readBounded returns an empty buffer for a null stream", async () => {
    const bytes = await readBounded(null, 5);
    expect(bytes.byteLength).toBe(0);
  });

  it("rejects a request body over budget with 413, never calling upstream", async () => {
    const upstreamFetch = vi.fn();
    const response = await handleRequest(
      relayRequest("https://juris-back.tjro.jus.br/search/varios_parametros/", {
        method: "POST",
        body: "x".repeat(11),
      }),
      ENV,
      upstreamFetch,
      { maxRequestBytes: 10, maxResponseBytes: 1024 },
    );

    expect(response.status).toBe(413);
    expect(upstreamFetch).not.toHaveBeenCalled();
  });

  it("allows a request body within budget", async () => {
    const upstreamFetch = vi.fn(async () => new Response("ok", { status: 200 }));
    const response = await handleRequest(
      relayRequest("https://juris-back.tjro.jus.br/search/varios_parametros/", {
        method: "POST",
        body: "x".repeat(10),
      }),
      ENV,
      upstreamFetch,
      { maxRequestBytes: 10, maxResponseBytes: 1024 },
    );

    expect(response.status).toBe(200);
    expect(upstreamFetch).toHaveBeenCalledOnce();
  });

  it("returns 502 when the upstream response exceeds budget", async () => {
    const upstreamFetch = vi.fn(async () => new Response("x".repeat(11), { status: 200 }));
    const response = await handleRequest(
      relayRequest("https://juris-back.tjro.jus.br/search/varios_parametros/"),
      ENV,
      upstreamFetch,
      { maxRequestBytes: 1024, maxResponseBytes: 10 },
    );

    expect(response.status).toBe(502);
    await expect(response.text()).resolves.toBe("upstream response too large");
  });

  it("allows an upstream response within budget", async () => {
    const upstreamFetch = vi.fn(async () => new Response("x".repeat(10), { status: 200 }));
    const response = await handleRequest(
      relayRequest("https://juris-back.tjro.jus.br/search/varios_parametros/"),
      ENV,
      upstreamFetch,
      { maxRequestBytes: 1024, maxResponseBytes: 10 },
    );

    expect(response.status).toBe(200);
    await expect(response.text()).resolves.toBe("x".repeat(10));
  });
});
