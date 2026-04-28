/**
 * Detection Stream Hook — Phase 23.6
 *
 * Subscribes to /ws/detections/{feed_id} and delivers detection events
 * for real-time AI overlay rendering on the video canvas.
 */

import { useCallback, useRef } from "react";
import { useWebSocket } from "./useWebSocket";

const WS_BASE = (() => {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/api/v1`;
})();

export interface DetectionOverlay {
  detection_event_id: string;
  detection_type: string;
  object_class?: string;
  confidence_score: number;
  bounding_box: { x: number; y: number; w: number; h: number };
  threat_level?: string;
  person_id?: string;
  watchlist_match_id?: string;
  frame_timestamp: string;
}

interface UseDetectionStreamOptions {
  feedId: string;
  onDetection?: (detection: DetectionOverlay) => void;
  enabled?: boolean;
}

export function useDetectionStream({
  feedId,
  onDetection,
  enabled = true,
}: UseDetectionStreamOptions) {
  const latestDetections = useRef<DetectionOverlay[]>([]);

  const handleMessage = useCallback(
    (data: unknown) => {
      const msg = data as { type: string; detection?: DetectionOverlay };
      if (msg.type === "NEW_DETECTION" && msg.detection) {
        // Keep last 20 detections per feed for overlay
        latestDetections.current = [
          msg.detection,
          ...latestDetections.current.slice(0, 19),
        ];
        onDetection?.(msg.detection);
      }
    },
    [onDetection]
  );

  const { isConnected, retryCount } = useWebSocket({
    url: enabled ? `${WS_BASE}/ws/detections/${feedId}` : "",
    onMessage: handleMessage,
    maxRetries: 3,
  });

  return {
    isConnected,
    retryCount,
    getLatestDetections: () => latestDetections.current,
  };
}
