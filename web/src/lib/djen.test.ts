import { describe, expect, it } from "vitest";
import { normalizeExternalUrl } from "./djen";

describe("normalizeExternalUrl", () => {
  it("passes absolute http(s) URLs through unchanged", () => {
    expect(normalizeExternalUrl("https://comunicaapi.pje.jus.br/doc/1")).toBe(
      "https://comunicaapi.pje.jus.br/doc/1",
    );
  });

  it("resolves a DJEN-relative path against the public base", () => {
    expect(normalizeExternalUrl("/doc/1")).toBe(
      "https://comunicaapi.pje.jus.br/doc/1",
    );
  });

  it("rejects a protocol-relative value instead of resolving onto its host", () => {
    const result = normalizeExternalUrl("//evil.example.com/malware");
    expect(result === undefined || !result.includes("evil.example.com")).toBe(true);
  });

  it("rejects non-http(s) schemes", () => {
    expect(normalizeExternalUrl("javascript:alert(1)")).toBeUndefined();
  });

  it("rejects empty/null/undefined values", () => {
    expect(normalizeExternalUrl("")).toBeUndefined();
    expect(normalizeExternalUrl(null)).toBeUndefined();
    expect(normalizeExternalUrl(undefined)).toBeUndefined();
  });
});
