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
    expect(normalizeExternalUrl("//evil.example.com/malware")).toBeUndefined();
  });

  it("rejects a backslash network-path variant of the same attack", () => {
    // WHATWG URL parsing treats "\" the same as "/" for special schemes, so
    // "/\host/path" is equivalent to "//host/path" once resolved.
    expect(normalizeExternalUrl("/\\evil.example.com/malware")).toBeUndefined();
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
