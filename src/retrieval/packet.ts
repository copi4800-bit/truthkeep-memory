import type { MemoryNode, MemoryType } from "../core/models.js";
import { truncate } from "../core/normalize.js";

/**
 * OpenClaw-compatible MemorySearchResult.
 * Matches the interface exactly from openclaw/src/memory/types.ts
 */
export interface MemorySearchResult {
  path: string;
  startLine: number;
  endLine: number;
  score: number;
  snippet: string;
  source: "memory" | "sessions";
  citation?: string;
}

export interface PacketCandidate {
  node: MemoryNode;
  score: number;
  explanation: string;
  hopCount?: number;
  matchedEntities?: string[];
  inferredVia?: string;
}

/**
 * Convert an Aegis v3 node to an OpenClaw MemorySearchResult.
 */
export function toMemorySearchResult(
  node: MemoryNode,
  score: number,
  explanation: string,
): MemorySearchResult {
  return {
    path: node.source_path ?? `aegis://${node.memory_type}/${node.id}`,
    startLine: node.source_start_line ?? 0,
    endLine: node.source_end_line ?? 0,
    score: clampScore(score),
    snippet: truncate(node.content, 500),
    source: mapScope(node.scope),
    citation: formatCitation(node, explanation),
  };
}

/**
 * Stage 7: Assemble the final memory packet.
 *
 * - Elephant overrides always come first (score = 1.0)
 * - Then ranked candidates sorted by score
 * - Deduplication by path
 * - Respects maxResults limit
 */
export function assemblePacket(
  candidates: PacketCandidate[],
  elephantOverrides: PacketCandidate[],
  maxResults: number,
): MemorySearchResult[] {
  const packet: MemorySearchResult[] = [];
  const seenPaths = new Set<string>();

  // Elephant overrides first
  for (const override of elephantOverrides) {
    if (packet.length >= maxResults) break;
    const result = toMemorySearchResult(override.node, 1.0, "safety_override");
    if (seenPaths.has(result.path)) continue;
    seenPaths.add(result.path);
    packet.push(result);
  }

  // Ranked candidates
  for (const candidate of candidates) {
    if (packet.length >= maxResults) break;
    const result = toMemorySearchResult(
      candidate.node,
      candidate.score,
      candidate.explanation,
    );
    if (seenPaths.has(result.path)) continue;
    seenPaths.add(result.path);
    packet.push(result);
  }

  return packet;
}

// --- Helpers ---

function clampScore(score: number): number {
  return Math.max(0, Math.min(1, score));
}

function mapScope(scope: string | null): "memory" | "sessions" {
  return scope === "session" ? "sessions" : "memory";
}

function formatCitation(node: MemoryNode, explanation: string): string {
  const prefix = `[${node.memory_type}]`;
  const subject = node.canonical_subject ? ` ${node.canonical_subject}` : "";
  const state = node.memory_state !== "volatile" ? ` (${node.memory_state})` : "";
  return `${prefix}${subject}${state} — ${explanation}`;
}

/**
 * Build human-readable explanation for why a result was included.
 */
export function buildExplanation(candidate: PacketCandidate): string {
  const parts: string[] = [];

  if (candidate.node.memory_type === "trauma" || candidate.node.memory_type === "invariant") {
    parts.push("safety override");
  }
  if (candidate.hopCount !== undefined && candidate.hopCount > 0) {
    parts.push(`graph activation (hop ${candidate.hopCount})`);
  }
  if (candidate.matchedEntities && candidate.matchedEntities.length > 0) {
    parts.push("entity: " + candidate.matchedEntities.join(", "));
  }
  if (candidate.node.memory_state === "crystallized") {
    parts.push("crystallized knowledge");
  }
  if (candidate.inferredVia) {
    parts.push("inferred via " + candidate.inferredVia);
  }

  return parts.join("; ") || "relevance match";
}
