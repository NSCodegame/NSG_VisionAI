/**
 * Admin Service — Phase 23.4
 */

import apiClient from "./api";

export interface MLModel {
  id: string;
  name: string;
  version: string;
  model_type: string;
  framework: string;
  weights_path: string;
  config_path?: string;
  accuracy_metrics?: Record<string, unknown>;
  is_active: boolean;
  deployed_at?: string;
  deployed_by?: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  user_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  ip_address?: string;
  user_agent?: string;
  details?: Record<string, unknown>;
  timestamp: string;
}

export const adminService = {
  // ML Models
  async listModels(modelType?: string): Promise<{ models: MLModel[]; total: number }> {
    const { data } = await apiClient.get("/admin/models", {
      params: { model_type: modelType },
    });
    return data;
  },

  async deployModel(modelId: string): Promise<MLModel> {
    const { data } = await apiClient.post<MLModel>(`/admin/models/${modelId}/deploy`, {
      confirmed: true,
    });
    return data;
  },

  async rollbackModel(modelId: string): Promise<MLModel> {
    const { data } = await apiClient.post<MLModel>(`/admin/models/${modelId}/rollback`);
    return data;
  },

  async validateModel(modelId: string): Promise<Record<string, unknown>> {
    const { data } = await apiClient.post(`/admin/models/${modelId}/validate`);
    return data;
  },

  // System Health
  async getSystemHealth(): Promise<Record<string, unknown>> {
    const { data } = await apiClient.get("/admin/health/system");
    return data;
  },

  async getWorkerHealth(): Promise<unknown[]> {
    const { data } = await apiClient.get("/admin/health/workers");
    return data;
  },

  async restartWorker(workerId: string): Promise<{ message: string }> {
    const { data } = await apiClient.post(`/admin/workers/${workerId}/restart`);
    return data;
  },

  // Audit Logs
  async listAuditLogs(filters: {
    user_id?: string;
    action?: string;
    resource_type?: string;
    skip?: number;
    limit?: number;
  } = {}): Promise<{ logs: AuditLog[]; total: number }> {
    const { data } = await apiClient.get("/admin/audit", { params: filters });
    return data;
  },

  async exportAuditLogs(filters: {
    user_id?: string;
    action?: string;
    resource_type?: string;
  } = {}): Promise<Blob> {
    const response = await apiClient.get("/admin/audit/export", {
      params: filters,
      responseType: "blob",
    });
    return response.data;
  },
};
