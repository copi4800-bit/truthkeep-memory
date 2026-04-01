# Memory Aegis v10 (The Constitutional Memory Engine)

Mathematical truth-alignment, governance, and judgment engine for AI agents.

## Build & Run

### Quick Install
```bash
npm install          # Auto-installs Python deps + creates .venv
# OR
bash install.sh      # Manual install script
# OR
pip install -e .     # Python developer mode
```

### Run MCP Server
```bash
export PYTHONPATH=$PYTHONPATH:.
python3 aegis_py/mcp/server.py
```

### Run Tests
```bash
export PYTHONPATH=$PYTHONPATH:.
python3 -m pytest tests/
python3 scripts/v10_gauntlet_test.py  # Governance stress test
```

## Workflow Contract
- Feature truth: `specs/*`
- Constitution: `.specify/memory/constitution.md`
- Orchestration/status: `.planning/*`
- Workflow contract: `specs/*` + `.specify/memory/constitution.md` with `.planning/*` as orchestration only

## Rule
- Use GSD to map, sequence, and execute work.
- Use Spec Kit to define scope, plan, and tasks.
- Check the active feature in `specs/*` before using `/gsd:*` for material work.
- If no active feature fits, update or create the Spec Kit artifacts first.
- Do not implement major feature work from `.planning/` alone.
- If `.planning/` and `specs/*` disagree, `specs/*` wins.

## Tech Stack
- Python 3.11+
- SQLite + FTS5
- MCP Python SDK (fastmcp)

## Coding Conventions
- Standard Library first (Zero-dependency goal)
- Type hints for all functions
- Dataclasses for memory models
- SQL migrations in `aegis_py/storage/migrations/`

## V10 Architecture
- `v10/engine.py`: Constitutional Governance Engine (C0-C4 policy pipeline)
- `v10/policy.py`: MemoryConstitution with 5-tier precedence enforcement
- `v10/truth_registry.py`: Margin-aware Winner/Contender/Loser slot management
- `v10/review.py`: Priority-based review queue for high-entropy memories
- `v10/events.py`: Full audit trail for every governance decision
- `facade.py`: Zero-config API (remember/recall/correct/status)
