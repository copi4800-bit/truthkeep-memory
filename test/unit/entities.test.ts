import { describe, it, expect } from "vitest";
import { extractEntities, extractEntityMentions } from "../../src/core/entities.js";

describe("extractEntities", () => {
  it("extracts @mentions", () => {
    const entities = extractEntities("Hello @john and @jane");
    const mentions = entities.filter((e) => e.type === "person");
    expect(mentions.length).toBe(2);
    expect(mentions.map((e) => e.text)).toContain("john");
    expect(mentions.map((e) => e.text)).toContain("jane");
    expect(mentions[0].confidence).toBe(0.8);
  });

  it("extracts URLs", () => {
    const entities = extractEntities("Visit https://example.com/path for info");
    const urls = entities.filter((e) => e.type === "url");
    expect(urls.length).toBe(1);
    expect(urls[0].text).toBe("https://example.com/path");
    expect(urls[0].confidence).toBe(0.9);
  });

  it("extracts file paths", () => {
    const entities = extractEntities("Edit src/core/models.ts and config/app.json");
    const files = entities.filter((e) => e.type === "file");
    expect(files.length).toBeGreaterThanOrEqual(2);
  });

  it("extracts capitalized phrases", () => {
    const entities = extractEntities("The Memory Aegis system is powerful. Also see Open Claw.");
    const named = entities.filter((e) => e.type === "named_entity");
    expect(named.length).toBeGreaterThanOrEqual(1);
    expect(named.some((e) => e.text.includes("Memory Aegis"))).toBe(true);
  });

  it("extracts quoted terms", () => {
    const entities = extractEntities('Set "memory_state" to "volatile"');
    const terms = entities.filter((e) => e.type === "term");
    expect(terms.length).toBeGreaterThanOrEqual(1);
  });

  it("extracts technical terms (snake_case)", () => {
    const entities = extractEntities("Check the memory_state and base_decay_rate");
    const tech = entities.filter((e) => e.type === "technical");
    expect(tech.length).toBeGreaterThanOrEqual(1);
  });

  it("deduplicates entities", () => {
    const entities = extractEntities("@john said hello, @john said goodbye");
    const johns = entities.filter((e) => e.text === "john");
    expect(johns.length).toBe(1);
  });

  it("returns empty for empty content", () => {
    expect(extractEntities("")).toEqual([]);
  });
});

describe("extractEntityMentions", () => {
  it("returns lowercase entity texts", () => {
    const mentions = extractEntityMentions("@John visited https://Example.com");
    expect(mentions).toContain("john");
  });
});
