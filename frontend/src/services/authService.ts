/**
 * Auth Service — Phase 23.4
 */

import apiClient from "./api";

export interface LoginRequest {
  service_number: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: string;
    service_number: string;
    full_name: string;
    role: string;
    unit: string;
  };
}

export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const { data } = await apiClient.post<LoginResponse>("/auth/login", credentials);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    return data;
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post("/auth/logout");
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
  },

  async refreshToken(): Promise<string> {
    const refreshToken = localStorage.getItem("refresh_token");
    const { data } = await apiClient.post<{ access_token: string }>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    localStorage.setItem("access_token", data.access_token);
    return data.access_token;
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem("access_token");
  },
};
