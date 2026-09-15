import { describe, expect, it, vi } from "vitest";

import { handleRequest, parseDownloadPath } from "../src/index.js";

function proxyRequest(path, options = {}) {
  const headers = new Headers(options.headers);
  return new Request(`https://proxy.example.test${path}`, {
    method: options.method ?? "GET",
    headers,
  });
}

describe("parseDownloadPath", () => {
  it("accepts a djen- item and a .parquet file", () => {
    expect(parseDownloadPath("/download/djen-tjro-2026/comunicacoes.parquet")).toEqual({
      item: "djen-tjro-2026",
      file: "comunicacoes.parquet",
    });
  });

  it.each([
    "/download/other-item/comunicacoes.parquet",
    "/download/djen-tjro-2026/readme.txt",
    "/download/djen-tjro-2026",
    "/metadata/djen-tjro-2026/files",
    "/download/djen-tjro-2026/../secrets.parquet",
  ])("rejects %s", (path) => {
    expect(parseDownloadPath(path)).toBeNull();
  });
});

describe("archive CORS proxy authorization", () => {
  it("answers an OPTIONS preflight without calling upstream", async () => {
    const upstreamFetch = vi.fn();
    const response = await handleRequest(
      proxyRequest("/download/djen-tjro-2026/comunicacoes.parquet", { method: "OPTIONS" }),
      {},
      upstreamFetch,
    );

    expect(response.status).toBe(204);
    expect(response.headers.get("access-control-allow-origin")).toBe("*");
    expect(response.headers.get("access-control-allow-headers")).toBe("range");
    expect(upstreamFetch).not.toHaveBeenCalled();
  });

  it.each([["POST"], ["PUT"], ["DELETE"]])("rejects %s with 405", async (method) => {
    const response = await handleRequest(
      proxyRequest("/download/djen-tjro-2026/comunicacoes.parquet", { method }),
      {},
      vi.fn(),
    );
    expect(response.status).toBe(405);
  });

  it("rejects a path outside the djen- allowlist with 404 and never calls upstream", async () => {
    const upstreamFetch = vi.fn();
    const response = await handleRequest(
      proxyRequest("/download/some-other-item/file.parquet"),
      {},
      upstreamFetch,
    );

    expect(response.status).toBe(404);
    expect(upstreamFetch).not.toHaveBeenCalled();
  });

  it("rejects a non-.parquet file with 404", async () => {
    const response = await handleRequest(
      proxyRequest("/download/djen-tjro-2026/readme.txt"),
      {},
      vi.fn(),
    );
    expect(response.status).toBe(404);
  });
});

describe("archive CORS proxy forwarding", () => {
  it("streams an allowed GET, forwards Range, and adds CORS headers", async () => {
    const upstreamFetch = vi.fn(async (url, init) => {
      expect(url).toBe("https://archive.org/download/djen-tjro-2026/comunicacoes.parquet");
      expect(init.method).toBe("GET");
      expect(init.headers.get("range")).toBe("bytes=0-99");
      expect(init.redirect).toBe("follow");
      return new Response("parquet-bytes", {
        status: 206,
        headers: {
          "content-type": "application/octet-stream",
          "content-range": "bytes 0-99/1000",
          "accept-ranges": "bytes",
          "content-length": "100",
        },
      });
    });

    const response = await handleRequest(
      proxyRequest("/download/djen-tjro-2026/comunicacoes.parquet", {
        headers: { range: "bytes=0-99" },
      }),
      {},
      upstreamFetch,
    );

    expect(response.status).toBe(206);
    expect(response.headers.get("access-control-allow-origin")).toBe("*");
    expect(response.headers.get("content-range")).toBe("bytes 0-99/1000");
    expect(response.headers.get("accept-ranges")).toBe("bytes");
    await expect(response.text()).resolves.toBe("parquet-bytes");
    expect(upstreamFetch).toHaveBeenCalledOnce();
  });

  it("forwards a HEAD request without a Range header", async () => {
    const upstreamFetch = vi.fn(async (url, init) => {
      expect(init.method).toBe("HEAD");
      expect(init.headers.has("range")).toBe(false);
      return new Response(null, { status: 200, headers: { "content-length": "1000" } });
    });

    const response = await handleRequest(
      proxyRequest("/download/djen-tjro-2026/comunicacoes.parquet", { method: "HEAD" }),
      {},
      upstreamFetch,
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("access-control-allow-origin")).toBe("*");
  });

  it("returns a generic 502 when the upstream fetch fails", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const response = await handleRequest(
      proxyRequest("/download/djen-tjro-2026/comunicacoes.parquet"),
      {},
      vi.fn(async () => {
        throw new Error("private upstream detail");
      }),
    );

    expect(response.status).toBe(502);
    expect(response.headers.get("access-control-allow-origin")).toBe("*");
    await expect(response.text()).resolves.toBe("upstream error");
    expect(errorSpy).toHaveBeenCalledOnce();
    errorSpy.mockRestore();
  });
});
