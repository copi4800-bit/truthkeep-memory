# TruthKeep Proof Hub

TruthKeep is strongest when it has to preserve *current truth* instead of merely surfacing the nearest match.

## What To Run

### 30-second proof

```bash
python scripts/prove_it.py
```

### Spotlight benchmark

```bash
python scripts/benchmark_truth_spotlight.py
python scripts/check_truth_spotlight_gate.py
```

### Long-horizon survival

```bash
python scripts/long_horizon_memory_survival.py
```

### Compressed tier closure

```bash
python scripts/benchmark_compressed_candidate_tier.py
python scripts/check_compressed_tier_completion.py
```

## What It Proves

- corrected facts can stay on top instead of leaking stale facts back
- why-this / why-not is part of the runtime, not a paper promise
- the memory field has observable v10 state through `Xi(t)`
- compressed retrieval substrate exists without weakening the truth core

## Positioning

TruthKeep is a **correctness-first memory engine**.

It is strongest when:
- stale facts are expensive
- corrected truth must stay protected
- operators need to understand *why* a memory won

It is not trying to be the thinnest possible semantic cache.
