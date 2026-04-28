/**
 * Zone Service — Phase 23.4
 */

import apiClient from "./api";

export interface SecurityZone {
  id: string;
  name: string;
  zone_type: "PERIMETER" | "RESTRICTED" | "PUBLIC" | "INNER_CORDON";
  threat_level: "GREEN" | "AMBER" | "RED" | "CRITICAL";
  polygon_coordinates: Array<[number, number]>;
  description?: string;
  camera_count?: number;
  active_alert_count?: number;
}

export interface CreateZoneRequest {
  name: string;
  zone_type: string;
  polygon_coordinates: Array<[number, number]>;
  description?: string;
}

export const zoneService = {
  async list(): Promise<SecurityZone[]> {
    const { data } = await apiClient.get<SecurityZone[]>("/zones");
    return data;
  },

  async get(zoneId: string): Promise<SecurityZone> {
    const { data } = await apiClient.get<SecurityZone>(`/zones/${zoneId}`);
    return data;
  },

  async create(zone: CreateZoneRequest): Promise<SecurityZone> {
    const { data } = await apiClient.post<SecurityZone>("/zones", zone);
    return data;
  },

  async update(zoneId: string, updates: Partial<CreateZoneRequest>): Promise<SecurityZone> {
    const { data } = await apiClient.put<SecurityZone>(`/zones/${zoneId}`, updates);
    return data;
  },

  async updateThreatLevel(
    zoneId: string,
    threatLevel: string
  ): Promise<SecurityZone> {
    const { data } = await apiClient.put<SecurityZone>(`/zones/${zoneId}/threat-level`, {
      threat_level: threatLevel,
    });
    return data;
  },

  async delete(zoneId: string): Promise<void> {
    await apiClient.delete(`/zones/${zoneId}`);
  },
};
