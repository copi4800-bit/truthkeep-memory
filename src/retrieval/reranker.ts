import type { MemoryNode, RerankerWeights } from "../core/models.js";
import { CONSTANTS, DEFAULT_RERANKER_WEIGHTS } from "../core/models.js";
import { daysBetween } from "../core/id.js";

export interface RankedCandidate {
  node: MemoryNode;
  score: number;
  signals: SignalSet;
}

export interface SignalSet {
  ftsScore: number;
  activationScore: number;
  entityOverlap: number;
  retention: number;
  scopeFit: number;
  procedureBonus: number;
  overridePriority: number;
}

// --- Retention Dynamics ---

/**
 * Compute base strength from importance, salience, and memory type.
 */
function computeBaseStrength(node: MemoryNode): number {
  const raw =
    CONSTANTS.IMPORTANCE_WEIGHT * node.importance +
    CONSTANTS.SALIENCE_WEIGHT * node.salience;

  const typeBonus = CONSTANTS.MEMORY_TYPE_STRENGTH[node.memory_type] ?? 0;
  const overrideBonus = node.override_priority * CONSTANTS.OVERRIDE_WEIGHT;

  return Math.min(1.0, raw + typeBonus + overrideBonus);
}

/**
 * Compute spacing-aware reinforcement score.
 */
function computeReinforcementScore(node: MemoryNode): number {
  if (node.recall_count === 0) return 0;

  const recallBonus = Math.log2(1 + node.recall_count);
  const frequencyBonus = Math.log2(1 + node.frequency_count) * 0.5;

  let spacingBonus = 0;
  if (node.first_seen_at && node.last_seen_at) {
    const totalSpanDays = daysBetween(node.last_seen_at, node.first_seen_at);
    if (totalSpanDays >= 1) {
      const avgInterval = totalSpanDays / Math.max(1, node.recall_count);
      const optimalInterval = Math.pow(2, node.recall_count - 1);
      let ratio = avgInterval / optimalInterval;
      ratio = Math.max(0.1, Math.min(2, ratio));
      spacingBonus =
        Math.exp(-Math.pow(Math.log(ratio), 2) / 2) * CONSTANTS.SPACING_WEIGHT;
    }
  }

  return recallBonus + spacingBonus + frequencyBonus;
}

/**
 * Compute dynamic retention for a memory node.
 * retention = base_strength * exp(-dynamic_decay * delta_t)
 */
export function computeRetention(node: MemoryNode, nowISO: string): number {
  // Crystallized and trauma memories don't decay
  if (
    node.memory_state === "crystallized" ||
    node.memory_type === "trauma" ||
    node.memory_type === "invariant"
  ) {
    return 1.0;
  }

  const accessTime = node.last_access_at ?? node.created_at;
  const deltaT = daysBetween(nowISO, accessTime);

  const baseStrength = computeBaseStrength(node);
  const reinforcement = computeReinforcementScore(node);

  // Dynamic decay: reduced by reinforcement, increased by interference
  let dynamicDecay = node.base_decay_rate / (1 + reinforcement);
  dynamicDecay *= 1 + node.interference_score;

  return baseStrength * Math.exp(-dynamicDecay * deltaT);
}

// --- Final Score ---

/**
 * Compute the final reranking score for a candidate.
 */
export function computeFinalScore(
  node: MemoryNode,
  signals: SignalSet,
  weights: RerankerWeights = DEFAULT_RERANKER_WEIGHTS,
): number {
  let raw =
    weights.fts * signals.ftsScore +
    weights.activation * signals.activationScore +
    weights.entity * signals.entityOverlap +
    weights.retention * signals.retention +
    weights.scope * signals.scopeFit +
    weights.procedure * signals.procedureBonus;

  // Elephant override bonus
  raw += signals.overridePriority * weights.override;

  // Interference penalty
  if (node.interference_score > 0) {
    raw *= 1 - node.interference_score * weights.interference_penalty;
  }

  // Suppression penalty
  if (node.memory_state === "suppressed") {
    raw *= CONSTANTS.SUPPRESSION_MULTIPLIER;
  }

  return raw;
}

// --- Score Normalization ---

/**
 * Normalize raw scores to [0, 1] using sigmoid.
 */
export function normalizeScores(rawScores: number[]): number[] {
  if (rawScores.length === 0) return [];
  if (rawScores.length === 1) return [1.0];

  const max = Math.max(...rawScores);
  const min = Math.min(...rawScores);
  const range = max - min;

  if (range === 0) return rawScores.map(() => 1.0);

  const sorted = [...rawScores].sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)];
  const steepness = 4.0 / range;

  return rawScores.map((s) => 1 / (1 + Math.exp(-steepness * (s - median))));
}

/**
 * Compute scope fitness score [0, 1].
 */
export function computeScopeFit(
  nodeScope: string | null,
  sessionKey?: string,
): number {
  if (!nodeScope) return 0.5; // No scope = neutral
  if (nodeScope === "global") return 0.9; // Global is always relevant
  if (sessionKey && nodeScope === "session") return 0.8; // Session match
  if (nodeScope === "user") return 0.7; // User scope is generally relevant
  return 0.4; // Other scopes
}
