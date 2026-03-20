/**
 * Chimpanzee Layer — Tool craft, correction traces, interaction state.
 *
 * Như tinh tinh quan sát và bắt chước — học từ hành vi,
 * ghi nhớ sự chỉnh sửa, thích nghi theo tương tác.
 */

import type Database from "better-sqlite3";
import { newId, nowISO } from "../core/id.js";
import { jaccardSimilarity, tokenizeToSet } from "../core/normalize.js";

// ============================================================
// A. TOOL ARTIFACT LIFECYCLE
// ============================================================

/**
 * Record a successful tool usage pattern.
 */
export function recordToolSuccess(
  db: Database.Database,
  toolName: string,
  params: unknown,
  result: unknown,
  sessionKey?: string,
): string {
  const now = nowISO();

  // Check if this tool artifact already exists
  const existing = db.prepare(`
    SELECT id, success_count, reusability_score FROM tool_artifacts
    WHERE artifact_type = 'tool_trace'
      AND json_extract(source_text, '$.tool') = ?
    LIMIT 1
  `).get(toolName) as { id: string; success_count: number; reusability_score: number } | undefined;

  if (existing) {
    // Update existing artifact
    const newScore = computeReusabilityScore(existing.success_count + 1, 0, 0.5, 0.5);
    db.prepare(`
      UPDATE tool_artifacts
      SET success_count = success_count + 1,
          reusability_score = ?,
          last_used_at = ?,
          updated_at = ?
      WHERE id = ?
    `).run(newScore, now, now, existing.id);
    return existing.id;
  }

  const id = newId();
  db.prepare(`
    INSERT INTO tool_artifacts (
      id, artifact_type, language, source_text,
      approval_required, reusability_score,
      success_count, failure_count, last_used_at, created_at, updated_at
    ) VALUES (?, 'tool_trace', NULL, ?, 1, 0.3, 1, 0, ?, ?, ?)
  `).run(
    id,
    JSON.stringify({ tool: toolName, params, result, session: sessionKey }),
    now, now, now,
  );

  return id;
}

/**
 * Record a tool failure for learning.
 */
export function recordToolFailure(
  db: Database.Database,
  toolName: string,
  params: unknown,
  error: string,
  sessionKey?: string,
): string {
  const now = nowISO();

  // Check if this tool artifact exists
  const existing = db.prepare(`
    SELECT id, success_count, failure_count FROM tool_artifacts
    WHERE artifact_type = 'tool_trace'
      AND json_extract(source_text, '$.tool') = ?
    LIMIT 1
  `).get(toolName) as { id: string; success_count: number; failure_count: number } | undefined;

  if (existing) {
    const newScore = computeReusabilityScore(
      existing.success_count, existing.failure_count + 1, 0.5, 0.5,
    );
    db.prepare(`
      UPDATE tool_artifacts
      SET failure_count = failure_count + 1,
          reusability_score = ?,
          last_used_at = ?,
          updated_at = ?
      WHERE id = ?
    `).run(newScore, now, now, existing.id);
    return existing.id;
  }

  const id = newId();
  db.prepare(`
    INSERT INTO tool_artifacts (
      id, artifact_type, language, source_text,
      approval_required, reusability_score,
      success_count, failure_count, last_used_at, created_at, updated_at
    ) VALUES (?, 'tool_trace', NULL, ?, 1, 0.1, 0, 1, ?, ?, ?)
  `).run(
    id,
    JSON.stringify({ tool: toolName, params, error, session: sessionKey }),
    now, now, now,
  );

  return id;
}

/**
 * Compute reusability score for a tool artifact.
 * Formula: 0.6 × success_rate + 0.3 × approval_score + 0.1 × scope_fit
 */
export function computeReusabilityScore(
  successCount: number,
  failureCount: number,
  approvalScore: number,
  scopeFit: number,
): number {
  const total = successCount + failureCount;
  const successRate = total > 0 ? successCount / total : 0;
  return Math.min(1.0, 0.6 * successRate + 0.3 * approvalScore + 0.1 * scopeFit);
}

/**
 * Find reusable tool artifacts ranked by relevance.
 */
export function findReusableTools(
  db: Database.Database,
  toolName?: string,
  minReusability = 0.3,
): Array<{ id: string; toolName: string; reusabilityScore: number; successCount: number; failureCount: number }> {
  let query = `
    SELECT id, source_text, reusability_score, success_count, failure_count
    FROM tool_artifacts
    WHERE artifact_type = 'tool_trace'
      AND reusability_score >= ?
  `;
  const params: unknown[] = [minReusability];

  if (toolName) {
    query += " AND json_extract(source_text, '$.tool') = ?";
    params.push(toolName);
  }

  query += " ORDER BY reusability_score DESC, success_count DESC LIMIT 20";

  const rows = db.prepare(query).all(...params) as Array<{
    id: string; source_text: string; reusability_score: number;
    success_count: number; failure_count: number;
  }>;

  return rows.map((r) => {
    const parsed = JSON.parse(r.source_text);
    return {
      id: r.id,
      toolName: parsed.tool,
      reusabilityScore: r.reusability_score,
      successCount: r.success_count,
      failureCount: r.failure_count,
    };
  });
}

