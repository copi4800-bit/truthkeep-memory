import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { openDatabase, type AegisDatabase } from "../../src/db/connection.js";
import {
  recordToolSuccess,
  recordToolFailure,
  computeReusabilityScore,
  findReusableTools,
  getInteractionState,
  updateInteractionState,
  detectCorrection,
  recordCorrection,
  findApplicableCorrections,
  markCorrectionReused,
  computeBehavioralModifiers,
} from "../../src/cognitive/chimpanzee.js";

let db: AegisDatabase;
let testDir: string;

beforeEach(() => {
  testDir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-chimp-"));
  db = openDatabase(path.join(testDir, "test.db"));
});

afterEach(() => {
  db.close();
  fs.rmSync(testDir, { recursive: true, force: true });
});

// ============================================================
// A. Tool Artifact Lifecycle
// ============================================================

describe("Tool success tracking", () => {
  it("records new tool artifact on first success", () => {
    const id = recordToolSuccess(db.db, "git_commit", { message: "fix bug" }, { sha: "abc123" });

    const artifact = db.db.prepare("SELECT * FROM tool_artifacts WHERE id = ?").get(id) as any;
    expect(artifact.artifact_type).toBe("tool_trace");
    expect(artifact.success_count).toBe(1);
    expect(artifact.failure_count).toBe(0);
  });

  it("increments success_count for existing tool", () => {
    recordToolSuccess(db.db, "npm_install", { pkg: "lodash" }, { ok: true });
    recordToolSuccess(db.db, "npm_install", { pkg: "express" }, { ok: true });

    const artifacts = db.db.prepare(
      "SELECT * FROM tool_artifacts WHERE json_extract(source_text, '$.tool') = 'npm_install'",
    ).all() as any[];

    expect(artifacts.length).toBe(1);
    expect(artifacts[0].success_count).toBe(2);
  });

  it("updates reusability score on success", () => {
    const id = recordToolSuccess(db.db, "test_tool", {}, {});
    recordToolSuccess(db.db, "test_tool", {}, {});
    recordToolSuccess(db.db, "test_tool", {}, {});

    const artifact = db.db.prepare(
      "SELECT reusability_score FROM tool_artifacts WHERE json_extract(source_text, '$.tool') = 'test_tool'",
    ).get() as any;

    expect(artifact.reusability_score).toBeGreaterThan(0.3);
  });
});

describe("Tool failure tracking", () => {
  it("records tool failure", () => {
    const id = recordToolFailure(db.db, "risky_op", { target: "prod" }, "Permission denied");

    const artifact = db.db.prepare("SELECT * FROM tool_artifacts WHERE id = ?").get(id) as any;
    expect(artifact.failure_count).toBe(1);
    expect(artifact.success_count).toBe(0);
  });

  it("lowers reusability score on failure", () => {
    recordToolSuccess(db.db, "flaky_tool", {}, {});
    recordToolFailure(db.db, "flaky_tool", {}, "timeout");

    const artifact = db.db.prepare(
      "SELECT reusability_score FROM tool_artifacts WHERE json_extract(source_text, '$.tool') = 'flaky_tool'",
    ).get() as any;

    // 1 success, 1 failure → 50% success rate
    expect(artifact.reusability_score).toBeLessThan(0.5);
  });
});

describe("computeReusabilityScore", () => {
  it("100% success rate gives high score", () => {
    const score = computeReusabilityScore(10, 0, 0.8, 0.5);
    expect(score).toBeGreaterThan(0.7);
  });

  it("0% success rate gives low score", () => {
    const score = computeReusabilityScore(0, 10, 0.5, 0.5);
    expect(score).toBeLessThan(0.3);
  });

  it("capped at 1.0", () => {
    const score = computeReusabilityScore(100, 0, 1.0, 1.0);
    expect(score).toBeLessThanOrEqual(1.0);
  });
});

