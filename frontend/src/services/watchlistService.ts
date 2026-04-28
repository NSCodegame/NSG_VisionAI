/**
 * Watchlist Service — Phase 23.4
 */

import apiClient from "./api";

export interface WatchlistEntry {
  id: string;
  name?: string;
  alias?: string;
  threat_category: "KNOWN_TERRORIST" | "SUSPECT" | "POI" | "BANNED";
  status: "PENDING_APPROVAL" | "ACTIVE" | "DEACTIVATED";
  source_agency?: string;
  added_by?: string;
  approved_by?: string;
  created_at: string;
}

export const watchlistService = {
  async list(filters: { status?: string; category?: string } = {}): Promise<WatchlistEntry[]> {
    const { data } = await apiClient.get<WatchlistEntry[]>("/watchlist", { params: filters });
    return data;
  },

  async get(entryId: string): Promise<WatchlistEntry> {
    const { data } = await apiClient.get<WatchlistEntry>(`/watchlist/${entryId}`);
    return data;
  },

  async approve(entryId: string): Promise<WatchlistEntry> {
    const { data } = await apiClient.post<WatchlistEntry>(`/watchlist/${entryId}/approve`);
    return data;
  },

  async deactivate(entryId: string): Promise<void> {
    await apiClient.delete(`/watchlist/${entryId}`);
  },

  async getDetectionHistory(entryId: string): Promise<unknown[]> {
    const { data } = await apiClient.get(`/watchlist/${entryId}/detection-history`);
    return data;
  },
};