// ============================================================
// B. INTERACTION STATE TRACKING
// ============================================================

export interface InteractionSignals {
  frustrationIndex: number;
  brevityPreference: number;
  explorationPreference: number;
  correctionPressure: number;
  formalityPreference: number;
}

const DEFAULT_SIGNALS: InteractionSignals = {
  frustrationIndex: 0,
  brevityPreference: 0.5,
  explorationPreference: 0.5,
  correctionPressure: 0,
  formalityPreference: 0.5,
};

/**
 * Get or create interaction state for a session.
 */
export function getInteractionState(
  db: Database.Database,
  sessionKey: string,
): InteractionSignals {
  const row = db.prepare(
    "SELECT * FROM interaction_states WHERE session_id = ?",
  ).get(sessionKey) as {
    frustration_index: number;
    brevity_preference: number;
    exploration_preference: number;
    correction_pressure: number;
    formality_preference: number;
  } | undefined;

  if (!row) return { ...DEFAULT_SIGNALS };

  return {
    frustrationIndex: row.frustration_index,
    brevityPreference: row.brevity_preference,
    explorationPreference: row.exploration_preference,
    correctionPressure: row.correction_pressure,
    formalityPreference: row.formality_preference,
  };
}

/**
 * Update interaction state for a session based on observed signals.
 *
 * Uses exponential moving average to smooth signal changes.
 */
export function updateInteractionState(
  db: Database.Database,
  sessionKey: string,
  updates: Partial<InteractionSignals>,
): InteractionSignals {
  const now = nowISO();
  const alpha = 0.3; // EMA smoothing factor

  const current = getInteractionState(db, sessionKey);

  // Apply EMA for each signal
  const updated: InteractionSignals = {
    frustrationIndex: clamp(
      updates.frustrationIndex !== undefined
        ? alpha * updates.frustrationIndex + (1 - alpha) * current.frustrationIndex
        : current.frustrationIndex,
    ),
    brevityPreference: clamp(
      updates.brevityPreference !== undefined
        ? alpha * updates.brevityPreference + (1 - alpha) * current.brevityPreference
        : current.brevityPreference,
    ),
    explorationPreference: clamp(
      updates.explorationPreference !== undefined
        ? alpha * updates.explorationPreference + (1 - alpha) * current.explorationPreference
        : current.explorationPreference,
    ),
    correctionPressure: clamp(
      updates.correctionPressure !== undefined
        ? alpha * updates.correctionPressure + (1 - alpha) * current.correctionPressure
        : current.correctionPressure,
    ),
    formalityPreference: clamp(
      updates.formalityPreference !== undefined
        ? alpha * updates.formalityPreference + (1 - alpha) * current.formalityPreference
        : current.formalityPreference,
    ),
  };

  // Upsert
  db.prepare(`
    INSERT INTO interaction_states (id, session_id, frustration_index, brevity_preference,
      exploration_preference, correction_pressure, formality_preference, last_updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(session_id) DO UPDATE SET
      frustration_index = excluded.frustration_index,
      brevity_preference = excluded.brevity_preference,
      exploration_preference = excluded.exploration_preference,
      correction_pressure = excluded.correction_pressure,
      formality_preference = excluded.formality_preference,
      last_updated_at = excluded.last_updated_at
  `).run(
    newId(), sessionKey,
    updated.frustrationIndex, updated.brevityPreference,
    updated.explorationPreference, updated.correctionPressure,
    updated.formalityPreference, now,
  );

  return updated;
}

/**
 * Detect if a user message is a correction of a previous response.
 * Returns correction signals for interaction state update.
 */
export function detectCorrection(
  userMessage: string,
  previousResponse?: string,
): { isCorrection: boolean; correctionType: string; intensity: number } {
  const lower = userMessage.toLowerCase();

  // Correction indicators
  const strongCorrections = ["no", "wrong", "incorrect", "that's not", "not what i",
    "don't do", "stop", "không", "sai", "không phải"];
  const mildCorrections = ["actually", "instead", "rather", "but", "however",
    "thực ra", "mà", "nhưng", "thay vì"];
  const frustrationIndicators = ["again", "already told", "i said", "lại", "đã nói",
    "please just", "just do", "làm đi"];

  let intensity = 0;
  let correctionType = "none";

  for (const pattern of strongCorrections) {
    if (lower.includes(pattern)) {
      intensity = Math.max(intensity, 0.8);
      correctionType = "behavioral";
    }
  }

  for (const pattern of mildCorrections) {
    if (lower.includes(pattern)) {
      intensity = Math.max(intensity, 0.4);
      if (correctionType === "none") correctionType = "phrasing";
    }
  }

  for (const pattern of frustrationIndicators) {
    if (lower.includes(pattern)) {
      intensity = Math.min(1.0, intensity + 0.2);
    }
  }

  return {
    isCorrection: intensity > 0.2,
    correctionType: intensity > 0.2 ? correctionType : "none",
    intensity,
  };
}

