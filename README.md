# Memory Aegis v8 (Pure Python)

Local-first, human-centric memory engine for OpenClaw and MCP-based agents.

## Product Overview

Aegis v8 is a complete evolution of the memory engine, now running on a pure Python-centric architecture. It is designed for agents that need memory to stay useful, scoped, and trustworthy over time, while maintaining a deeply personalized user experience.

### Key v8 Enhancements:
- **Personalized Identity:** Assistants address you by your preferred honorific (Sếp, Anh, Chị...).
- **Human-Centric Conflict Resolution:** Interactive dialogue prompts to resolve contradictions between memories using simple 1/2 choices.
- **Explainable Trust:** Every memory recalled comes with a clear "Human Reason" explaining why it was selected.
- **Actionable Health Reports:** A "Memory Doctor" surface that provides polite, supportive maintenance advice.
- **Deterministic Correction:** Smart intent detection ensuring old facts are superseded seamlessly.

## Why Aegis v8?

Aegis v8 isn't just a database; it's a "Cognitive Beast" system that mimics human memory patterns:
- **Crystallization:** Memories you repeat become stronger and more stable.
- **Decay:** Stale, unused information fades away to reduce noise.
- **Self-Healing:** Automatically repairs broken links and identifies contradictions.

## Installation

### Requirements:
- Python 3.10+
- SQLite (FTS5 enabled)

### Quick Start:
1. Clone the repository.
2. Run `pip install -r requirements.txt`.
3. Integrated directly into OpenClaw via the Python tool adapter.

## Architecture

The v8 runtime is organized into six core modules:
- `memory`: Ingest and smart intent detection.
- `retrieval`: Scoped search with semantic expansion.
- `hygiene`: Decay, crystallization, and maintenance.
- `profiles`: Identity and personalized preferences.
- `storage`: High-performance SQLite persistence.
- `conflict`: Interactive contradiction management.

---
Built for reliability, designed for trust. Aegis v8 — The brain of your agent.
