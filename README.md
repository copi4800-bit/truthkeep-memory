# Memory Aegis v3 (Animal Upgrade)

**Version:** 3.1.0  
**Framework:** OpenClaw Plugin (Memory Slot)  
**Status:** Stable - Production Ready

Memory Aegis v3 is a local-first, graph-activation cognitive memory engine for OpenClaw. It provides a tiered memory structure using **10 specialized animal layers** to protect and evolve your AI's knowledge.

## 🐾 The 10 Cognitive Layers

### Core Processing
1.  **Elephant:** Long-term invariant memory. Essential facts that never change.
2.  **Orca:** Semantic graph activation. Connects the dots between different topics.
3.  **Dolphin:** Active working memory. Maintains context during your current session.
4.  **Octopus:** Context splitting. Manages complex subgraphs and partitions.
5.  **Chimpanzee:** Tool craft & Interaction. Remembers how to use tools and fixes errors.
6.  **Sea Lion:** Logical inference. Inherits concepts and recognizes temporal patterns.
7.  **Salmon:** Data Fingerprinting. De-duplicates information to keep DB clean.
8.  **Nutcracker:** Micro-chunking. Breaks down large data and manages TTL hygiene.

### Survival & Resilience
9.  **Tardigrade (Water Bear):** The Survivor. Handles high-durability snapshots and exports.
10. **Planarian:** The Immortal. Handles deep restoration and memory rebuilding.

## 🧹 The "Four Great Purges" (V3.1.0 Updates)
- 🐝 **Honeybee (Measurement):** Real-time telemetry dashboard (`memory_stats`).
- 🐍 **Viper (Hygiene):** Automatic backup rotation and interaction state caps.
- 🐜 **Leafcutter Ant (Cold Storage):** Archives events > 90 days into compressed Gzip logs.
- 🦎 **Axolotl (Regeneration):** Regenerates derived knowledge links from crystallized facts.

## 🛠 Available Tools
- `memory_stats`: View Honeybee telemetry.
- `memory_search`: Search deep memories using FTS5.
- `memory_store`: Persist specific facts.
- `memory_rebuild`: Manually trigger Axolotl regeneration.
- `memory_backup_upload`: Create snapshots (Tardigrade).
- `memory_backup_download`: Restore memory (Planarian).

## 🚀 Installation
Place this folder in your `~/.openclaw/extensions/` directory and enable it in `openclaw.json`.

---
*Developed by Bim Bim & The OpenClaw Team.*
