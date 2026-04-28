/**
 * Login Page — NSG VisionAI
 *
 * Full-screen dark tactical login with NSG branding,
 * service number validation, failed attempt tracking,
 * account lockout display, and Sign Up navigation.
 */

import { useState } from "react";
import { Shield, Eye, EyeOff, AlertTriangle, Lock } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

interface LoginPageProps {
  onLoginSuccess: () => void;
  onNavigateToRegister: () => void;
}

export function LoginPage({ onLoginSuccess, onNavigateToRegister }: LoginPageProps) {
  const { login } = useAuth();
  const [serviceNumber, setServiceNumber] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [attemptCount, setAttemptCount] = useState(0);
  const [isLocked, setIsLocked] = useState(false);
  const [lockoutMinutes, setLockoutMinutes] = useState(0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login({ service_number: serviceNumber, password });
      onLoginSuccess();
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: { status: number; data?: { detail?: string; lockout_minutes?: number; message?: string } };
      };
      const status = axiosErr.response?.status;
      const detail = axiosErr.response?.data?.detail;
      const message = typeof detail === "object"
        ? (detail as { message?: string })?.message
        : detail;

      if (status === 423) {
        setIsLocked(true);
        setLockoutMinutes(axiosErr.response?.data?.lockout_minutes ?? 30);
        setError("Account locked due to too many failed attempts.");
      } else if (status === 401) {
        const newCount = attemptCount + 1;
        setAttemptCount(newCount);
        setError(
          newCount >= 4
            ? `Authentication failed. 1 attempt remaining before lockout.`
            : `Authentication failed. Please try again. (${newCount}/5)`
        );
      } else {
        setError(message ?? "Authentication failed. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: "#05070a" }}
    >
      {/* Grid background */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0,242,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,242,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: "40px 40px",
        }}
      />

      {/* Radial glow */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse at 50% 0%, rgba(0,128,255,0.08) 0%, transparent 60%)",
        }}
      />

      <div className="relative w-full max-w-[420px]">
        {/* Warning banner */}
        <div
          className="rounded-t-2xl px-4 py-2.5 flex items-center justify-center gap-2"
          style={{
            background: "linear-gradient(135deg, #7f1d1d, #991b1b)",
            border: "1px solid #ef4444",
            borderBottom: "none",
          }}
        >
          <AlertTriangle size={14} className="text-red-300" />
          <span className="text-red-200 text-xs font-bold tracking-widest uppercase">
            Restricted System — Authorised Access Only
          </span>
          <AlertTriangle size={14} className="text-red-300" />
        </div>

        {/* Card */}
        <div
          className="rounded-b-2xl p-8"
          style={{
            background: "rgba(10,20,40,0.95)",
            border: "1px solid rgba(0,242,255,0.15)",
            borderTop: "none",
            boxShadow: "0 0 40px rgba(0,242,255,0.08), 0 25px 50px rgba(0,0,0,0.5)",
          }}
        >
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div
              className="w-16 h-16 rounded-full border-2 border-cyan-400/60 flex items-center justify-center mb-4"
              style={{
                background: "rgba(0,242,255,0.08)",
                boxShadow: "0 0 25px rgba(0,242,255,0.25), inset 0 0 15px rgba(0,242,255,0.05)",
              }}
            >
              <Shield size={30} className="text-cyan-400" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">NSG VisionAI</h1>
            <p className="text-xs text-slate-500 mt-1 font-mono tracking-wide">
              Video Intelligence Platform — Restricted Access
            </p>
          </div>

          {/* Lockout state */}
          {isLocked && (
            <div
              className="mb-5 flex items-start gap-3 px-4 py-3 rounded-xl"
              style={{
                background: "rgba(127,29,29,0.3)",
                border: "1px solid rgba(239,68,68,0.4)",
              }}
            >
              <Lock size={15} className="text-red-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-red-300 text-sm font-semibold">Account Locked</p>
                <p className="text-red-400/80 text-xs mt-0.5">
                  Locked for {lockoutMinutes} minutes. Contact NSG IT Cell for immediate access.
                </p>
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Service Number */}
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                Service Number
              </label>
              <input
                type="text"
                value={serviceNumber}
                onChange={(e) => setServiceNumber(e.target.value.toUpperCase())}
                placeholder="NSG/UNIT/12345"
                required
                disabled={isLocked || isLoading}
                className="w-full px-4 py-3.5 rounded-xl text-sm font-mono text-white placeholder-slate-600 transition-all disabled:opacity-50"
                style={{
                  background: "rgba(15,25,50,0.8)",
                  border: "1px solid rgba(59,130,246,0.25)",
                  outline: "none",
                }}
                onFocus={(e) => {
                  e.target.style.border = "1px solid rgba(0,242,255,0.5)";
                  e.target.style.boxShadow = "0 0 15px rgba(0,242,255,0.1)";
                }}
                onBlur={(e) => {
                  e.target.style.border = "1px solid rgba(59,130,246,0.25)";
                  e.target.style.boxShadow = "none";
                }}
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={isLocked || isLoading}
                  className="w-full px-4 py-3.5 pr-12 rounded-xl text-sm text-white placeholder-slate-600 transition-all disabled:opacity-50"
                  style={{
                    background: "rgba(15,25,50,0.8)",
                    border: "1px solid rgba(59,130,246,0.25)",
                    outline: "none",
                  }}
                  onFocus={(e) => {
                    e.target.style.border = "1px solid rgba(0,242,255,0.5)";
                    e.target.style.boxShadow = "0 0 15px rgba(0,242,255,0.1)";
                  }}
                  onBlur={(e) => {
                    e.target.style.border = "1px solid rgba(59,130,246,0.25)";
                    e.target.style.boxShadow = "none";
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-cyan-400 transition-colors"
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && !isLocked && (
              <div
                className="flex items-center gap-2.5 px-4 py-3 rounded-xl"
                style={{
                  background: "rgba(127,29,29,0.35)",
                  border: "1px solid rgba(239,68,68,0.4)",
                }}
              >
                <AlertTriangle size={14} className="text-red-400 shrink-0" />
                <p className="text-red-300 text-xs">{error}</p>
              </div>
            )}

            {/* Sign In button */}
            <button
              type="submit"
              disabled={isLocked || isLoading}
              className="w-full py-3.5 rounded-xl font-bold text-sm tracking-widest transition-all"
              style={{
                background:
                  isLocked || isLoading
                    ? "rgba(59,130,246,0.2)"
                    : "linear-gradient(135deg, #00f2ff, #0080ff)",
                color: isLocked || isLoading ? "#64748b" : "#05070a",
                boxShadow:
                  isLocked || isLoading ? "none" : "0 0 20px rgba(0,242,255,0.35)",
                cursor: isLocked || isLoading ? "not-allowed" : "pointer",
              }}
            >
              {isLoading ? "AUTHENTICATING..." : "SIGN IN"}
            </button>
          </form>

          {/* Sign Up link */}
          <p className="text-center text-xs text-slate-500 mt-5">
            Don't have an account?{" "}
            <button
              onClick={onNavigateToRegister}
              className="font-semibold transition-colors"
              style={{ color: "#00f2ff" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#67e8f9")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "#00f2ff")}
            >
              Sign Up
            </button>
          </p>

          {/* Session reminder */}
          <p className="text-center text-xs text-slate-600 mt-3">
            Sessions auto-expire after 8 hours
          </p>

          {/* Footer */}
          <p className="text-center text-[10px] text-slate-700 mt-5 font-mono">
            NSG IT Cell — Ministry of Home Affairs | v1.0.0
          </p>
        </div>
      </div>
    </div>
  );
}
