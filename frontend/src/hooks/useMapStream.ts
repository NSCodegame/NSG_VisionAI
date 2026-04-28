/**
 * Map Stream Hook — Phase 23.6
 *
 * Subscribes to /ws/map and delivers real-time position updates,
 * zone changes, and alert markers for the tactical map.
 */

import { useCallback, useRef, useState } from "react";
import { useWebSocket } from "./useWebSocket";

const WS_BASE = (() => {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/api/v1`;
})();

export interface MapPersonUpdate {
  person_id: string;
  track_id: string;
  feed_id: string;
  latitude?: number;
  longitude?: number;
  x?: number;
  y?: number;
  label: string;
  watchlist_match: boolean;
  timestamp: string;
}

export interface MapAlertMarker {
  alert_id: string;
  alert_type: string;
  priority: string;
  feed_id: string;
  latitude?: number;
  longitude?: number;
  triggered_at: string;
}

export interface MapZoneUpdate {
  zone_id: string;
  threat_level: string;
  updated_at: string;
}

export interface MapState {
  persons: Record<string, MapPersonUpdate>;
  alerts: MapAlertMarker[];
  zoneUpdates: MapZoneUpdate[];
}

export function useMapStream() {
  const [mapState, setMapState] = useState<MapState>({
    persons: {},
    alerts: [],
    zoneUpdates: [],
  });

  const handleMessage = useCallback((data: unknown) => {
    const msg = data as { type: string; [key: string]: unknown };

    switch (msg.type) {
      case "PERSON_POSITION_UPDATE": {
        const update = msg.update as MapPersonUpdate;
        if (update?.person_id) {
          setMapState((prev) => ({
            ...prev,
            persons: { ...prev.persons, [update.person_id]: update },
          }));
        }
        break;
      }
      case "NEW_ALERT": {
        const alert = msg.alert as MapAlertMarker;
        if (alert?.alert_id) {
          setMapState((prev) => ({
            ...prev,
            alerts: [alert, ...prev.alerts].slice(0, 100),
          }));
        }
        break;
      }
      case "ZONE_THREAT_UPDATE": {
        const zoneUpdate = msg.zone as MapZoneUpdate;
        if (zoneUpdate?.zone_id) {
          setMapState((prev) => ({
            ...prev,
            zoneUpdates: [
              zoneUpdate,
              ...prev.zoneUpdates.filter((z) => z.zone_id !== zoneUpdate.zone_id),
            ].slice(0, 50),
          }));
        }
        break;
      }
    }
  }, []);

  const { isConnected } = useWebSocket({
    url: `${WS_BASE}/ws/map`,
    onMessage: handleMessage,
  });

  return { isConnected, mapState };
}