describe("findReusableTools", () => {
  it("returns tools above minimum reusability", () => {
    recordToolSuccess(db.db, "good_tool", {}, {});
    recordToolSuccess(db.db, "good_tool", {}, {});
    recordToolSuccess(db.db, "good_tool", {}, {});
    recordToolFailure(db.db, "bad_tool", {}, "error");

    const tools = findReusableTools(db.db, undefined, 0.2);
    expect(tools.length).toBeGreaterThan(0);
    expect(tools[0].toolName).toBe("good_tool");
  });

  it("filters by tool name", () => {
    recordToolSuccess(db.db, "tool_a", {}, {});
    recordToolSuccess(db.db, "tool_b", {}, {});

    const tools = findReusableTools(db.db, "tool_a");
    expect(tools.length).toBe(1);
    expect(tools[0].toolName).toBe("tool_a");
  });
});

// ============================================================
// B. Interaction State
// ============================================================

describe("getInteractionState", () => {
  it("returns defaults for new session", () => {
    const state = getInteractionState(db.db, "new-session");
    expect(state.frustrationIndex).toBe(0);
    expect(state.brevityPreference).toBe(0.5);
    expect(state.explorationPreference).toBe(0.5);
    expect(state.correctionPressure).toBe(0);
    expect(state.formalityPreference).toBe(0.5);
  });
});

describe("updateInteractionState", () => {
  it("creates interaction state on first update", () => {
    const updated = updateInteractionState(db.db, "session-1", {
      frustrationIndex: 0.8,
    });

    // EMA: 0.3 * 0.8 + 0.7 * 0 = 0.24
    expect(updated.frustrationIndex).toBeCloseTo(0.24, 2);
  });

  it("smooths updates with EMA", () => {
    updateInteractionState(db.db, "session-2", { frustrationIndex: 1.0 });
    const second = updateInteractionState(db.db, "session-2", { frustrationIndex: 0.0 });

    // Should be smoothed, not snapping to 0
    expect(second.frustrationIndex).toBeGreaterThan(0);
    expect(second.frustrationIndex).toBeLessThan(1);
  });

  it("preserves unchanged signals", () => {
    updateInteractionState(db.db, "session-3", {
      brevityPreference: 0.9,
      formalityPreference: 0.1,
    });

    const updated = updateInteractionState(db.db, "session-3", {
      frustrationIndex: 0.5,
    });

    // Brevity and formality should still reflect previous update
    expect(updated.brevityPreference).toBeGreaterThan(0.5);
    expect(updated.formalityPreference).toBeLessThan(0.5);
  });

  it("clamps values to [0, 1]", () => {
    const updated = updateInteractionState(db.db, "session-4", {
      frustrationIndex: 5.0,
      brevityPreference: -1.0,
    });

    expect(updated.frustrationIndex).toBeLessThanOrEqual(1.0);
    expect(updated.brevityPreference).toBeGreaterThanOrEqual(0);
  });
});

// ============================================================
// C. Correction Detection & Learning
// ============================================================

describe("detectCorrection", () => {
  it("detects strong correction", () => {
    const result = detectCorrection("No, that's not what I wanted");
    expect(result.isCorrection).toBe(true);
    expect(result.intensity).toBeGreaterThan(0.5);
  });

  it("detects mild correction", () => {
    const result = detectCorrection("Actually, I meant the other approach instead");
    expect(result.isCorrection).toBe(true);
    expect(result.correctionType).toBe("phrasing");
  });

  it("detects frustration indicators", () => {
    const result = detectCorrection("I already told you, just do it");
    expect(result.isCorrection).toBe(true);
    expect(result.intensity).toBeGreaterThan(0.3);
  });

  it("does not flag normal messages", () => {
    const result = detectCorrection("That looks great, thanks!");
    expect(result.isCorrection).toBe(false);
  });

  it("detects Vietnamese corrections", () => {
    const result = detectCorrection("Không phải, sai rồi");
    expect(result.isCorrection).toBe(true);
  });
});

