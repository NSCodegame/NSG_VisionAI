/**
 * Auth Hook — Phase 23.6
 */

import { useCallback } from "react";
import { useAuthStore } from "../stores";
import { authService, type LoginRequest } from "../services/authService";

export function useAuth() {
  const { user, token, setAuth, logout: clearAuth } = useAuthStore();

  const login = useCallback(
    async (credentials: LoginRequest) => {
      const response = await authService.login(credentials);
      setAuth(
        {
          id: response.user.id,
          service_number: response.user.service_number,
          full_name: response.user.full_name,
          role: response.user.role as import("../types").Role,
          unit: response.user.unit,
          is_active: true,
        },
        response.access_token
      );
      return response;
    },
    [setAuth]
  );

  const logout = useCallback(async () => {
    await authService.logout();
    clearAuth();
  }, [clearAuth]);

  return {
    user,
    token,
    isAuthenticated: !!token,
    login,
    logout,
  };
}
