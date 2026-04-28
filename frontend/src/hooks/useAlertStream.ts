/**
 * Alert Stream Hook — Phase 23.6
 *
 * Subscribes to /ws/alerts WebSocket and updates the alert store.
 */

import { useCallback } from "react";
import { useWebSocket } from "./useWebSocket";
import { useAlertStore } from "../stores";
import type { Alert } from "../types";

// Use relative WebSocket URL — Vite proxy forwards /ws to backend
const WS_BASE = (() => {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/api/v1`;
})();

export function useAlertStream() {
  const addAlert = useAlertStore((s) => s.addAlert);

  const handleMessage = useCallback(
    (data: unknown) => {
      const msg = data as { type: string; alert?: Alert };
      if (msg.type === "NEW_ALERT" && msg.alert) {
        addAlert(msg.alert);

        // Browser notification for P1/P2
        if (
          ["P1_CRITICAL", "P2_HIGH"].includes(msg.alert.priority) &&
          Notification.permission === "granted"
        ) {
          new Notification(`${msg.alert.priority} ALERT`, {
            body: `${msg.alert.type} — Feed ${msg.alert.feed_id}`,
            icon: "/favicon.svg",
          });
        }
      }
    },
    [addAlert]
  );

  return useWebSocket({
    url: `${WS_BASE}/ws/alerts`,
    onMessage: handleMessage,
  });
}
