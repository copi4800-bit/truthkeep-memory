import { describe, it, expect } from "vitest";
import { microChunk, extractLandmarks } from "../../src/cognitive/nutcracker.js";

describe("microChunk", () => {
  it("splits on blank lines", () => {
    const chunks = microChunk("Paragraph one.\n\nParagraph two.");
    expect(chunks.length).toBe(2);
    expect(chunks[0].content).toContain("Paragraph one");
    expect(chunks[1].content).toContain("Paragraph two");
  });

  it("splits on markdown headings", () => {
    const content = "# Title\nSome text here.\n## Subtitle\nMore text.";
    const chunks = microChunk(content);
    expect(chunks.length).toBeGreaterThanOrEqual(2);
  });

  it("preserves line numbers", () => {
    const content = "Line 0\nLine 1\n\nLine 3\nLine 4";
    const chunks = microChunk(content);
    expect(chunks[0].startLine).toBe(0);
    expect(chunks.length).toBeGreaterThanOrEqual(2);
  });

  it("handles empty content", () => {
    const chunks = microChunk("");
    expect(chunks.length).toBe(0);
  });

  it("handles single line", () => {
    const chunks = microChunk("Just one line");
    expect(chunks.length).toBe(1);
    expect(chunks[0].content).toBe("Just one line");
  });

  it("splits on code fences", () => {
    const content = "Before code\n```\ncode here\n```\nAfter code";
    const chunks = microChunk(content);
    expect(chunks.length).toBeGreaterThanOrEqual(2);
  });

  it("extracts landmarks from chunks", () => {
    const content = "# Project Setup\n@alice created the repo.\nconfig.yaml: enabled\n\n# Testing\nRun npm test.";
    const chunks = microChunk(content);

    const allLandmarks = chunks.flatMap((c) => c.landmarks);
    expect(allLandmarks.some((l) => l === "Project Setup" || l === "Testing")).toBe(true);
  });

  it("handles large content by splitting at sentence boundaries", () => {
    // Create content larger than MAX_CHUNK_CHARS (2000)
    const sentences = Array.from({ length: 100 }, (_, i) =>
      `This is sentence number ${i} with enough words to make it substantial.`,
    );
    const content = sentences.join(" ");

    const chunks = microChunk(content);
    for (const chunk of chunks) {
      expect(chunk.content.length).toBeLessThanOrEqual(2500); // Allow some slack
    }
  });
});

describe("extractLandmarks", () => {
  it("extracts markdown headings", () => {
    const landmarks = extractLandmarks("# Main Title\nSome text\n## Sub Title");
    expect(landmarks).toContain("Main Title");
    expect(landmarks).toContain("Sub Title");
  });

  it("extracts @mentions", () => {
    const landmarks = extractLandmarks("@alice and @bob discussed the plan.");
    expect(landmarks).toContain("@alice");
    expect(landmarks).toContain("@bob");
  });

  it("extracts key-value pairs", () => {
    const landmarks = extractLandmarks("name: John\nage: 30\nstatus = active");
    expect(landmarks).toContain("kv:name");
    expect(landmarks).toContain("kv:age");
    expect(landmarks).toContain("kv:status");
  });

  it("extracts file paths", () => {
    const landmarks = extractLandmarks("Edit src/components/App.tsx for the fix.");
    expect(landmarks.some((l) => l.startsWith("file:"))).toBe(true);
  });

  it("extracts proper nouns", () => {
    const landmarks = extractLandmarks("The SkyClaw Project uses Memory Aegis.");
    expect(landmarks.some((l) => l.includes("SkyClaw"))).toBe(true);
  });

  it("extracts code identifiers", () => {
    const landmarks = extractLandmarks("Use memory_search_manager and buildFtsQuery.");
    expect(landmarks.some((l) => l.includes("memory_search_manager"))).toBe(true);
  });

  it("deduplicates landmarks", () => {
    const landmarks = extractLandmarks("@alice met @alice again.");
    const aliceCount = landmarks.filter((l) => l === "@alice").length;
    expect(aliceCount).toBe(1);
  });

  it("returns empty for empty text", () => {
    const landmarks = extractLandmarks("");
    expect(landmarks.length).toBe(0);
  });
});
