/**
 * Memory Aegis v3 — OpenClaw Plugin Entry Point.
 *
 * Registers Aegis v3 as a memory backend plugin.
 */

export { AegisMemoryManager, closeAllManagers } from "./aegis-manager.js";
export type { AegisConfig, CognitiveLayers, MemoryNode, MemoryEdge } from "./core/models.js";
export { DEFAULT_AEGIS_CONFIG } from "./core/models.js";

// Hooks
export { createSessionHooks } from "./hooks/session-hook.js";
export { createToolHooks } from "./hooks/tool-hook.js";
export { createMessageHooks } from "./hooks/message-hook.js";

// Cognitive layers (advanced usage)
export { microChunk, extractLandmarks } from "./cognitive/nutcracker.js";
export { resolveEntities, rebuildCoOccurrenceEdges, prewarm, consolidateSession } from "./cognitive/dolphin.js";
export { detectCorrection, computeBehavioralModifiers } from "./cognitive/chimpanzee.js";
export { upsertConcept, addInheritance, resolveInheritedRules, transitiveInference } from "./cognitive/sea-lion.js";
export { createPartition, subgraphSearch, autoPartition, upsertContextTexture, getContextTexture } from "./cognitive/octopus.js";
export { checkAntiRegression, findElephantOverrides, storeElephantMemory } from "./cognitive/elephant.js";
export { dedupByFingerprint, findDuplicateCluster } from "./cognitive/salmon.js";

// Disaster Recovery
export { createSnapshot, exportLogicalData } from "./cognitive/tardigrade.js";
export { restoreFromSnapshot, rebuildIndexes } from "./cognitive/planarian.js";
export { BACKUP_SYNC_TOOLS } from "./cognitive/chimpanzee-tools.js";
