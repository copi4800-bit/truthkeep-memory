# Task List: Aegis v10 Complete Definition

## Phase 1: Semantic & Architectural Completion
- [ ] Task 1.1: Update `aegis_py/v10/models.py` with `fact_kind`, `singleton_fact`, and enhanced lifecycle fields.
- [ ] Task 1.2: Refactor `aegis_py/v10/scorer.py` to formalize score tiers (base, judge delta, life delta, hard constraints).
- [ ] Task 1.3: Update `aegis_py/v10/adapter.py` for rich signal mapping (evidence, conflict, correction, lifecycle).

## Phase 2: Runtime & Retrieval Completion
- [ ] Task 2.1: Upgrade `aegis_py/v10/query_signals.py` to support intents and normalized [0,1] signals.
- [ ] Task 2.2: Refactor `aegis_py/retrieval/search.py` to ensure v10 reranking is the final gatekeeper.
- [ ] Task 2.3: Implement operational modes (`v10_primary`, `shadow_v10`, `v10_primary`) via configuration/flags.

## Phase 3: UX & Explanation Completion
- [ ] Task 3.1: Upgrade `aegis_py/v10/translator.py` for compact, standard, and deep narratives.
- [ ] Task 3.2: Expose the `v10_audit` payload in `aegis_py/surface.py`.
- [ ] Task 3.3: Update `aegis_py/health_surface.py` to reflect v10 metrics.

## Phase 4: Quality & Validation
- [ ] Task 4.1: Create comprehensive integration tests in `tests/test_v10_full_path.py` (no SQL mocks).
- [ ] Task 4.2: Develop and run `scripts/v10_shadow_eval.py` for v10 vs v10 comparison.
- [ ] Task 4.3: Execute v10-specific stress gauntlet.

## Verification
- [ ] Verify SC-001 (Pytest pass)
- [ ] Verify SC-002 (Shadow eval success)
- [ ] Verify SC-003 (Faithful explanations)
- [ ] Verify SC-004 (Latency within limits)
- [ ] Verify SC-005 (Audit findings addressed)

