import { describe, it, expect } from "vitest";
import { newId, nowISO, daysBetween } from "../../src/core/id.js";

describe("newId", () => {
  it("returns a UUID string", () => {
    const id = newId();
    expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
  });

  it("returns unique IDs", () => {
    const ids = new Set(Array.from({ length: 100 }, () => newId()));
    expect(ids.size).toBe(100);
  });
});

describe("nowISO", () => {
  it("returns ISO-8601 string", () => {
    const now = nowISO();
    expect(() => new Date(now)).not.toThrow();
    expect(now).toContain("T");
  });
});

describe("daysBetween", () => {
  it("same timestamp returns 0", () => {
    const ts = "2024-01-15T12:00:00.000Z";
    expect(daysBetween(ts, ts)).toBe(0);
  });

  it("one day apart returns 1", () => {
    const a = "2024-01-15T12:00:00.000Z";
    const b = "2024-01-16T12:00:00.000Z";
    expect(daysBetween(a, b)).toBeCloseTo(1, 5);
  });

  it("order doesn't matter (absolute)", () => {
    const a = "2024-01-15T12:00:00.000Z";
    const b = "2024-01-20T12:00:00.000Z";
    expect(daysBetween(a, b)).toBe(daysBetween(b, a));
  });

  it("30 days apart returns 30", () => {
    const a = "2024-01-01T00:00:00.000Z";
    const b = "2024-01-31T00:00:00.000Z";
    expect(daysBetween(a, b)).toBeCloseTo(30, 5);
  });
});
