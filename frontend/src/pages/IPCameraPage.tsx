/**
 * IP Camera Configuration Page
 *
 * Two-panel layout:
 *   Left  — Subnet scanner: discover cameras on the LAN
 *   Right — Camera configurator: register a discovered (or manual) camera
 */

import { useState } from "react";
import {
  Wifi, WifiOff, Search, Plus, CheckCircle, XCircle,
  RefreshCw, Camera, Settings, ChevronRight, AlertTriangle,
  Eye, EyeOff, Network,
} from "lucide-react";
import {
  ipCameraService,
  feedService,
  type DiscoveredCamera,
  type IPCameraConfigRequest,
} from "../services/feedService";

// ── Brand options ──────────────────────────────────────────────────────────

const BRANDS = [
  { value: "", label: "Auto-detect" },
  { value: "hikvision", label: "Hikvision" },
  { value: "dahua", label: "Dahua" },
  { value: "axis", label: "Axis" },
  { value: "reolink", label: "Reolink" },
  { value: "amcrest", label: "Amcrest" },
];

const BRAND_PATHS: Record<string, string> = {
  hikvision: "/Streaming/Channels/101",
  dahua: "/cam/realmonitor?channel=1&subtype=0",
  axis: "/axis-media/media.amp",
  reolink: "/h264Preview_01_main",
  amcrest: "/cam/realmonitor?channel=1&subtype=0",
};

// ── Helper ─────────────────────────────────────────────────────────────────

function Field({
  label, children, hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div>
      <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
        {label}
      </label>
      {children}
      {hint && <p className="text-[10px] text-slate-600 mt-1">{hint}</p>}
    </div>
  );
}

function Input({
  value, onChange, placeholder, type = "text", disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  disabled?: boolean;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-xs text-white
                 focus:outline-none focus:border-cyan-500/60 disabled:opacity-50 disabled:cursor-not-allowed"
    />
  );
}

// ── Subnet Scanner Panel ───────────────────────────────────────────────────

