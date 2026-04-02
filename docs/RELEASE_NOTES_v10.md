# TruthKeep Memory v10

Initial public release of the TruthKeep Memory surface.

Highlights:

- Truth-aware memory selection with `winner / contender / superseded`
- Spotlight and full-core showcase surfaces
- Truth spotlight benchmark, gate, report, and release bundle
- Broader gauntlet coverage across truth, scale, adversarial, recovery, and ingest pressure
- Long-horizon survival validation for current truth and memory cleanup behavior

Validation status at release:

- `pytest -q tests` -> `32 passed`
- long-horizon `90d / 365d` survival scenarios passing

Recommended first commands:

```bash
python3 scripts/demo_core_showcase.py
python3 scripts/aegis_gauntlet.py
python3 scripts/long_horizon_memory_survival.py
```
