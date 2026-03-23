# Memory Aegis v4

> Local-first cognitive memory engine for OpenClaw. Smart recall, automatic maintenance, conflict detection, and guided setup — no cloud required.

**Version:** 4.0.0 | **Status:** Stable

---

## What it does

Aegis gives your AI agent a persistent, self-maintaining long-term memory:

- **Remembers** facts, procedures, preferences, and decisions across sessions
- **Retrieves** the most relevant context for any query (FTS5 + graph spreading activation)
- **Cleans itself** — expires stale memories, resolves conflicts, archives old data
- **Protects** core persona and safety rules from being diluted by task overflow
- **Works offline** — pure SQLite, no embeddings, no external API

---

## Quick Start

### 1. Install
```bash
npm install
npm run build
```

### 2. Place in OpenClaw
```bash
cp -r . ~/.openclaw/extensions/memory-aegis-v4
```

### 3. Run guided setup
Use the `/memory-setup` skill or call `memory_setup` tool from your agent.

---

## Presets

Choose a preset when initializing:

| Preset | Layers | Best for |
|--------|--------|----------|
| `minimal` | Storage + dedup only | Fast, low overhead |
| `balanced` | + Graph + Maintenance | Most users (default) |
| `local-safe` | + Archive + Health | Privacy-sensitive use |
| `full` | All layers | Maximum capability |

---

## Tools

### Basic (everyday use)
| Tool | What it does |
|------|-------------|
| `memory_search` | Find relevant memories for a query |
| `memory_store` | Save a new memory |
| `memory_profile` | See what Aegis remembers about you |
| `memory_setup` | First-time guided onboarding |
| `memory_stats` | Memory count, growth, health summary |

### Advanced (power users)
| Tool | What it does |
|------|-------------|
| `memory_doctor` | Run full health diagnostics |
| `memory_clean` | Expire TTL nodes, run maintenance |
| `memory_backup` | Snapshot or JSONL export |
| `memory_restore` | Restore from backup |
| `memory_taxonomy` | View/fix memory label distribution |
| `memory_debug` | Trace retrieval decisions, inspect nodes |
| `memory_get` | Read a specific memory citation |

---

## Skills (slash commands)

| Skill | Shortcut | What it does |
|-------|----------|-------------|
| remember | `/remember` | Store information into long-term memory |
| recall | `/recall` | Search memory for relevant context |
| memory-status | `/memory-status` | Health + stats overview |
| memory-clean | `/memory-clean` | Run maintenance |
| memory-backup | `/memory-backup` | Create a snapshot |
| memory-profile | `/memory-profile` | Show your memory profile |
| memory-setup | `/memory-setup` | Guided first-time setup |

---

## Cognitive Layers

Aegis uses specialized layers — each responsible for one aspect of memory:

| Layer | Role |
|-------|------|
| **Elephant** | Long-term invariant facts and safety rules |
| **Orca** | Graph spreading activation — connects related topics |
| **Dolphin** | Active session working memory |
| **Octopus** | Context partitioning and subgraph management |
| **Sea Lion** | Logical inference and concept inheritance |
| **Salmon** | Deduplication via content fingerprinting |
| **Nutcracker** | Micro-chunking and TTL hygiene |
| **Dragonfly** | Hybrid FTS rescue for low-hit queries |
| **Bowerbird** | Taxonomy classifier — labels unclassified memories |
| **Meerkat** | Contradiction sentinel — finds conflicting facts |
| **Zebra Finch** | Memory consolidator — supersedes outdated nodes |
| **Eagle** | Health monitoring and telemetry reports |
| **Scrub Jay** | Episodic grouping of session memory |
| **Weaver Bird** | Procedural knowledge extractor |
| **Chameleon** | Context budget allocation for prompt assembly |
| **Tardigrade** | Durable snapshots and exports |
| **Planarian** | Memory restoration and FTS rebuild |
| **Viper** | Backup rotation (daily/weekly/monthly) |
| **Leafcutter** | Cold archive for events older than 90 days |
| **Axolotl** | Derived knowledge regeneration |
| **Chimpanzee** | Tool trace capture for correction learning |

---

## Architecture

- **Storage:** SQLite (WAL mode) + FTS5 full-text index
- **Graph:** Bidirectional weighted edges with Hebbian reinforcement
- **Retrieval:** FTS5 seed → Orca spreading activation → reranker → Chameleon budget
- **Maintenance:** Automated decay, TTL, conflict detection, near-duplicate merge
- **Vietnamese support:** Tone-normalized synonym bridging (no LLM required)

---

## Requirements

- Node.js 18+
- OpenClaw host application
- No GPU, no cloud, no embeddings required

---

*Memory Aegis v4 — built for reliability, designed to be forgotten about.*