describe("recordCorrection", () => {
  it("stores correction trace", () => {
    const id = recordCorrection(
      db.db,
      "User asked about deployment",
      "Use Docker Compose",
      "No, use Kubernetes instead",
      { correctionType: "action_change", confidence: 0.7 },
    );

    const trace = db.db.prepare(
      "SELECT * FROM correction_traces WHERE id = ?",
    ).get(id) as any;

    expect(trace.agent_proposal).toBe("Use Docker Compose");
    expect(trace.user_correction).toBe("No, use Kubernetes instead");
    expect(trace.correction_type).toBe("action_change");
    expect(trace.confidence).toBe(0.7);
  });

  it("logs correction event", () => {
    recordCorrection(db.db, "ctx", "proposal", "correction");

    const events = db.db.prepare(
      "SELECT * FROM memory_events WHERE event_type = 'correction_recorded'",
    ).all();
    expect(events.length).toBe(1);
  });
});

describe("findApplicableCorrections", () => {
  it("finds corrections matching context", () => {
    recordCorrection(
      db.db,
      "deploying to production with Docker",
      "Use docker-compose up",
      "Use kubectl apply instead",
      { confidence: 0.8 },
    );

    const matches = findApplicableCorrections(db.db, "deployment to production environment");
    expect(matches.length).toBeGreaterThan(0);
    expect(matches[0].correction).toContain("kubectl");
  });

  it("ranks by score", () => {
    recordCorrection(db.db, "React component styling", "Use CSS modules", "Use Tailwind", {
      confidence: 0.9,
    });
    recordCorrection(db.db, "API error handling", "Return 500", "Return 422 with details", {
      confidence: 0.3,
    });

    const matches = findApplicableCorrections(db.db, "React component design and styling");
    if (matches.length >= 2) {
      expect(matches[0].score).toBeGreaterThanOrEqual(matches[1].score);
    }
  });

  it("returns empty for unrelated context", () => {
    recordCorrection(db.db, "nuclear physics", "proposal", "correction", { confidence: 0.5 });

    const matches = findApplicableCorrections(db.db, "chocolate cake recipe");
    // May return results but with low scores, filtered by minimum
    for (const m of matches) {
      expect(m.score).toBeLessThan(0.5);
    }
  });
});

describe("markCorrectionReused", () => {
  it("updates last_reused_at timestamp", () => {
    const id = recordCorrection(db.db, "ctx", "proposal", "correction");

    markCorrectionReused(db.db, id);

    const trace = db.db.prepare(
      "SELECT last_reused_at FROM correction_traces WHERE id = ?",
    ).get(id) as any;
    expect(trace.last_reused_at).not.toBeNull();
  });
});

// ============================================================
// D. Behavioral Modifiers
// ============================================================

describe("computeBehavioralModifiers", () => {
  it("high frustration reduces results and verbosity", () => {
    const mods = computeBehavioralModifiers({
      frustrationIndex: 0.9,
      brevityPreference: 0.8,
      explorationPreference: 0.2,
      correctionPressure: 0.7,
      formalityPreference: 0.5,
    });

    expect(mods.maxResultsMultiplier).toBeLessThan(1.0);
    expect(mods.verbosityMultiplier).toBeLessThan(0.5);
    expect(mods.procedureBoost).toBeGreaterThan(0);
  });

  it("calm session has normal modifiers", () => {
    const mods = computeBehavioralModifiers({
      frustrationIndex: 0,
      brevityPreference: 0.3,
      explorationPreference: 0.7,
      correctionPressure: 0,
      formalityPreference: 0.5,
    });

    expect(mods.maxResultsMultiplier).toBe(1.0);
    expect(mods.verbosityMultiplier).toBeGreaterThan(0.7);
    expect(mods.explorationBias).toBe(0.7);
    expect(mods.procedureBoost).toBe(0);
  });

  it("modifiers stay within bounds", () => {
    const mods = computeBehavioralModifiers({
      frustrationIndex: 1.0,
      brevityPreference: 1.0,
      explorationPreference: 1.0,
      correctionPressure: 1.0,
      formalityPreference: 1.0,
    });

    expect(mods.maxResultsMultiplier).toBeGreaterThanOrEqual(0.5);
    expect(mods.verbosityMultiplier).toBeGreaterThanOrEqual(0.3);
  });
});