function ScannerPanel({
  onSelect,
}: {
  onSelect: (cam: DiscoveredCamera) => void;
}) {
  const [subnet, setSubnet] = useState("192.168.1.0/24");
  const [port, setPort] = useState("554");
  const [scanning, setScanning] = useState(false);
  const [results, setResults] = useState<DiscoveredCamera[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [scanned, setScanned] = useState(false);

  const handleScan = async () => {
    setScanning(true);
    setError(null);
    setResults([]);
    try {
      const res = await ipCameraService.discover(subnet, Number(port));
      setResults(res.cameras);
      setScanned(true);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Scan failed. Check subnet format.";
      setError(msg);
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-blue-500/10">
        <div className="flex items-center gap-2 mb-3">
          <Network size={14} className="text-cyan-400" />
          <h2 className="text-sm font-bold text-white">Discover Cameras</h2>
        </div>
        <p className="text-[10px] text-slate-500 mb-3">
          Scan your LAN for IP cameras with RTSP port open.
        </p>

        <div className="space-y-2">
          <Field label="Subnet (CIDR)">
            <Input
              value={subnet}
              onChange={setSubnet}
              placeholder="192.168.1.0/24"
              disabled={scanning}
            />
          </Field>
          <Field label="RTSP Port">
            <Input
              value={port}
              onChange={setPort}
              placeholder="554"
              disabled={scanning}
            />
          </Field>
          <button
            onClick={handleScan}
            disabled={scanning || !subnet}
            className="w-full flex items-center justify-center gap-2 py-2 bg-cyan-500/20 border
                       border-cyan-500/40 rounded text-xs text-cyan-400 hover:bg-cyan-500/30
                       disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {scanning ? (
              <RefreshCw size={12} className="animate-spin" />
            ) : (
              <Search size={12} />
            )}
            {scanning ? "Scanning…" : "Scan Network"}
          </button>
        </div>

        {error && (
          <div className="mt-3 flex items-start gap-2 text-xs text-red-400 bg-red-900/20
                          border border-red-500/30 rounded px-3 py-2">
            <AlertTriangle size={12} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {scanned && results.length === 0 && !scanning && (
          <div className="text-center py-8">
            <WifiOff size={28} className="text-slate-700 mx-auto mb-2" />
            <p className="text-xs text-slate-500">No cameras found on {subnet}</p>
            <p className="text-[10px] text-slate-600 mt-1">
              Check that cameras are powered and on the same network.
            </p>
          </div>
        )}

        {results.map((cam) => (
          <div
            key={cam.ip}
            className="bg-slate-900/60 border border-slate-700 rounded-lg p-3 hover:border-cyan-500/40
                       transition-colors cursor-pointer group"
            onClick={() => onSelect(cam)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-sm font-bold text-white font-mono">{cam.ip}</span>
                <span className="text-[10px] text-slate-500">:{cam.port}</span>
              </div>
              <ChevronRight
                size={14}
                className="text-slate-600 group-hover:text-cyan-400 transition-colors"
              />
            </div>
            <div className="mt-1.5 flex gap-3 text-[10px] text-slate-500 font-mono">
              <span className="flex items-center gap-1">
                <Wifi size={9} className="text-emerald-400" /> RTSP OPEN
              </span>
              {cam.resolution && <span>{cam.resolution}</span>}
              {cam.fps && <span>{cam.fps} fps</span>}
            </div>
            <p className="text-[10px] text-cyan-500/60 mt-1">Click to configure →</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Camera Configurator Panel ──────────────────────────────────────────────

function ConfiguratorPanel({
  prefill,
  onSuccess,
}: {
  prefill: DiscoveredCamera | null;
  onSuccess: (feedId: string) => void;
}) {
  const [form, setForm] = useState<IPCameraConfigRequest>({
    ip: prefill?.ip ?? "",
    port: prefill?.port ?? 554,
    username: "admin",
    password: "",
    stream_path: prefill?.stream_path ?? "",
    brand: "",
    name: prefill ? `Camera ${prefill.ip}` : "",
    location_name: "",
    ai_enabled: true,
    auto_probe: true,
  });

  // Update form when prefill changes
  const [lastPrefillIp, setLastPrefillIp] = useState<string | null>(null);
  if (prefill && prefill.ip !== lastPrefillIp) {
    setLastPrefillIp(prefill.ip);
    setForm((prev) => ({
      ...prev,
      ip: prefill.ip,
      port: prefill.port,
      name: `Camera ${prefill.ip}`,
      stream_path: prefill.stream_path ?? "",
    }));
  }

  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [result, setResult] = useState<{ feed_id: string; message: string; stream_path: string; resolution?: string; fps?: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const set = (key: keyof IPCameraConfigRequest, value: unknown) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  // When brand changes, suggest the default path
  const handleBrandChange = (brand: string) => {
    set("brand", brand);
    if (brand && BRAND_PATHS[brand] && !form.stream_path) {
      set("stream_path", BRAND_PATHS[brand]);
    }
  };

  const handleTestRTSP = async () => {
    const url = `rtsp://${form.username}:${form.password}@${form.ip}:${form.port}${form.stream_path || "/stream1"}`;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await feedService.testConnection(url);
      setTestResult(res);
    } catch {
      setTestResult({ success: false, message: "Connection test failed" });
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async () => {
    if (!form.ip || !form.name) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const res = await ipCameraService.configure(form);
      setResult({
        feed_id: res.feed_id,
        message: res.message,
        stream_path: res.stream_path,
        resolution: res.resolution ?? undefined,
        fps: res.fps ?? undefined,
      });
      onSuccess(res.feed_id);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Failed to configure camera.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-blue-500/10 flex items-center gap-2">
        <Camera size={14} className="text-cyan-400" />
        <h2 className="text-sm font-bold text-white">Configure IP Camera</h2>
        {prefill && (
          <span className="ml-auto text-[10px] font-mono text-emerald-400 bg-emerald-900/20
                           border border-emerald-500/30 px-2 py-0.5 rounded">
            {prefill.ip} selected
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Success banner */}
        {result && (
          <div className="bg-emerald-900/20 border border-emerald-500/30 rounded-lg p-3">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold mb-1">
              <CheckCircle size={14} /> Camera Registered Successfully
            </div>
            <div className="text-[10px] text-slate-400 space-y-0.5 font-mono">
              <p>Feed ID: {result.feed_id}</p>
              <p>Stream: {result.stream_path}</p>
              {result.resolution && <p>Resolution: {result.resolution}</p>}
              {result.fps && <p>FPS: {result.fps}</p>}
            </div>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 flex items-start gap-2">
            <XCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
            <p className="text-xs text-red-400">{error}</p>
          </div>
        )}

        {/* Connection section */}
        <div className="bg-slate-900/40 border border-slate-800 rounded-lg p-3 space-y-3">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            Connection
          </p>

          <div className="grid grid-cols-3 gap-2">
            <div className="col-span-2">
              <Field label="Camera IP *">
                <Input
                  value={form.ip}
                  onChange={(v) => set("ip", v)}
                  placeholder="192.168.1.64"
                />
              </Field>
            </div>
            <Field label="Port">
              <Input
                value={String(form.port)}
                onChange={(v) => set("port", Number(v))}
                placeholder="554"
              />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <Field label="Username">
              <Input
                value={form.username}
                onChange={(v) => set("username", v)}
                placeholder="admin"
              />
            </Field>
            <Field label="Password">
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={form.password}
                  onChange={(e) => set("password", e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-xs
                             text-white focus:outline-none focus:border-cyan-500/60 pr-8"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showPassword ? <EyeOff size={12} /> : <Eye size={12} />}
                </button>
              </div>
            </Field>
          </div>

          <Field label="Brand" hint="Helps auto-detect the correct stream path faster">
            <select
              value={form.brand ?? ""}
              onChange={(e) => handleBrandChange(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-xs
                         text-white focus:outline-none focus:border-cyan-500/60"
            >
              {BRANDS.map((b) => (
                <option key={b.value} value={b.value}>{b.label}</option>
              ))}
            </select>
          </Field>

          <Field
            label="Stream Path"
            hint='Leave blank to auto-detect. Example: /Streaming/Channels/101'
          >
            <Input
              value={form.stream_path ?? ""}
              onChange={(v) => set("stream_path", v)}
              placeholder="/stream1  (auto-detected if blank)"
            />
          </Field>

          {/* Auto-probe toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <div
              onClick={() => set("auto_probe", !form.auto_probe)}
              className={`w-8 h-4 rounded-full transition-colors relative ${
                form.auto_probe ? "bg-cyan-500" : "bg-slate-700"
              }`}
            >
              <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${
                form.auto_probe ? "translate-x-4" : "translate-x-0.5"
              }`} />
            </div>
            <span className="text-xs text-slate-400">
              Auto-probe stream path
              <span className="text-slate-600 ml-1">(recommended)</span>
            </span>
          </label>

          {/* Test connection */}
          <button
            onClick={handleTestRTSP}
            disabled={!form.ip || testing}
            className="w-full flex items-center justify-center gap-2 py-1.5 bg-slate-800
                       border border-slate-700 rounded text-xs text-slate-400
                       hover:border-slate-500 disabled:opacity-50 transition-colors"
          >
            {testing ? <RefreshCw size={11} className="animate-spin" /> : <Wifi size={11} />}
            {testing ? "Testing…" : "Test RTSP Connection"}
          </button>

          {testResult && (
            <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded border ${
              testResult.success
                ? "bg-emerald-900/20 border-emerald-500/30 text-emerald-400"
                : "bg-red-900/20 border-red-500/30 text-red-400"
            }`}>
              {testResult.success
                ? <CheckCircle size={12} />
                : <XCircle size={12} />}
              {testResult.message}
            </div>
          )}
        </div>

        {/* Feed metadata section */}
        <div className="bg-slate-900/40 border border-slate-800 rounded-lg p-3 space-y-3">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            Feed Details
          </p>

          <Field label="Feed Name *">
            <Input
              value={form.name}
              onChange={(v) => set("name", v)}
              placeholder="Gate Camera 1"
            />
          </Field>

          <Field label="Location Name">
            <Input
              value={form.location_name ?? ""}
              onChange={(v) => set("location_name", v)}
              placeholder="Main Entrance"
            />
          </Field>

          <div className="grid grid-cols-2 gap-2">
            <Field label="Latitude">
              <Input
                value={String(form.latitude ?? "")}
                onChange={(v) => set("latitude", v ? Number(v) : undefined)}
                placeholder="28.6139"
              />
            </Field>
            <Field label="Longitude">
              <Input
                value={String(form.longitude ?? "")}
                onChange={(v) => set("longitude", v ? Number(v) : undefined)}
                placeholder="77.2090"
              />
            </Field>
          </div>

          {/* AI toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <div
              onClick={() => set("ai_enabled", !form.ai_enabled)}
              className={`w-8 h-4 rounded-full transition-colors relative ${
                form.ai_enabled ? "bg-cyan-500" : "bg-slate-700"
              }`}
            >
              <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${
                form.ai_enabled ? "translate-x-4" : "translate-x-0.5"
              }`} />
            </div>
            <span className="text-xs text-slate-400">Enable AI processing</span>
          </label>
        </div>

        {/* RTSP URL preview */}
        {form.ip && (
          <div className="bg-slate-900/40 border border-slate-800 rounded-lg p-3">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
              RTSP URL Preview
            </p>
            <p className="text-[10px] font-mono text-cyan-400/70 break-all">
              rtsp://{form.username || "admin"}:{"•".repeat(form.password.length || 4)}
              @{form.ip}:{form.port}{form.stream_path || "/stream1"}
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-blue-500/10">
        <button
          onClick={handleSubmit}
          disabled={!form.ip || !form.name || submitting}
          className="w-full py-2.5 bg-cyan-500 hover:bg-cyan-400 disabled:bg-slate-700
                     disabled:cursor-not-allowed text-slate-900 font-bold rounded text-sm
                     transition-all flex items-center justify-center gap-2"
        >
          {submitting ? (
            <><RefreshCw size={14} className="animate-spin" /> Registering…</>
          ) : (
            <><Plus size={14} /> Register Camera</>
          )}
        </button>
        <p className="text-[10px] text-slate-600 text-center mt-2">
          {form.auto_probe
            ? "Server will auto-detect the stream path"
            : "Using provided stream path"}
        </p>
      </div>
    </div>
  );
}

// ── Quick Reference Panel ──────────────────────────────────────────────────

function QuickReference() {
  const brands = [
    { name: "Hikvision", path: "/Streaming/Channels/101", port: "554" },
    { name: "Dahua", path: "/cam/realmonitor?channel=1&subtype=0", port: "554" },
    { name: "Axis", path: "/axis-media/media.amp", port: "554" },
    { name: "Reolink", path: "/h264Preview_01_main", port: "554" },
    { name: "Amcrest", path: "/cam/realmonitor?channel=1&subtype=0", port: "554" },
    { name: "Generic", path: "/stream1", port: "554" },
  ];

  return (
    <div className="p-4 border-t border-blue-500/10 bg-slate-900/30">
      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
        RTSP Path Reference
      </p>
      <div className="space-y-1">
        {brands.map((b) => (
          <div key={b.name} className="flex items-center gap-2 text-[10px] font-mono">
            <span className="text-slate-400 w-16 shrink-0">{b.name}</span>
            <span className="text-cyan-400/60 truncate">{b.path}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

export function IPCameraPage() {
  const [selectedCamera, setSelectedCamera] = useState<DiscoveredCamera | null>(null);
  const [registeredFeeds, setRegisteredFeeds] = useState<string[]>([]);

  const handleSuccess = (feedId: string) => {
    setRegisteredFeeds((prev) => [feedId, ...prev]);
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Page header */}
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-blue-500/10
                      bg-[#0d1117]/60 shrink-0">
        <Camera size={14} className="text-cyan-400" />
        <h1 className="text-sm font-bold text-white">IP Camera Configuration</h1>
        <span className="text-[10px] text-slate-500">
          Discover and register CCTV / IP cameras on your network
        </span>
        {registeredFeeds.length > 0 && (
          <span className="ml-auto text-[10px] font-bold text-emerald-400 bg-emerald-900/20
                           border border-emerald-500/30 px-2 py-0.5 rounded">
            {registeredFeeds.length} camera{registeredFeeds.length > 1 ? "s" : ""} registered
          </span>
        )}
      </div>

      {/* Two-panel layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left — Scanner */}
        <div className="w-72 shrink-0 border-r border-blue-500/10 flex flex-col overflow-hidden">
          <ScannerPanel onSelect={setSelectedCamera} />
        </div>

        {/* Right — Configurator + reference */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <ConfiguratorPanel
              prefill={selectedCamera}
              onSuccess={handleSuccess}
            />
          </div>
          <QuickReference />
        </div>
      </div>
    </div>
  );
}
