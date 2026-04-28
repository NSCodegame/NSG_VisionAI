/**
 * Alert Service — Phase 23.4
 */

import apiClient from "./api";

export interface AlertFilters {
  priority?: string;
  status?: string;
  alert_type?: string;
  feed_id?: string;
  zone_id?: string;
  skip?: number;
  limit?: number;
}

export interface AlertItem {
  id: string;
  detection_event_id: string;
  alert_type: string;
  priority: "P1_CRITICAL" | "P2_HIGH" | "P3_MEDIUM" | "P4_LOW";
  status: "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED" | "FALSE_POSITIVE";
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

export interface AlertListResponse {
  alerts: AlertItem[];
  total: number;
  skip: number;
  limit: number;
}

export const alertService = {
  async list(filters: AlertFilters = {}): Promise<AlertListResponse> {
    const { data } = await apiClient.get<AlertListResponse>("/alerts", { params: filters });
    return data;
  },

  async get(alertId: string): Promise<AlertItem> {
    const { data } = await apiClient.get<AlertItem>(`/alerts/${alertId}`);
    return data;
  },

  async acknowledge(alertId: string, notes?: string): Promise<AlertItem> {
    const { data } = await apiClient.post<AlertItem>(`/alerts/${alertId}/acknowledge`, { notes });
    return data;
  },

  async resolve(alertId: string, resolutionNotes: string): Promise<AlertItem> {
    const { data } = await apiClient.post<AlertItem>(`/alerts/${alertId}/resolve`, {
      resolution_notes: resolutionNotes,
    });
    return data;
  },

  async markFalsePositive(alertId: string, reason: string): Promise<AlertItem> {
    const { data } = await apiClient.post<AlertItem>(`/alerts/${alertId}/false-positive`, {
      reason,
    });
    return data;
  },

  async bulkAcknowledge(alertIds: string[], notes?: string): Promise<{ success_count: number; failed_alert_ids: string[] }> {
    const { data } = await apiClient.post("/alerts/bulk-acknowledge", {
      alert_ids: alertIds,
      notes,
    });
    return data;
  },
};
