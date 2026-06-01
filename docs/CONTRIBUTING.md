# Contributing to TruthKeep Memory

Thank you for your interest in contributing to TruthKeep Memory! This guide will help you get set up and understand our development practices.

## Development Setup

### Prerequisites

- **Python 3.12+** (required)
- **Git** for version control
- No external dependencies required — TruthKeep is pure Python

### Installation

```bash
# Clone the repository
git clone https://github.com/truthkeep/truthkeep-memory.git
cd truthkeep-memory

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install in development mode
pip install -e .

# Verify installation
truthkeep-check
truthkeep field-snapshot
```

### Running Tests

```bash
# Run the full test suite
python -m pytest tests -x --tb=short

# Run with verbose output
python -m pytest tests -v

# Run a specific test file
python -m pytest tests/test_ancient_math.py -v

# Run the proof flow
python scripts/prove_it.py

# Run the full gauntlet (stress tests)
python scripts/aegis_gauntlet.py
```

The test suite should show **185 tests passing** on a clean checkout.

## Code Standards

### Type Hints Required

All function signatures must include type hints:

```python
# ✅ Good
def compute_gradient(self, error: float, link_weight: float, depth: int) -> float:
    ...

# ❌ Bad
def compute_gradient(self, error, link_weight, depth):
    ...
```

### Docstrings Required

All public classes and functions must have docstrings explaining what they do:

```python
# ✅ Good
def posterior(prior: float, likelihood: float, evidence_marginal: float = 0.0) -> float:
    """Compute Bayesian posterior probability.

    P(A|B) = P(B|A) × P(A) / P(B)

    Args:
        prior: P(A) — prior belief
        likelihood: P(B|A) — probability of evidence given hypothesis
        evidence_marginal: P(B) — total probability of evidence

    Returns:
        Posterior probability P(A|B), clamped to [0, 1]
    """
```

### Named Constants for Magic Numbers

```python
# ✅ Good
DISTORTION_THRESHOLD = 0.3
DEFAULT_LEARNING_RATE = 0.15
MAX_PROPAGATION_DEPTH = 2

def compute(self, value: float) -> float:
    return value * self.DISTORTION_THRESHOLD

# ❌ Bad
def compute(self, value: float) -> float:
    return value * 0.3
```

### Pure Python Requirement

TruthKeep must remain **pure Python** with no heavy external dependencies.

The following are **not allowed**:
- `numpy` / `scipy`
- `pycryptodome` / `cryptography`
- `torch` / `tensorflow`
- Any library that requires native compilation

This is a deliberate design choice to support deployment on:
- ESP32 and other embedded devices
- Minimal Python environments
- Systems without C compilers

If you need mathematical operations, implement them using Python's `math` module, `hashlib`, and `struct`.

## Pull Request Checklist

Before submitting a pull request, verify:

- [ ] All tests pass: `python -m pytest tests -x --tb=short`
- [ ] Type hints added to all new function signatures
- [ ] Docstrings written for all new public classes and functions
- [ ] No magic numbers — all constants are named
- [ ] No new external dependencies added
- [ ] Existing tests still pass (no regressions)
- [ ] New features include corresponding tests
- [ ] Code follows existing file organization patterns

## Architecture Overview

Before contributing, familiarize yourself with the project structure:

- **[docs/MATH_ARCHITECTURE.md](docs/MATH_ARCHITECTURE.md)** — The mathematical foundation: 13 engines across 4 phases
- **[aegis_py/ARCHITECTURE_BEAST_MAP.md](aegis_py/ARCHITECTURE_BEAST_MAP.md)** — Internal "23 beasts" architecture mapping
- **[SECURITY.md](SECURITY.md)** — Security model and known limitations

### Key Directories

| Directory | Purpose |
|-----------|--------|
| `truthkeep/` | Public package, CLI wrappers, TruthKeep-first entry points |
| `aegis_py/` | Internal runtime: storage, retrieval, governance, MCP |
| `aegis_py/storage/` | Mathematical engines, schema, data management |
| `aegis_py/security/` | Cryptography, key management, privacy |
| `aegis_py/retrieval/` | Search, ranking, compressed prefilter |
| `aegis_py/hygiene/` | Decay, consolidation, lifecycle management |
| `aegis_py/v10/` | v10 dynamics, state machine, field snapshots |
| `tests/` | Regression, validation, and stress tests |
| `scripts/` | Demos, proofs, benchmarks, gauntlets |
| `docs/` | Public documentation |

## Questions?

If you're unsure about something, open an issue for discussion before writing code. We'd rather talk through an approach first than review a large PR that may not fit the architecture.
