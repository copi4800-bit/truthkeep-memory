# TruthKeep Quickstart

## 5 Minutes To First Proof

1. Install the package locally.

```bash
pip install -e .
```

2. Store your first memory.

```bash
truthkeep remember "The release owner is Bao."
```

3. Recall it.

```bash
truthkeep recall "Who is the release owner?"
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
aegis-mcp
```

Or:

```bash
truthkeep mcp --json
```
