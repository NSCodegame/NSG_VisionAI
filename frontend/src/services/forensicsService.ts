/**
 * Forensics Service — Phase 23.4
 */

import apiClient from "./api";

export interface ForensicJob {
  job_id: string;
  job_type: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  result_count?: number;
  results?: unknown[];
  created_at?: string;
  completed_at?: string;
  error_message?: string;
}

export const forensicsService = {
  async faceSearch(params: Record<string, unknown>): Promise<{ job_id: string; status: string }> {
    const { data } = await apiClient.post("/forensics/face-search", params);
    return data;
  },

  async objectSearch(params: Record<string, unknown>): Promise<{ job_id: string; status: string }> {
    const { data } = await apiClient.post("/forensics/object-search", params);
    return data;
  },

  async zoneSearch(params: Record<string, unknown>): Promise<{ job_id: string; status: string }> {
    const { data } = await apiClient.post("/forensics/zone-search", params);
    return data;
  },

  async timelineSearch(params: Record<string, unknown>): Promise<{ job_id: string; status: string }> {
    const { data } = await apiClient.post("/forensics/timeline-search", params);
    return data;
  },

  async getJob(jobId: string): Promise<ForensicJob> {
    const { data } = await apiClient.get<ForensicJob>(`/forensics/jobs/${jobId}`);
    return data;
  },

  async pollJob(jobId: string, intervalMs = 2000, maxAttempts = 30): Promise<ForensicJob> {
    for (let i = 0; i < maxAttempts; i++) {
      const job = await this.getJob(jobId);
      if (job.status === "COMPLETED" || job.status === "FAILED") {
        return job;
      }
      await new Promise((r) => setTimeout(r, intervalMs));
    }
    throw new Error(`Job ${jobId} did not complete within timeout`);
  },
};
