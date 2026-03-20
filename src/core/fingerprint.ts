import { createHash } from "node:crypto";
import { normalizeForHash, extractStructure } from "./normalize.js";

export interface Fingerprints {
  rawHash: string;
  normalizedHash: string;
  structureHash: string;
}

/**
 * SHA-256 hash of a string, returned as hex.
 */
function sha256(input: string): string {
  return createHash("sha256").update(input, "utf-8").digest("hex");
}

/**
 * Compute all three fingerprint hashes for content.
 *
 * - rawHash: exact byte-level identity
 * - normalizedHash: ignores whitespace/formatting/punctuation
 * - structureHash: compares logical form (headings, lists, keys)
 */
export function computeFingerprints(content: string): Fingerprints {
  const rawHash = sha256(content);
  const normalizedHash = sha256(normalizeForHash(content));
  const structureHash = sha256(extractStructure(content));

  return { rawHash, normalizedHash, structureHash };
}

/**
 * Current fingerprint algorithm version.
 * Increment when normalization or structure extraction changes.
 */
export const FINGERPRINT_VERSION = "1.0.0";
