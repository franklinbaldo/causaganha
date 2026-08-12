import { describe, expect, it, vi } from "vitest";

import { handleRequest, hostAllowed, verifyToken } from "../src/index.js";

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
});
