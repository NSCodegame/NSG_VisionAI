/**
 * Analytics Service — Phase 23.4
 */

import apiClient from "./api";

export interface AnalyticsSummary {
  period: { from: string; to: string };
  total_alerts: number;
  alerts_by_priority: Record<string, number>;
  watchlist_matches: number;
  zone_breaches: number;
  persons_tracked: number;
  false_positive_rate: number;
  false_positives: number;
}

export interface TimelineBucket {
  timestamp: string;
  P1_CRITICAL: number;
  P2_HIGH: number;
  P3_MEDIUM: number;
  P4_LOW: number;
}

export interface AlertDistributionItem {
  alert_type: string;
  count: number;
  percentage: number;
}

export interface ZoneHeatmapItem {
  zone_id: string;
  hour: number;
  alert_count: number;
}

export interface MLPerformance {
  period_days: number;
  total_detections: number;
  avg_confidence: number;
  min_confidence: number;
  max_confidence: number;
  by_detection_type: Array<{
    detection_type: string;
    count: number;
    avg_confidence: number;
  }>;
}

export const analyticsService = {
  async getSummary(fromDt?: string, toDt?: string): Promise<AnalyticsSummary> {
    const { data } = await apiClient.get<AnalyticsSummary>("/analytics/summary", {
      params: { from_dt: fromDt, to_dt: toDt },
    });
    return data;
  },

  async getAlertsTimeline(
    fromDt?: string,
    toDt?: string,
    granularity: "hour" | "day" = "hour"
  ): Promise<TimelineBucket[]> {
    const { data } = await apiClient.get<TimelineBucket[]>("/analytics/alerts", {
      params: { from_dt: fromDt, to_dt: toDt, granularity },
    });
    return data;
  },

  async getAlertDistribution(fromDt?: string, toDt?: string): Promise<AlertDistributionItem[]> {
    const { data } = await apiClient.get<AlertDistributionItem[]>("/analytics/distribution", {
      params: { from_dt: fromDt, to_dt: toDt },
    });
    return data;
  },

  async getZoneHeatmap(fromDt?: string, toDt?: string): Promise<ZoneHeatmapItem[]> {
    const { data } = await apiClient.get<ZoneHeatmapItem[]>("/analytics/zones", {
      params: { from_dt: fromDt, to_dt: toDt },
    });
    return data;
  },

  async getMLPerformance(): Promise<MLPerformance> {
    const { data } = await apiClient.get<MLPerformance>("/analytics/performance");
    return data;
  },

  async getTopFeeds(fromDt?: string, toDt?: string, limit = 10): Promise<Array<{ feed_id: string; alert_count: number }>> {
    const { data } = await apiClient.get("/analytics/top-feeds", {
      params: { from_dt: fromDt, to_dt: toDt, limit },
    });
    return data;
  },
};
