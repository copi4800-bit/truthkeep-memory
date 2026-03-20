# Memory Aegis v3 (Animal Upgrade)

**Version:** 3.1.0  
**Framework:** OpenClaw Plugin (Memory Slot)  
**Status:** Stable - Production Ready

Memory Aegis v3 is a local-first, graph-activation cognitive memory engine for OpenClaw. It provides a tiered memory structure using animal metaphors to represent different cognitive functions.

## 🐾 8 Cognitive Layers
- **Elephant:** Long-term invariant memory.
- **Orca:** Semantic graph activation and relational indexing.
- **Dolphin:** Active working memory and interaction context.
- **Octopus:** Context splitting and subgraph partitioning.
- **Chimpanzee:** Tool craft, correction traces, and interaction state.
- **Sea Lion:** Inference and concept inheritance patterns.
- **Salmon:** Fingerprinting, de-duplication (Dedup), and drift detection.
- **Nutcracker:** Micro-chunking and LANDMARK indexing with TTL hygiene.

## 🧹 The "Four Great Purges" (V3.1.0 Updates)
The system now includes an automated maintenance ecosystem to keep your database healthy and fast:
- 🐝 **Honeybee (Measurement):** Real-time telemetry dashboard.
- 🐍 **Viper (Hygiene):** Automatic backup rotation and interaction state caps.
- 🐜 **Leafcutter Ant (Cold Storage):** Archives events > 90 days into compressed Gzip logs.
- 🦎 **Axolotl (Regeneration):** Regenerates derived knowledge links from crystallized facts.

## 🛠 Available Tools
- `memory_stats`: View Honeybee telemetry.
- `memory_search`: Search deep memories using FTS5.
- `memory_store`: Persist specific facts.
- `memory_rebuild`: Manually trigger Axolotl regeneration.
- `memory_backup_upload`: Create snapshots for backup.
- `memory_backup_download`: Restore memory from snapshots.

## 🚀 Installation
Place this folder in your `~/.openclaw/extensions/` directory and enable it in `openclaw.json`.

---
*Developed by Bim Bim & The OpenClaw Team.*
