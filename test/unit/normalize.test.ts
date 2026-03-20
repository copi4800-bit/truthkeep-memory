import { describe, it, expect } from "vitest";
import {
  tokenize,
  tokenizeToSet,
  jaccardSimilarity,
  normalizeForHash,
  extractStructure,
  buildFtsQuery,
  bm25RankToScore,
  truncate,
} from "../../src/core/normalize.js";

describe("tokenize", () => {
  it("extracts Unicode word tokens", () => {
    expect(tokenize("Hello world 123")).toEqual(["Hello", "world", "123"]);
  });

  it("handles Vietnamese text with diacritics", () => {
    const tokens = tokenize("Xin chào thế giới");
    expect(tokens).toEqual(["Xin", "chào", "thế", "giới"]);
  });

  it("handles empty string", () => {
    expect(tokenize("")).toEqual([]);
  });

  it("handles special characters", () => {
    expect(tokenize("hello_world foo-bar")).toEqual(["hello_world", "foo", "bar"]);
  });

  it("handles CJK characters", () => {
    const tokens = tokenize("メモリ Aegis");
    expect(tokens.length).toBeGreaterThanOrEqual(2);
  });
});

describe("tokenizeToSet", () => {
  it("returns lowercase set", () => {
    const set = tokenizeToSet("Hello World HELLO");
    expect(set.has("hello")).toBe(true);
    expect(set.has("world")).toBe(true);
    expect(set.size).toBe(2); // "hello" deduped
  });
});

describe("jaccardSimilarity", () => {
  it("identical sets return 1", () => {
    const a = new Set(["a", "b", "c"]);
    expect(jaccardSimilarity(a, a)).toBe(1);
  });

  it("disjoint sets return 0", () => {
    const a = new Set(["a", "b"]);
    const b = new Set(["c", "d"]);
    expect(jaccardSimilarity(a, b)).toBe(0);
  });

  it("partial overlap returns correct ratio", () => {
    const a = new Set(["a", "b", "c"]);
    const b = new Set(["b", "c", "d"]);
    // intersection=2, union=4
    expect(jaccardSimilarity(a, b)).toBe(0.5);
  });

  it("empty sets return 1", () => {
    expect(jaccardSimilarity(new Set(), new Set())).toBe(1);
  });

  it("one empty set returns 0", () => {
    expect(jaccardSimilarity(new Set(["a"]), new Set())).toBe(0);
  });
});

describe("normalizeForHash", () => {
  it("collapses whitespace and lowercases", () => {
    expect(normalizeForHash("  Hello   World  ")).toBe("hello world");
  });

  it("strips punctuation", () => {
    expect(normalizeForHash("Hello, world! How's it?")).toBe("hello world hows it");
  });

  it("preserves Unicode letters", () => {
    const result = normalizeForHash("Xin chào thế giới!");
    expect(result).toBe("xin chào thế giới");
  });
});

describe("extractStructure", () => {
  it("identifies markdown headings", () => {
    const result = extractStructure("# Title\nSome text\n## Subtitle");
    expect(result).toContain("H:Title");
    expect(result).toContain("H:Subtitle");
  });

  it("identifies list items", () => {
    const result = extractStructure("- item one\n- item two");
    expect(result).toContain("L:item one");
  });

  it("identifies key-value pairs", () => {
    const result = extractStructure("name: John\nage: 30");
    expect(result).toContain("K:name");
    expect(result).toContain("K:age");
  });

  it("skips empty lines", () => {
    const result = extractStructure("line1\n\n\nline2");
    expect(result.split("\n").length).toBe(2);
  });
});

describe("buildFtsQuery", () => {
  it("single token returns quoted with prefix fallback", () => {
    const result = buildFtsQuery("hello");
    expect(result).toContain('"hello"');
    expect(result).toContain("hello*");
  });

  it("multiple tokens use NEAR and AND", () => {
    const result = buildFtsQuery("hello world");
    expect(result).toContain("NEAR");
    expect(result).toContain("AND");
  });

  it("empty string returns null", () => {
    expect(buildFtsQuery("")).toBeNull();
  });

  it("strips quotes from tokens", () => {
    const result = buildFtsQuery('say "hello"');
    expect(result).not.toContain('""');
  });
});

describe("bm25RankToScore", () => {
  it("negative rank converts to positive score", () => {
    const score = bm25RankToScore(-5);
    expect(score).toBeGreaterThan(0);
    expect(score).toBeLessThanOrEqual(1);
  });

  it("rank 0 returns 1.0", () => {
    // rank=0, not negative, so 1/(1+0) = 1
    expect(bm25RankToScore(0)).toBe(1);
  });

  it("non-finite returns low score", () => {
    expect(bm25RankToScore(NaN)).toBeCloseTo(0.001, 3);
    expect(bm25RankToScore(Infinity)).toBeCloseTo(0.001, 3);
  });

  it("higher negative rank = higher score", () => {
    expect(bm25RankToScore(-10)).toBeGreaterThan(bm25RankToScore(-1));
  });
});

describe("truncate", () => {
  it("short text unchanged", () => {
    expect(truncate("hello", 100)).toBe("hello");
  });

  it("long text truncated at word boundary", () => {
    const result = truncate("hello world this is a test", 15);
    expect(result.length).toBeLessThanOrEqual(18); // 15 + "..."
    expect(result).toContain("...");
  });
});
