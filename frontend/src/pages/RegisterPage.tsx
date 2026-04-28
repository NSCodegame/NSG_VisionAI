/**
 * Register Page — NSG VisionAI
 *
 * Self-registration for new operators.
 * Accounts are created inactive and require admin approval.
 */

import { useState } from "react";
import {
  Shield, Eye, EyeOff, AlertTriangle, CheckCircle,
  User, Hash, Star, Mail, Lock, ArrowLeft,
} from "lucide-react";
import apiClient from "../services/api";

interface RegisterPageProps {
  onNavigateToLogin: () => void;
}

interface FormData {
  full_name: string;
  service_number: string;
  rank: string;
  email: string;
  unit: string;
  password: string;
  confirm_password: string;
  terms: boolean;
}

const RANKS = [
  "Constable", "Head Constable", "ASI", "SI", "Inspector",
  "DSP", "SP", "SSP", "DIG", "IG", "ADG", "DG",
  "Commandant", "Deputy Commandant", "Assistant Commandant",
];

export function RegisterPage({ onNavigateToLogin }: RegisterPageProps) {
  const [form, setForm] = useState<FormData>({
    full_name: "",
    service_number: "",
    rank: "",
    email: "",
    unit: "",
    password: "",
    confirm_password: "",
    terms: false,
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const set = (key: keyof FormData, value: string | boolean) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const validate = (): string | null => {
    if (!form.full_name.trim()) return "Full name is required";
    if (!form.service_number.trim()) return "Service number is required";
    if (!/^NSG\/[A-Z]+\/\d+$/.test(form.service_number.toUpperCase()))
      return "Service number must be in format NSG/UNIT/NUMBER (e.g., NSG/OP/1234)";
    if (!form.password) return "Password is required";
    if (form.password.length < 8) return "Password must be at least 8 characters";
    if (form.password !== form.confirm_password) return "Passwords do not match";
    if (!form.terms) return "You must accept the Terms & Conditions";
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const validationError = validate();
    if (validationError) { setError(validationError); return; }

    setIsLoading(true);
    try {
      await apiClient.post("/auth/register", {
        full_name: form.full_name,
        service_number: form.service_number.toUpperCase(),
        rank: form.rank || undefined,
        email: form.email || undefined,
        unit: form.unit || undefined,
        password: form.password,
        confirm_password: form.confirm_password,
      });
      setSuccess(true);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr.response?.data?.detail ?? "Registration failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // ── Success screen ──────────────────────────────────────────────────────
  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "#05070a" }}>
        <GridBackground />
        <div className="relative w-full max-w-md text-center">
          <div className="rounded-2xl border border-cyan-500/30 p-10"
            style={{ background: "rgba(10,20,40,0.95)", boxShadow: "0 0 40px rgba(0,242,255,0.1)" }}>
            <div className="w-20 h-20 rounded-full border-2 border-emerald-400 flex items-center justify-center mx-auto mb-6"
              style={{ boxShadow: "0 0 20px rgba(16,185,129,0.4)" }}>
              <CheckCircle size={40} className="text-emerald-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-3">Registration Submitted</h2>
            <p className="text-slate-400 text-sm leading-relaxed mb-2">
              Your account request has been submitted successfully.
            </p>
            <p className="text-cyan-400 text-sm font-mono mb-8">
              Status: <span className="text-yellow-400">PENDING ADMIN APPROVAL</span>
            </p>
            <div className="bg-slate-900/60 border border-slate-700 rounded-xl p-4 text-left mb-8 space-y-1">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Next Steps</p>
              <p className="text-xs text-slate-400">1. Contact NSG IT Cell to activate your account</p>
              <p className="text-xs text-slate-400">2. An admin will review and approve your request</p>
              <p className="text-xs text-slate-400">3. You will be notified once access is granted</p>
            </div>
            <button
              onClick={onNavigateToLogin}
              className="w-full py-3 rounded-xl font-bold text-sm tracking-widest transition-all"
              style={{ background: "linear-gradient(135deg, #00f2ff, #0080ff)", color: "#05070a" }}
            >
              BACK TO SIGN IN
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Register form ───────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "#05070a" }}>
      <GridBackground />

      <div className="relative w-full max-w-md">
        {/* Warning banner */}
        <div className="rounded-t-2xl px-4 py-2.5 flex items-center justify-center gap-2"
          style={{ background: "linear-gradient(135deg, #7f1d1d, #991b1b)", border: "1px solid #ef4444" }}>
          <AlertTriangle size={14} className="text-red-300" />
          <span className="text-red-200 text-xs font-bold tracking-widest uppercase">
            Restricted System — Authorised Access Only
          </span>
          <AlertTriangle size={14} className="text-red-300" />
        </div>

        {/* Card */}
        <div className="rounded-b-2xl p-8"
          style={{
            background: "rgba(10,20,40,0.95)",
            border: "1px solid rgba(0,242,255,0.15)",
            borderTop: "none",
            boxShadow: "0 0 40px rgba(0,242,255,0.08), 0 25px 50px rgba(0,0,0,0.5)",
          }}>

          {/* Back link */}
          <button
            onClick={onNavigateToLogin}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-cyan-400 transition-colors mb-6"
          >
            <ArrowLeft size={13} /> Back to Sign In
          </button>

          {/* Logo */}
          <div className="flex flex-col items-center mb-7">
            <div className="w-14 h-14 rounded-full border-2 border-cyan-400/50 flex items-center justify-center mb-4"
              style={{ background: "rgba(0,242,255,0.08)", boxShadow: "0 0 20px rgba(0,242,255,0.2)" }}>
              <Shield size={26} className="text-cyan-400" />
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">Create Account</h1>
            <p className="text-xs text-slate-500 mt-1 font-mono">NSG VisionAI — New Operator Registration</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name */}
            <InputField
              icon={<User size={15} />}
              label="Full Name *"
              type="text"
              value={form.full_name}
              onChange={(v) => set("full_name", v)}
              placeholder="Rajesh Kumar"
            />

            {/* Service Number */}
            <InputField
              icon={<Hash size={15} />}
              label="Service Number *"
              type="text"
              value={form.service_number}
              onChange={(v) => set("service_number", v.toUpperCase())}
              placeholder="NSG/OP/1234"
              mono
            />

            {/* Rank */}
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                Rank / Designation
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
                  <Star size={15} />
                </div>
                <select
                  value={form.rank}
                  onChange={(e) => set("rank", e.target.value)}
                  className="w-full pl-9 pr-4 py-3 rounded-xl text-sm text-white appearance-none"
                  style={{
                    background: "rgba(15,25,50,0.8)",
                    border: "1px solid rgba(59,130,246,0.25)",
                    outline: "none",
                  }}
                >
                  <option value="">Select rank (optional)</option>
                  {RANKS.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            </div>

            {/* Email */}
            <InputField
              icon={<Mail size={15} />}
              label="Email Address"
              type="email"
              value={form.email}
              onChange={(v) => set("email", v)}
              placeholder="officer@nsg.gov.in"
            />

            {/* Unit */}
            <InputField
              icon={<Shield size={15} />}
              label="Unit / Division"
              type="text"
              value={form.unit}
              onChange={(v) => set("unit", v)}
              placeholder="SAG, SFC, NSG HQ..."
            />

            {/* Password */}
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                Password *
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
                  <Lock size={15} />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  value={form.password}
                  onChange={(e) => set("password", e.target.value)}
                  placeholder="Min. 8 characters"
                  className="w-full pl-9 pr-12 py-3 rounded-xl text-sm text-white"
                  style={{
                    background: "rgba(15,25,50,0.8)",
                    border: "1px solid rgba(59,130,246,0.25)",
                    outline: "none",
                  }}
                />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-cyan-400 transition-colors">
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                Confirm Password *
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
                  <Lock size={15} />
                </div>
                <input
                  type={showConfirm ? "text" : "password"}
                  value={form.confirm_password}
                  onChange={(e) => set("confirm_password", e.target.value)}
                  placeholder="Re-enter password"
                  className="w-full pl-9 pr-12 py-3 rounded-xl text-sm text-white"
                  style={{
                    background: "rgba(15,25,50,0.8)",
                    border: form.confirm_password && form.confirm_password !== form.password
                      ? "1px solid rgba(239,68,68,0.6)"
                      : form.confirm_password && form.confirm_password === form.password
                        ? "1px solid rgba(16,185,129,0.6)"
                        : "1px solid rgba(59,130,246,0.25)",
                    outline: "none",
                  }}
                />
                <button type="button" onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-cyan-400 transition-colors">
                  {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {form.confirm_password && form.confirm_password !== form.password && (
                <p className="text-xs text-red-400 mt-1">Passwords do not match</p>
              )}
            </div>

            {/* Terms */}
            <label className="flex items-start gap-3 cursor-pointer group">
              <div
                onClick={() => set("terms", !form.terms)}
                className="mt-0.5 w-5 h-5 rounded border flex items-center justify-center shrink-0 transition-all"
                style={{
                  background: form.terms ? "rgba(0,242,255,0.2)" : "rgba(15,25,50,0.8)",
                  border: form.terms ? "1px solid #00f2ff" : "1px solid rgba(59,130,246,0.3)",
                  boxShadow: form.terms ? "0 0 8px rgba(0,242,255,0.3)" : "none",
                }}
              >
                {form.terms && <CheckCircle size={12} className="text-cyan-400" />}
              </div>
              <span className="text-xs text-slate-400 leading-relaxed">
                I agree to the{" "}
                <span className="text-cyan-400 cursor-pointer hover:underline">Terms & Conditions</span>
                {" "}and acknowledge that this system is for authorised NSG personnel only.
                Unauthorised access is a criminal offence.
              </span>
            </label>

            {/* Error */}
            {error && (
              <div className="flex items-start gap-2 px-4 py-3 rounded-xl"
                style={{ background: "rgba(127,29,29,0.4)", border: "1px solid rgba(239,68,68,0.4)" }}>
                <AlertTriangle size={14} className="text-red-400 mt-0.5 shrink-0" />
                <p className="text-red-300 text-xs">{error}</p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3.5 rounded-xl font-bold text-sm tracking-widest transition-all mt-2"
              style={{
                background: isLoading
                  ? "rgba(59,130,246,0.3)"
                  : "linear-gradient(135deg, #00f2ff, #0080ff)",
                color: isLoading ? "#94a3b8" : "#05070a",
                boxShadow: isLoading ? "none" : "0 0 20px rgba(0,242,255,0.3)",
                cursor: isLoading ? "not-allowed" : "pointer",
              }}
            >
              {isLoading ? "SUBMITTING..." : "SIGN UP"}
            </button>
          </form>

          {/* Sign in link */}
          <p className="text-center text-xs text-slate-500 mt-5">
            Already have an account?{" "}
            <button
              onClick={onNavigateToLogin}
              className="text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
            >
              Sign In
            </button>
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

// ── Shared sub-components ─────────────────────────────────────────────────

function InputField({
  icon, label, type, value, onChange, placeholder, mono = false,
}: {
  icon: React.ReactNode;
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  mono?: boolean;
}) {
  return (
    <div>
      <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">
        {label}
      </label>
      <div className="relative">
        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">{icon}</div>
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`w-full pl-9 pr-4 py-3 rounded-xl text-sm text-white placeholder-slate-600 transition-all ${mono ? "font-mono" : ""}`}
          style={{
            background: "rgba(15,25,50,0.8)",
            border: "1px solid rgba(59,130,246,0.25)",
            outline: "none",
          }}
          onFocus={(e) => { e.target.style.border = "1px solid rgba(0,242,255,0.5)"; e.target.style.boxShadow = "0 0 12px rgba(0,242,255,0.1)"; }}
          onBlur={(e) => { e.target.style.border = "1px solid rgba(59,130,246,0.25)"; e.target.style.boxShadow = "none"; }}
        />
      </div>
    </div>
  );
}

function GridBackground() {
  return (
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
  );
}
