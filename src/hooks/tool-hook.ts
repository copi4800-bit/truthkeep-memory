/**
 * Tool call hooks for Chimpanzee learning.
 */

import type { AegisMemoryManager } from "../aegis-manager.js";
import { recordToolSuccess, recordToolFailure } from "../cognitive/chimpanzee.js";

export function createToolHooks(getManager: () => AegisMemoryManager | null) {
  return {
    async afterToolCall(event: {
      toolName: string;
      params: unknown;
      result: unknown;
      success: boolean;
      error?: string;
      sessionKey?: string;
    }): Promise<void> {
      const manager = getManager();
      if (!manager || !manager.layerEnabled("chimpanzee")) return;

      const db = manager.getDb();

      if (event.success) {
        recordToolSuccess(db, event.toolName, event.params, event.result, event.sessionKey);
      } else {
        recordToolFailure(db, event.toolName, event.params, event.error ?? "unknown error", event.sessionKey);
      }
    },
  };
}
