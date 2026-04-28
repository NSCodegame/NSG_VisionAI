/**
 * Feed Service — Phase 23.4
 */

import apiClient from "./api";

export interface FeedItem {
  id: string;
  name: string;
  feed_type: string;
  status: "ACTIVE" | "OFFLINE" | "DEGRADED" | "MAINTENANCE";
  zone_id?: string;
  latitude?: number;
  longitude?: number;
  location_name?: string;
  resolution?: string;
  fps?: number;
  ai_processing_enabled?: boolean;
}

export interface CreateFeedRequest {
  name: string;
  feed_type: string;
  rtsp_url: string;
  zone_id?: string;
  latitude?: number;
  longitude?: number;
  location_name?: string;
  resolution?: string;
  fps?: number;
}

export interface FeedListResponse {
  feeds: FeedItem[];
  total: number;
  skip: number;
  limit: number;
}

export const feedService = {
  async list(filters: { zone_id?: string; status?: string; feed_type?: string } = {}): Promise<FeedItem[]> {
    const { data } = await apiClient.get<FeedListResponse | FeedItem[]>("/feeds", { params: filters });
    // Backend returns { feeds: [], total, skip, limit } — extract the array
    if (data && !Array.isArray(data) && 'feeds' in data) {
      return data.feeds;
    }
    return data as FeedItem[];
  },

  async get(feedId: string): Promise<FeedItem> {
    const { data } = await apiClient.get<FeedItem>(`/feeds/${feedId}`);
    return data;
  },

  async create(feed: CreateFeedRequest): Promise<FeedItem> {
    const { data } = await apiClient.post<FeedItem>("/feeds", feed);
    return data;
  },

  async update(feedId: string, updates: Partial<CreateFeedRequest>): Promise<FeedItem> {
    const { data } = await apiClient.put<FeedItem>(`/feeds/${feedId}`, updates);
    return data;
  },

  async delete(feedId: string): Promise<void> {
    await apiClient.delete(`/feeds/${feedId}`);
  },

  async toggleAI(feedId: string): Promise<FeedItem> {
    const { data } = await apiClient.post<FeedItem>(`/feeds/${feedId}/toggle-ai`);
    return data;
  },

  async testConnection(rtspUrl: string): Promise<{ success: boolean; message: string; latency_ms?: number }> {
    const { data } = await apiClient.post("/feeds/test", { rtsp_url: rtspUrl });
    return data;
  },

  async getStats(feedId: string): Promise<Record<string, unknown>> {
    const { data } = await apiClient.get(`/feeds/${feedId}/stats`);
    return data;
  },
};
