/**
 * Message hooks for correction detection and interaction state tracking.
 */

import type { AegisMemoryManager } from "../aegis-manager.js";
import {
  detectCorrection,
  recordCorrection,
  updateInteractionState,
} from "../cognitive/chimpanzee.js";

export function createMessageHooks(getManager: () => AegisMemoryManager | null) {
  return {
    async onMessageReceived(event: {
      message: string;
      previousAssistantMessage?: string;
      sessionKey?: string;
    }): Promise<void> {
      const manager = getManager();
      if (!manager || !manager.layerEnabled("chimpanzee")) return;

      const db = manager.getDb();
      const sessionKey = event.sessionKey ?? "default";

      // Detect correction patterns
      const detection = detectCorrection(event.message, event.previousAssistantMessage);

      if (detection.isCorrection && event.previousAssistantMessage) {
        recordCorrection(
          db,
          event.message,
          event.previousAssistantMessage,
          event.message,
          {
            correctionType: detection.correctionType,
            confidence: detection.intensity,
          },
        );
      }

      // Update interaction state signals
      updateInteractionState(db, sessionKey, {
        correctionPressure: detection.isCorrection ? detection.intensity : 0,
        frustrationIndex: detection.intensity > 0.6 ? detection.intensity : 0,
        brevityPreference: event.message.length < 20 ? 0.8 : 0.3,
      });
    },
  };
}