// ============================================================
// C. CORRECTION TRACE MATCHING & LEARNING
// ============================================================

/**
 * Record a user correction for future learning.
 */
export function recordCorrection(
  db: Database.Database,
  context: string,
  proposal: string,
  correction: string,
  opts?: {
    scope?: string;
    correctionType?: string;
    confidence?: number;
    appliesTo?: Record<string, unknown>;
  },
): string {
  const now = nowISO();
  const id = newId();

  db.prepare(`
    INSERT INTO correction_traces (
      id, scope, context_snapshot, agent_proposal, user_correction,
      final_accepted_form, correction_type, confidence,
      applies_to_json, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    id,
    opts?.scope ?? null,
    context,
    proposal,
    correction,
    correction, // final_accepted = correction by default
    opts?.correctionType ?? "behavioral",
    opts?.confidence ?? 0.5,
    opts?.appliesTo ? JSON.stringify(opts.appliesTo) : null,
    now,
  );

  // Log correction event
  db.prepare(`
    INSERT INTO memory_events (id, event_type, scope, payload_json, created_at)
    VALUES (?, 'correction_recorded', ?, ?, ?)
  `).run(newId(), opts?.scope ?? null, JSON.stringify({ correction_type: opts?.correctionType }), now);

  return id;
}

/**
 * Find correction traces applicable to the current context.
 * Ranks by: 0.5×confidence + 0.3×domain_match + 0.2×recency_bonus
 */
export function findApplicableCorrections(
  db: Database.Database,
  context: string,
  opts?: { scope?: string; minConfidence?: number },
): Array<{ id: string; correction: string; score: number; correctionType: string }> {
  const minConfidence = opts?.minConfidence ?? 0.3;

  const traces = db.prepare(`
    SELECT id, context_snapshot, user_correction, correction_type, confidence, created_at
    FROM correction_traces
    WHERE confidence >= ?
    ORDER BY created_at DESC
    LIMIT 50
  `).all(minConfidence) as Array<{
    id: string;
    context_snapshot: string;
    user_correction: string;
    correction_type: string;
    confidence: number;
    created_at: string;
  }>;

  const contextTokens = tokenizeToSet(context);
  const now = Date.now();

  const scored = traces.map((trace) => {
    const traceTokens = tokenizeToSet(trace.context_snapshot);
    const domainMatch = jaccardSimilarity(contextTokens, traceTokens);

    // Recency bonus: 1.0 for today, decaying over 30 days
    const ageMs = now - new Date(trace.created_at).getTime();
    const ageDays = ageMs / (1000 * 60 * 60 * 24);
    const recencyBonus = Math.max(0, 1 - ageDays / 30);

    const score = 0.5 * trace.confidence + 0.3 * domainMatch + 0.2 * recencyBonus;

    return {
      id: trace.id,
      correction: trace.user_correction,
      score,
      correctionType: trace.correction_type,
    };
  });

  return scored
    .filter((s) => s.score >= 0.2)
    .sort((a, b) => b.score - a.score)
    .slice(0, 10);
}

/**
 * Mark a correction trace as reused.
 */
export function markCorrectionReused(db: Database.Database, traceId: string): void {
  db.prepare(
    "UPDATE correction_traces SET last_reused_at = ? WHERE id = ?",
  ).run(nowISO(), traceId);
}

// ============================================================
// D. BEHAVIORAL ADAPTATION
// ============================================================

/**
 * Compute behavioral modifiers based on interaction state.
 * Returns adjustments to apply to retrieval and output.
 */
export function computeBehavioralModifiers(
  signals: InteractionSignals,
): {
  maxResultsMultiplier: number;
  verbosityMultiplier: number;
  explorationBias: number;
  procedureBoost: number;
} {
  // High frustration/correction → fewer, more direct results
  const frustrationEffect = signals.frustrationIndex * 0.5 + signals.correctionPressure * 0.5;

  return {
    // Reduce results when frustrated
    maxResultsMultiplier: Math.max(0.5, 1.0 - frustrationEffect * 0.5),
    // Reduce verbosity when brevity preferred
    verbosityMultiplier: Math.max(0.3, 1.0 - signals.brevityPreference * 0.7),
    // More exploration when preferred
    explorationBias: signals.explorationPreference,
    // Boost procedures when user wants action, not explanation
    procedureBoost: frustrationEffect > 0.5 ? 0.3 : 0,
  };
}

// --- Helpers ---

function clamp(v: number, min = 0, max = 1): number {
  return Math.max(min, Math.min(max, v));
}
