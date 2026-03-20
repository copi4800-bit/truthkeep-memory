/**
 * Nutcracker Layer — Micro-chunking, landmark indexing, TTL lifecycle.
 *
 * Như chim nutcracker giấu hạt ở hàng nghìn vị trí khác nhau —
 * chia nhỏ content thành chunks có landmark để tìm lại nhanh.
 */

import type Database from "better-sqlite3";
import { newId, nowISO } from "../core/id.js";
import { CONSTANTS } from "../core/models.js";

// ============================================================
// A. Micro-Chunking
// ============================================================

export interface Chunk {
  content: string;
  startLine: number;
  endLine: number;
  landmarks: string[];
}

/**
 * Split content into semantic micro-chunks.
 *
 * Strategies:
 * - Split on blank lines (paragraph boundaries)
 * - Split on markdown headings
 * - Split on code fences
 * - Respect MAX_CHUNK_CHARS limit
 * - Extract landmarks from each chunk
 */
export function microChunk(content: string, sourceType?: string): Chunk[] {
  const lines = content.split("\n");
  const chunks: Chunk[] = [];
  let currentLines: string[] = [];
  let startLine = 0;

  function flushChunk(endLine: number): void {
    if (currentLines.length === 0) return;
    const text = currentLines.join("\n");
    if (text.trim().length === 0) return;

    // If chunk exceeds max size, split further
    if (text.length > CONSTANTS.MAX_CHUNK_CHARS) {
      const subChunks = splitLargeChunk(text, startLine);
      chunks.push(...subChunks);
    } else {
      chunks.push({
        content: text,
        startLine,
        endLine,
        landmarks: extractLandmarks(text),
      });
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Split boundaries
    const isBlankLine = line.trim() === "";
    const isHeading = /^#{1,6}\s/.test(line);
    const isCodeFence = /^```/.test(line);
    const isHorizontalRule = /^[-*_]{3,}\s*$/.test(line);
    const isSplitBoundary = isBlankLine || isHeading || isCodeFence || isHorizontalRule;

    if (isSplitBoundary && currentLines.length > 0) {
      flushChunk(i - 1);
      currentLines = isBlankLine ? [] : [line];
      startLine = isBlankLine ? i + 1 : i;
    } else {
      currentLines.push(line);
    }
  }

  // Flush remaining
  flushChunk(lines.length - 1);

  return chunks;
}

/**
 * Split an oversized chunk into smaller pieces at sentence boundaries.
 */
function splitLargeChunk(text: string, baseStartLine: number): Chunk[] {
  const chunks: Chunk[] = [];
  const maxLen = CONSTANTS.MAX_CHUNK_CHARS;

  // Split by sentences (rough heuristic)
  const sentences = text.split(/(?<=[.!?])\s+/);
  let current = "";
  let sentenceCount = 0;

  for (const sentence of sentences) {
    if (current.length + sentence.length > maxLen && current.length > 0) {
      const lineCount = current.split("\n").length;
      chunks.push({
        content: current,
        startLine: baseStartLine,
        endLine: baseStartLine + lineCount - 1,
        landmarks: extractLandmarks(current),
      });
      baseStartLine += lineCount;
      current = sentence;
      sentenceCount = 1;
    } else {
      current += (sentenceCount > 0 ? " " : "") + sentence;
      sentenceCount++;
    }
  }

  if (current.trim().length > 0) {
    const lineCount = current.split("\n").length;
    chunks.push({
      content: current,
      startLine: baseStartLine,
      endLine: baseStartLine + lineCount - 1,
      landmarks: extractLandmarks(current),
    });
  }

  return chunks;
}

// ============================================================
// B. Landmark Extraction
// ============================================================

/**
 * Extract landmarks (key structural elements) from a chunk.
 * Landmarks help locate relevant chunks quickly without FTS.
 */
export function extractLandmarks(text: string): string[] {
  const landmarks: string[] = [];
  const seen = new Set<string>();

  function add(landmark: string): void {
    const key = landmark.toLowerCase();
    if (seen.has(key) || landmark.length < 2) return;
    seen.add(key);
    landmarks.push(landmark);
  }

  // Markdown headings
  const headings = text.match(/^#{1,6}\s+(.+)$/gm);
  if (headings) {
    for (const h of headings) {
      add(h.replace(/^#+\s*/, "").trim());
    }
  }

  // @mentions
  const mentions = text.match(/@[\w]+/g);
  if (mentions) {
    for (const m of mentions) add(m);
  }

  // Key-value pairs
  const kvPairs = text.match(/^[\w.]+\s*[:=]\s*.+$/gm);
  if (kvPairs) {
    for (const kv of kvPairs) {
      const key = kv.match(/^([\w.]+)\s*[:=]/)?.[1];
      if (key) add(`kv:${key}`);
    }
  }

  // File paths
  const paths = text.match(/(?:[\w./\\-]+\/)?[\w.-]+\.\w{1,10}/g);
  if (paths) {
    for (const p of paths) {
      if (p.includes("/") || p.includes("\\")) add(`file:${p}`);
    }
  }

  // Capitalized proper nouns (2+ words)
  const properNouns = text.match(/\b[A-Z][\w]*(?:\s+[A-Z][\w]*)+\b/g);
  if (properNouns) {
    for (const pn of properNouns) {
      if (pn.length >= 4 && pn.length <= 50) add(pn);
    }
  }

  // Code identifiers (snake_case, camelCase)
  const identifiers = text.match(/\b[a-z]+(?:_[a-z]+){1,5}\b|\b[a-z]+(?:[A-Z][a-z]+){1,5}\b/g);
  if (identifiers) {
    for (const id of identifiers) {
      if (id.length > 5) add(`code:${id}`);
    }
  }

  return landmarks;
}

// ============================================================
// C. TTL Lifecycle
// ============================================================

/**
 * Set TTL on a memory node. After TTL expires, maintenance will expire the node.
 */
export function setTTL(
  db: Database.Database,
  nodeId: string,
  ttlHours: number,
): void {
  const expiresAt = new Date(Date.now() + ttlHours * 60 * 60 * 1000).toISOString();

  db.prepare(`
    UPDATE memory_nodes
    SET ttl_expires_at = ?, updated_at = ?
    WHERE id = ?
  `).run(expiresAt, nowISO(), nodeId);
}

/**
 * Clear TTL from a node (make it permanent until decay handles it).
 */
export function clearTTL(db: Database.Database, nodeId: string): void {
  db.prepare(`
    UPDATE memory_nodes
    SET ttl_expires_at = NULL, updated_at = ?
    WHERE id = ?
  `).run(nowISO(), nodeId);
}

/**
 * Find all nodes with expired TTL.
 */
export function findExpiredTTL(
  db: Database.Database,
): Array<{ id: string; content: string; ttlExpiresAt: string }> {
  const now = nowISO();
  return db.prepare(`
    SELECT id, content, ttl_expires_at as ttlExpiresAt
    FROM memory_nodes
    WHERE ttl_expires_at IS NOT NULL
      AND ttl_expires_at < ?
      AND status = 'active'
  `).all(now) as Array<{ id: string; content: string; ttlExpiresAt: string }>;
}

/**
 * Expire nodes whose TTL has passed. Returns count of expired nodes.
 */
export function expireTTLNodes(db: Database.Database): number {
  const now = nowISO();

  const result = db.prepare(`
    UPDATE memory_nodes
    SET status = 'expired', updated_at = ?
    WHERE ttl_expires_at IS NOT NULL
      AND ttl_expires_at < ?
      AND status = 'active'
  `).run(now, now);

  return result.changes;
}

/**
 * Auto-set TTL for working_scratch nodes that don't have one.
 * Default: 24 hours.
 */
export function autoSetScratchTTL(
  db: Database.Database,
  defaultTTLHours = 24,
): number {
  const expiresAt = new Date(Date.now() + defaultTTLHours * 60 * 60 * 1000).toISOString();
  const now = nowISO();

  const result = db.prepare(`
    UPDATE memory_nodes
    SET ttl_expires_at = ?, updated_at = ?
    WHERE memory_type = 'working_scratch'
      AND status = 'active'
      AND ttl_expires_at IS NULL
  `).run(expiresAt, now);

  return result.changes;
}
