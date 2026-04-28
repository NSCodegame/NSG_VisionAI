/**
 * Core Type Definitions — Phase 23.3
 *
 * Centralized TypeScript interfaces for the NSG VisionAI platform.
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type Role = 'SUPER_ADMIN' | 'COMMANDER' | 'OPERATOR' | 'ANALYST';

export type FeedStatus = 'ACTIVE' | 'OFFLINE' | 'ALERT' | 'MAINTENANCE';

export type FeedType = 'FIXED_CAMERA' | 'DRONE' | 'BODY_CAM' | 'LEGACY_CCTV';

export type ZoneType = 'PERIMETER' | 'RESTRICTED' | 'PUBLIC' | 'INNER_CORDON';

export type ThreatLevel = 'GREEN' | 'AMBER' | 'RED' | 'CRITICAL';


export type AlertType = 'WATCHLIST_MATCH' | 'ZONE_BREACH' | 'WEAPON_DETECTED' | 'ABANDONED_OBJECT' | 'CROWD_DENSITY' | 'UNATTENDED_OBJECT' | 'CROWD_ANOMALY' | 'LOITERING' | 'VEHICLE_THREAT';

export type AlertPriority = "P1_CRITICAL" | "P2_HIGH" | "P3_MEDIUM" | "P4_LOW";
export type AlertStatus = "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED" | "FALSE_POSITIVE";

export type OperatorLabel = 'SUSPECT' | 'CIVILIAN' | 'FRIENDLY' | 'UNKNOWN';

export type WatchlistStatus = 'PENDING_APPROVAL' | 'ACTIVE' | 'DEACTIVATED';

export type ThreatCategory = 'KNOWN_TERRORIST' | 'SUSPECT' | 'POI' | 'BANNED';

export type ReportType = 'INCIDENT_REPORT' | 'PERSON_REPORT' | 'ZONE_ACTIVITY' | 'OPERATION_SUMMARY' | 'FORENSIC_TIMELINE';


export type Classification = 'RESTRICTED' | 'CONFIDENTIAL' | 'SECRET' | 'TOP_SECRET';

// ---------------------------------------------------------------------------
// Models
// ---------------------------------------------------------------------------

export interface User {
  id: string;
  service_number: string;
  full_name: string;
  role: Role;
  unit: string;
  is_active: boolean;
}

export interface VideoFeed {
  id: string;
  name: string;
  feed_type: FeedType;
  status: FeedStatus;
  rtsp_url?: string;
  zone_id?: string;
  latitude?: number;
  longitude?: number;
  location_name?: string;
  resolution?: string;
  fps?: number;
  ai_processing_enabled?: boolean;
}

export interface SecurityZone {
  id: string;
  name: string;
  zone_type: ZoneType;
  threat_level: ThreatLevel;
  polygon_coordinates: Array<[number, number]>;
  description?: string;
}

export interface Alert {
  id: string;
  detection_event_id: string;
  alert_type: AlertType | string;
  priority: AlertPriority;
  status: AlertStatus;
  feed_id?: string;
  zone_id?: string;
  confidence_score?: number;
  triggered_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  acknowledged_by?: string;
  resolution_notes?: string;
  false_positive_reason?: string;
  occurrence_count: number;
}

export interface DetectionEvent {
  id: string;
  feed_id: string;
  detection_type: string;
  confidence_score: number;
  bounding_box: { x: number; y: number; w: number; h: number };
  object_class?: string;
  person_id?: string;
  frame_timestamp: string;
  frame_snapshot_path?: string;
}

export interface TrackedPerson {
  id: string;
  track_id: string;
  label: OperatorLabel;
  watchlist_match_id?: string;
  last_seen_at?: string;
  trajectory?: Array<{
    timestamp: string;
    feed_id: string;
    x: number;
    y: number;
  }>;
}

export interface WatchlistEntry {
  id: string;
  name?: string;
  alias?: string;
  threat_category: ThreatCategory;
  status: WatchlistStatus;
  source_agency?: string;
  added_by?: string;
  approved_by?: string;
  created_at: string;
}

export interface Report {
  id: string;
  title: string;
  report_type: ReportType | string;
  classification: Classification;
  status: "PENDING" | "COMPLETED" | "FAILED";
  generated_at?: string;
  file_path?: string;
}

// ---------------------------------------------------------------------------
// API response wrappers
// ---------------------------------------------------------------------------

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export const TACTICAL_TYPES_VERSION = "23.3.2";
