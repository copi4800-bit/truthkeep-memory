# Tasks: Aegis v10 Runtime

**Input**: Design documents from `/specs/069-aegis-v10-runtime/`
**Prerequisites**: plan.md, spec.md

**Tests**: This feature requires automated pytest coverage for ingest, governance, transitions, and background planning.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Phase 1: Setup

- [x] T001 Create feature spec and plan in `specs/069-aegis-v10-runtime/`
- [x] T002 Create feature branch `069-aegis-v10-runtime`

## Phase 2: Foundational

- [x] T003 Add v10 governance-shell migration in `aegis_py/storage/migrations/003_v7_governance_shell.sql`
- [x] T004 Extend storage helpers for governance events and state transitions in `aegis_py/storage/manager.py`
- [x] T005 [P] Add v10 package scaffolding in `aegis_py/v10/__init__.py`

## Phase 3: User Story 1 - Trusted Admission Pipeline (Priority: P1)

**Goal**: Evidence-first ingest with validation and policy gating.

**Independent Test**: Admit one strong fact and block one weak fact while retaining evidence and governance records.

- [x] T006 [P] [US1] Implement v10 policy gate in `aegis_py/v10/policy_gate.py`
- [x] T007 [US1] Wire ingest to the v10 policy gate in `aegis_py/memory/ingest.py`
- [x] T008 [P] [US1] Add tests for admitted and blocked v10 candidates in `tests/test_v7_runtime.py`

## Phase 4: User Story 2 - Explicit Memory State Governance (Priority: P1)

**Goal**: Persist explicit v10 state and audit transitions.

**Independent Test**: Archive a memory and verify state history plus governance inspection.

- [x] T009 [P] [US2] Implement v10 state machine in `aegis_py/v10/state_machine.py`
- [x] T010 [US2] Persist `memory_state` alongside admission metadata in `aegis_py/storage/models.py` and `aegis_py/storage/manager.py`
- [x] T011 [P] [US2] Add transition audit coverage in `tests/test_v7_runtime.py`

## Phase 5: User Story 3 - Orchestrated Retrieval And Shadow Background Planning (Priority: P2)

**Goal**: Add specialized storage surfaces, retrieval orchestration, and shadow-only background planning.

**Independent Test**: Use runtime methods to create retrieval bundles and background proposals without direct mutation.

- [x] T012 [P] [US3] Implement specialized storage facades in `aegis_py/v10/storage_surfaces.py`
- [x] T013 [P] [US3] Implement governed background planning in `aegis_py/v10/background.py`
- [x] T014 [P] [US3] Implement retrieval orchestrator in `aegis_py/v10/retrieval_orchestrator.py`
- [x] T015 [US3] Wire the v10 runtime into `aegis_py/app.py`
- [x] T016 [P] [US3] Add background-planning coverage in `tests/test_v7_runtime.py`

## Phase 6: Polish

- [x] T017 Update runtime-facing docs in `README.md`
- [x] T018 Run targeted pytest verification for v10 runtime behavior
- [x] T019 Summarize remaining gaps between `11.md` and the implemented runtime in `specs/069-aegis-v10-runtime/plan.md` or final report

