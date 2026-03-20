import { randomUUID } from "node:crypto";

/**
 * Generate a new UUID for use as primary key.
 * Uses crypto.randomUUID() for high-quality randomness.
 */
export function newId(): string {
  return randomUUID();
}

/**
 * Get current timestamp in ISO-8601 format for SQLite TEXT columns.
 */
export function nowISO(): string {
  return new Date().toISOString();
}

/**
 * Compute days between two ISO timestamps.
 */
export function daysBetween(a: string, b: string): number {
  const msA = new Date(a).getTime();
  const msB = new Date(b).getTime();
  return Math.abs(msA - msB) / (24 * 60 * 60 * 1000);
}
