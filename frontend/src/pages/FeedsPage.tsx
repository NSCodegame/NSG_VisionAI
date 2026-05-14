/**
 * Feed Management Page — Phase 28.3
 *
 * Status summary bar, feed cards grid, add feed drawer.
 */

import { useState, useEffect } from "react";
import { Monitor, Plus, RefreshCw, Wifi, WifiOff, AlertTriangle, Play, Pause, Trash2, Edit, CheckCircle, XCircle } from "lucide-react";
import { feedService, type FeedItem, type CreateFeedRequest } from "../services/feedService";

const STATUS_CONFIG: Record<string, { color: string; icon: React.ElementType; label: string }> = {
  ACTIVE: { color: "text-emerald-400 border-emerald-500/40", icon: Wifi, label: "ACTIVE" },
  OFFLINE: { color: "text-red-400 border-red-500/40", icon: WifiOff, label: "OFFLINE" },
  DEGRADED: { color: "text-yellow-400 border-yellow-500/40", icon: AlertTriangle, label: "DEGRADED" },
  MAINTENANCE: { color: "text-slate-400 border-slate-500/40", icon: Monitor, label: "MAINTENANCE" },
};

export function FeedsPage() {
  const [feeds, setFeeds] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [testing, setTesting] = useState(false);

  // Add form state
  const [form, setForm] = useState<CreateFeedRequest>({
    name: "",
    feed_type: "FIXED_CAMERA",
    rtsp_url: "",
    location_name: "",
    fps: 25,
    resolution: "1920x1080",
  });

  const load = async () => {
    setLoading(true);
    try {
      const data = await feedService.list();
      if (data && data.length > 0) {
        setFeeds(data);
      } else {
        const { SEED_FEEDS } = await import("../data/seedData");
        setFeeds(SEED_FEEDS);
      }
    } catch {
      const { SEED_FEEDS } = await import("../data/seedData");
      setFeeds(SEED_FEEDS);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleTestConnection = async () => {
    if (!form.rtsp_url) return;
    setTesting(true);
    setTestResult(null);
    try {
      const result = await feedService.testConnection(form.rtsp_url);
      setTestResult(result);
    } catch {
      setTestResult({ success: false, message: "Connection test failed" });
    } finally {
      setTesting(false);
    }
  };

  const handleAddFeed = async () => {
    if (!form.name || !form.rtsp_url) return;
    try {
      const feed = await feedService.create(form);
      setFeeds((prev) => [feed, ...prev]);
      setShowAddForm(false);
      setForm({ name: "", feed_type: "FIXED_CAMERA", rtsp_url: "", location_name: "", fps: 25, resolution: "1920x1080" });
      setTestResult(null);
    } catch (err) {
      console.error("Add feed failed:", err);
    }
  };

  const handleToggleAI = async (feedId: string) => {
    try {
      const updated = await feedService.toggleAI(feedId);
      setFeeds((prev) => prev.map((f) => (f.id === feedId ? updated : f)));
    } catch (err) {
      console.error("Toggle AI failed:", err);
    }
  };

  const handleDelete = async (feedId: string) => {
    if (!confirm("Delete this feed?")) return;
    try {
      await feedService.delete(feedId);
      setFeeds((prev) => prev.filter((f) => f.id !== feedId));
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  // Status summary
  const counts = feeds.reduce((acc, f) => {
    acc[f.status] = (acc[f.status] ?? 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Status summary bar */}
      <div className="flex items-center gap-6 px-4 py-2.5 border-b border-blue-500/10 bg-[#0d1117]/60 shrink-0">
        <span className="text-xs font-bold text-slate-400">FEEDS: {feeds.length}</span>
        {Object.entries(STATUS_CONFIG).map(([status, cfg]) => {
          const Icon = cfg.icon;
          const count = counts[status] ?? 0;
          return (
            <div key={status} className="flex items-center gap-1.5 text-xs">
              <Icon size={12} className={cfg.color.split(" ")[0]} />
              <span className={cfg.color.split(" ")[0]}>{count} {cfg.label}</span>
            </div>
          );
        })}
        <div className="ml-auto flex gap-2">
          <button onClick={load} className="p-1.5 text-slate-500 hover:text-cyan-400 transition-colors">
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-500/20 border border-cyan-500/40 rounded text-xs text-cyan-400 hover:bg-cyan-500/30 transition-colors"
          >
            <Plus size={12} /> Add Feed
          </button>
        </div>
      </div>

      {/* Feed cards grid */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="text-center text-slate-600 text-xs py-12">Loading feeds...</div>
        ) : feeds.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 gap-3">
            <Monitor size={40} className="text-slate-700" />
            <p className="text-slate-500 text-sm">No feeds configured</p>
            <button
              onClick={() => setShowAddForm(true)}
              className="flex items-center gap-2 px-4 py-2 bg-cyan-500/20 border border-cyan-500/40 rounded text-xs text-cyan-400"
            >
              <Plus size={12} /> Add First Feed
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {feeds.map((feed) => {
              const cfg = STATUS_CONFIG[feed.status] ?? STATUS_CONFIG.OFFLINE;
              const StatusIcon = cfg.icon;
              return (
                <div
                  key={feed.id}
                  className={`bg-slate-900/60 border rounded-lg overflow-hidden ${
                    feed.status === "ACTIVE" ? "border-slate-700" : `border-${cfg.color.split("-")[1]}-500/20`
                  }`}
                >
                  {/* Thumbnail area — live MJPEG snapshot */}
                  <div className="h-36 bg-slate-900 flex items-center justify-center relative overflow-hidden">
                    {feed.status === "ACTIVE" ? (
                      <img
                        src={`${import.meta.env.VITE_API_URL ?? "/api/v1"}/streams/${feed.id}/snapshot?token=${localStorage.getItem("access_token") ?? ""}&_t=${Date.now()}`}
                        alt={feed.name}
                        className="w-full h-full object-cover"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                      />
                    ) : (
                      <Monitor size={28} className="text-slate-700" />
                    )}
                    <div className={`absolute top-2 right-2 flex items-center gap-1 px-2 py-0.5 rounded border text-[9px] font-bold ${cfg.color}`}>
                      <StatusIcon size={9} />
                      {cfg.label}
                    </div>
                    {feed.ai_processing_enabled && (
                      <div className="absolute bottom-2 left-2 text-[9px] font-bold text-emerald-400 bg-emerald-900/60 border border-emerald-500/30 px-1.5 py-0.5 rounded">
                        AI ACTIVE
                      </div>
                    )}
                    {/* Tactical corner brackets */}
                    <div className="absolute top-1 left-1 w-3 h-3 border-t border-l border-cyan-500/30" />
                    <div className="absolute top-1 right-1 w-3 h-3 border-t border-r border-cyan-500/30" />
                    <div className="absolute bottom-1 left-1 w-3 h-3 border-b border-l border-cyan-500/30" />
                    <div className="absolute bottom-1 right-1 w-3 h-3 border-b border-r border-cyan-500/30" />
                  </div>

                  {/* Metadata */}
                  <div className="p-3">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="text-sm font-bold text-white">{feed.name}</p>
                        <p className="text-[10px] text-slate-500 font-mono">{feed.feed_type}</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-1 mb-3">
                      {[
                        ["Resolution", feed.resolution ?? "—"],
                        ["FPS", String(feed.fps ?? "—")],
                        ["Location", feed.location_name ?? "—"],
                        ["Zone", feed.zone_id?.slice(0, 8) ?? "—"],
                      ].map(([label, value]) => (
                        <div key={label} className="text-[10px] font-mono">
                          <span className="text-slate-600">{label}: </span>
                          <span className="text-slate-400">{value}</span>
                        </div>
                      ))}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-1.5">
                      <button
                        onClick={() => handleToggleAI(feed.id)}
                        className={`flex items-center gap-1 px-2 py-1 rounded border text-[10px] font-bold transition-colors ${
                          feed.ai_processing_enabled
                            ? "bg-yellow-900/20 border-yellow-500/30 text-yellow-400 hover:bg-yellow-900/40"
                            : "bg-emerald-900/20 border-emerald-500/30 text-emerald-400 hover:bg-emerald-900/40"
                        }`}
                      >
                        {feed.ai_processing_enabled ? <Pause size={10} /> : <Play size={10} />}
                        {feed.ai_processing_enabled ? "Pause AI" : "Start AI"}
                      </button>
                      <button
                        onClick={() => handleDelete(feed.id)}
                        className="flex items-center gap-1 px-2 py-1 bg-red-900/20 border border-red-500/30 rounded text-[10px] text-red-400 hover:bg-red-900/40 transition-colors ml-auto"
                      >
                        <Trash2 size={10} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Feed Drawer */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-end">
          <div className="w-96 h-full bg-[#0d1117] border-l border-blue-500/20 flex flex-col overflow-hidden">
            <div className="p-4 border-b border-blue-500/10 flex items-center justify-between">
              <h3 className="text-sm font-bold text-white">Add Video Feed</h3>
              <button onClick={() => { setShowAddForm(false); setTestResult(null); }} className="text-slate-500 hover:text-white">✕</button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {[
                { label: "Feed Name *", key: "name", type: "text", placeholder: "Camera 01 - Gate A" },
                { label: "RTSP URL *", key: "rtsp_url", type: "text", placeholder: "rtsp://user:pass@192.168.1.100/stream" },
                { label: "Location Name", key: "location_name", type: "text", placeholder: "Main Gate" },
              ].map(({ label, key, type, placeholder }) => (
                <div key={key}>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">{label}</label>
                  <input
                    type={type}
                    value={String((form as Record<string, unknown>)[key] ?? "")}
                    onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))}
                    placeholder={placeholder}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500/50"
                  />
                </div>
              ))}

              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Feed Type</label>
                <select
                  value={form.feed_type}
                  onChange={(e) => setForm((prev) => ({ ...prev, feed_type: e.target.value }))}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500/50"
                >
                  {["FIXED_CAMERA", "DRONE", "BODY_CAM", "LEGACY_CCTV", "IP_CAMERA"].map((t) => (
                    <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>

              {/* Test connection */}
              <div>
                <button
                  onClick={handleTestConnection}
                  disabled={!form.rtsp_url || testing}
                  className="w-full flex items-center justify-center gap-2 py-2 bg-slate-800 border border-slate-700 rounded text-xs text-slate-400 hover:border-slate-500 disabled:opacity-50 transition-colors"
                >
                  {testing ? <RefreshCw size={12} className="animate-spin" /> : <Wifi size={12} />}
                  {testing ? "Testing..." : "Test Connection"}
                </button>
                {testResult && (
                  <div className={`mt-2 flex items-center gap-2 text-xs px-3 py-2 rounded border ${
                    testResult.success
                      ? "bg-emerald-900/20 border-emerald-500/30 text-emerald-400"
                      : "bg-red-900/20 border-red-500/30 text-red-400"
                  }`}>
                    {testResult.success ? <CheckCircle size={12} /> : <XCircle size={12} />}
                    {testResult.message}
                  </div>
                )}
              </div>
            </div>

            <div className="p-4 border-t border-blue-500/10 flex gap-3">
              <button
                onClick={handleAddFeed}
                disabled={!form.name || !form.rtsp_url}
                className="flex-1 py-2.5 bg-cyan-500 hover:bg-cyan-400 disabled:bg-slate-700 disabled:cursor-not-allowed text-slate-900 font-bold rounded text-sm transition-all"
              >
                Save Feed
              </button>
              <button
                onClick={() => { setShowAddForm(false); setTestResult(null); }}
                className="px-4 py-2.5 border border-slate-700 rounded text-sm text-slate-400 hover:border-slate-500 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
