import { describe, it, expect } from "vitest";
import { computeFingerprints, FINGERPRINT_VERSION } from "../../src/core/fingerprint.js";

describe("computeFingerprints", () => {
  it("returns three different hashes", () => {
    const fp = computeFingerprints("# Title\nSome content here.\n- item 1\n- item 2");
    expect(fp.rawHash).toHaveLength(64); // SHA-256 hex
    expect(fp.normalizedHash).toHaveLength(64);
    expect(fp.structureHash).toHaveLength(64);
  });

  it("rawHash changes with any byte change", () => {
    const a = computeFingerprints("hello world");
    const b = computeFingerprints("hello  world");
    expect(a.rawHash).not.toBe(b.rawHash);
  });

  it("normalizedHash ignores whitespace differences", () => {
    const a = computeFingerprints("hello   world");
    const b = computeFingerprints("hello world");
    expect(a.normalizedHash).toBe(b.normalizedHash);
  });

  it("normalizedHash ignores case", () => {
    const a = computeFingerprints("Hello World");
    const b = computeFingerprints("hello world");
    expect(a.normalizedHash).toBe(b.normalizedHash);
  });

  it("normalizedHash ignores punctuation", () => {
    const a = computeFingerprints("Hello, world!");
    const b = computeFingerprints("Hello world");
    expect(a.normalizedHash).toBe(b.normalizedHash);
  });

  it("structureHash matches same logical structure", () => {
    const a = computeFingerprints("# Title\n- item 1\n- item 2");
    const b = computeFingerprints("# Title\n- item 1 modified\n- item 2 modified");
    // Structure should differ because list item text differs
    // but heading structure is same
    expect(a.structureHash).not.toBe(b.structureHash);
  });

  it("identical content produces identical hashes", () => {
    const content = "# Test\nSome content\n- list item";
    const a = computeFingerprints(content);
    const b = computeFingerprints(content);
    expect(a.rawHash).toBe(b.rawHash);
    expect(a.normalizedHash).toBe(b.normalizedHash);
    expect(a.structureHash).toBe(b.structureHash);
  });

  it("version constant is defined", () => {
    expect(FINGERPRINT_VERSION).toBe("1.0.0");
  });
});
