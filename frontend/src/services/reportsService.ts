/**
 * Reports Service — Phase 23.4
 */

import apiClient from "./api";

export interface Report {
  id: string;
  title: string;
  report_type: string;
  classification: "RESTRICTED" | "CONFIDENTIAL" | "SECRET";
  status: "PENDING" | "COMPLETED" | "FAILED";
  generated_at?: string;
  file_path?: string;
  detection_event_ids?: string[];
}

export interface CreateReportRequest {
  title: string;
  report_type: string;
  classification?: string;
  summary?: string;
  analyst_notes?: string;
  detection_event_ids?: string[];
}

export const reportsService = {
  async list(reportType?: string): Promise<Report[]> {
    const { data } = await apiClient.get<Report[]>("/reports", {
      params: { report_type: reportType },
    });
    return data;
  },

  async get(reportId: string): Promise<Report> {
    const { data } = await apiClient.get<Report>(`/reports/${reportId}`);
    return data;
  },

  async create(req: CreateReportRequest): Promise<Report> {
    const { data } = await apiClient.post<Report>("/reports", null, {
      params: {
        title: req.title,
        report_type: req.report_type,
        classification: req.classification ?? "RESTRICTED",
        summary: req.summary,
        analyst_notes: req.analyst_notes,
      },
    });
    return data;
  },

  async getDownloadUrl(reportId: string): Promise<{ download_url: string; expires_in_seconds: number }> {
    const { data } = await apiClient.get(`/reports/${reportId}/download`);
    return data;
  },
};
