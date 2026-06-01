# TruthKeep Quickstart

## 5 Minutes To First Proof

1. Install the package locally.

```bash
pip install -e .
```

2. Check local runtime and plugin readiness.

```bash
truthkeep-check
```

3. Run the setup helper.

```bash
truthkeep-setup
```

4. Inspect the whole-system field snapshot.

```bash
truthkeep field-snapshot
```

5. Run the short proof flow.

```bash
python scripts/prove_it.py
```

You should now have:
- a local SQLite memory database
- correction-aware recall
- a visible `Xi(t)` field snapshot
- a short proof artifact showing TruthKeep's correctness-first behavior

## Standalone Commands

```bash
truthkeep status
truthkeep remember "Bao prefers black coffee."
truthkeep correct "Correction: Bao prefers green tea."
truthkeep recall "What does Bao prefer to drink?"
truthkeep field-snapshot
truthkeep prove-it
```

## MCP Path

```bash
truthkeep-mcp
```

Or:

```bash
truthkeep mcp --json
```

Compatibility aliases also remain available:

```bash
aegis-check
aegis-setup
aegis-mcp
```

## Python SDK

You can also use TruthKeep directly from Python:

```python
from truthkeep import TruthKeep

# Auto-configure with default settings
tk = TruthKeep.auto()

# Store a memory
tk.remember("The capital of France is Paris", scope_id="geography")

# Recall with governed truth handling
results = tk.recall("What is the capital of France?", scope_id="geography")
for r in results:
    print(r["memory"]["content"])

# Correct a memory (old fact is superseded)
tk.correct("The capital of Japan is Tokyo", subject="capital of Japan", scope_id="geography")

# Check system health
print(tk.status())
```

The `TruthKeep` class inherits from `Aegis` and provides:
- `remember()` — store a new memory
- `recall()` — retrieve memories with governance and truth handling
- `correct()` — update a fact (supersedes the old one)
- `status()` — health snapshot of the memory engine

## API Reference

Full API reference documentation: `docs/API_REFERENCE.md` *(coming soon)*

For the mathematical foundations powering TruthKeep, see [docs/MATH_ARCHITECTURE.md](docs/MATH_ARCHITECTURE.md).
