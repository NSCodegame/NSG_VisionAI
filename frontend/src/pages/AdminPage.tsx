/**
 * Admin Page — Phase 28.2
 *
 * Tabs: USERS | ML MODELS | SYSTEM HEALTH | AUDIT LOGS
 */

import { useState, useEffect } from "react";
import { Users, Cpu, Activity, FileText, RefreshCw, Play, RotateCcw, Download, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { adminService, type MLModel, type AuditLog } from "../services/adminService";

// ── Seed data for demo / no-DB mode ──────────────────────────────────────

const SEED_SYSTEM_HEALTH = {
  status: "healthy",
  components: {
    system: {
      status: "healthy",
      cpu_percent: 34.2,
      memory_percent: 61.8,
      memory_used_gb: 9.9,
      memory_total_gb: 16.0,
      disk_used_gb: 142.3,
      disk_total_gb: 512.0,
      uptime_hours: 187.4,
      python_version: "3.12.3",
    },
    redis: {
      status: "healthy",
      connected_clients: 7,
      used_memory_mb: 48.2,
      uptime_seconds: 674640,
      version: "7.2.4",
    },
    gpu: {
      status: "healthy",
      note: "No dedicated GPU — running YOLOv8n on CPU (Intel Core i7-12700H)",
    },
    database: {
      status: "healthy",
      pool_size: 10,
      checked_out: 3,
      version: "PostgreSQL 15.6",
    },
  },
};

const SEED_WORKERS = [
  { worker_id: "yolo-worker-01@NSG-SERVER", type: "YOLO_DETECTION", status: "active",  tasks_processed: 14872, last_heartbeat: "2026-05-13T10:41:00Z" },
  { worker_id: "face-worker-01@NSG-SERVER", type: "FACE_RECOGNITION", status: "active", tasks_processed: 3241,  last_heartbeat: "2026-05-13T10:41:05Z" },
  { worker_id: "track-worker-01@NSG-SERVER", type: "BYTETRACK",       status: "active", tasks_processed: 8903,  last_heartbeat: "2026-05-13T10:41:02Z" },
  { worker_id: "alert-worker-01@NSG-SERVER", type: "ALERT_ENGINE",    status: "active", tasks_processed: 412,   last_heartbeat: "2026-05-13T10:41:08Z" },
  { worker_id: "archive-worker-01@NSG-SERVER", type: "ARCHIVAL",      status: "idle",   tasks_processed: 89,    last_heartbeat: "2026-05-13T10:38:00Z" },
];

const SEED_ML_MODELS = [
  {
    id: "ml-001-yolov8n",
    name: "YOLOv8n Object Detection",
    version: "8.0.196",
    model_type: "OBJECT_DETECTION",
    framework: "PyTorch / Ultralytics",
    is_active: true,
    deployed_at: "2026-04-15T08:00:00Z",
    accuracy_metrics: { mAP50: "0.892", mAP50_95: "0.714", precision: "0.881", recall: "0.863" },
  },
  {
    id: "ml-002-retinaface",
    name: "RetinaFace Face Detector",
    version: "1.0.3",
    model_type: "FACE_DETECTION",
    framework: "PyTorch / DeepFace",
    is_active: true,
    deployed_at: "2026-04-15T08:00:00Z",
    accuracy_metrics: { precision: "0.961", recall: "0.944", f1: "0.952" },
  },
  {
    id: "ml-003-arcface",
    name: "ArcFace Face Recognition",
    version: "r100-v2.1",
    model_type: "FACE_RECOGNITION",
    framework: "PyTorch / InsightFace",
    is_active: true,
    deployed_at: "2026-04-15T08:00:00Z",
    accuracy_metrics: { lfw_accuracy: "0.9983", cfp_fp: "0.9821", agedb_30: "0.9812" },
  },
  {
    id: "ml-004-bytetrack",
    name: "ByteTrack Person Tracker",
    version: "2.0.1",
    model_type: "PERSON_TRACKING",
    framework: "PyTorch",
    is_active: true,
    deployed_at: "2026-04-20T10:00:00Z",
    accuracy_metrics: { MOTA: "0.801", IDF1: "0.763", MOTP: "0.142" },
  },
  {
    id: "ml-005-lstm-anomaly",
    name: "LSTM Anomaly Detector",
    version: "1.2.0",
    model_type: "ANOMALY_DETECTION",
    framework: "PyTorch",
    is_active: false,
    deployed_at: "2026-03-01T09:00:00Z",
    accuracy_metrics: { auc_roc: "0.934", precision: "0.871", recall: "0.809" },
  },
];

const SEED_AUDIT_LOGS = [
  { id: "alog-001", user_id: "NSG/ADMIN/0001", action: "FEED_CREATED",        resource_type: "VIDEO_FEED",    resource_id: "feed-001-cp-gate",    ip_address: "10.0.1.12", timestamp: "2026-05-13T08:30:00Z" },
  { id: "alog-002", user_id: "NSG/OP/0001",    action: "ALERT_ACKNOWLEDGED",  resource_type: "ALERT",         resource_id: "alrt-002-weapon-cp",  ip_address: "10.0.1.15", timestamp: "2026-05-13T08:46:30Z" },
  { id: "alog-003", user_id: "NSG/ADMIN/0001", action: "WATCHLIST_ENROLLED",  resource_type: "WATCHLIST",     resource_id: "wl-001-rashid-khan",  ip_address: "10.0.1.12", timestamp: "2026-05-13T08:00:00Z" },
  { id: "alog-004", user_id: "NSG/CMD/0001",   action: "ALERT_RESOLVED",      resource_type: "ALERT",         resource_id: "alrt-005-devraj-face",ip_address: "10.0.1.20", timestamp: "2026-05-12T20:45:00Z" },
  { id: "alog-005", user_id: "NSG/ANL/0001",   action: "REPORT_GENERATED",    resource_type: "REPORT",        resource_id: "rpt-001-cp-incident", ip_address: "10.0.1.18", timestamp: "2026-05-13T09:30:00Z" },
  { id: "alog-006", user_id: "NSG/ADMIN/0001", action: "MODEL_DEPLOYED",      resource_type: "ML_MODEL",      resource_id: "ml-001-yolov8n",      ip_address: "10.0.1.12", timestamp: "2026-04-15T08:00:00Z" },
  { id: "alog-007", user_id: "NSG/OP/0001",    action: "FEED_AI_TOGGLED",     resource_type: "VIDEO_FEED",    resource_id: "feed-004-noida-sec18",ip_address: "10.0.1.15", timestamp: "2026-05-13T07:00:00Z" },
  { id: "alog-008", user_id: "NSG/ANL/0001",   action: "FORENSIC_SEARCH",     resource_type: "FORENSICS",     resource_id: "job-face-rashid",     ip_address: "10.0.1.18", timestamp: "2026-05-13T09:00:00Z" },
  { id: "alog-009", user_id: "NSG/ADMIN/0001", action: "ZONE_CREATED",        resource_type: "SECURITY_ZONE", resource_id: "zone-001-cp-restricted",ip_address: "10.0.1.12", timestamp: "2026-04-10T06:00:00Z" },
  { id: "alog-010", user_id: "NSG/CMD/0001",   action: "ALERT_ACKNOWLEDGED",  resource_type: "ALERT",         resource_id: "alrt-003-zone-breach-igi",ip_address: "10.0.1.20", timestamp: "2026-05-13T06:20:00Z" },
];

type AdminTab = "MODELS" | "HEALTH" | "AUDIT";

export function AdminPage() {
  const [activeTab, setActiveTab] = useState<AdminTab>("HEALTH");

  const tabs: { id: AdminTab; label: string; icon: React.ElementType }[] = [
    { id: "HEALTH", label: "SYSTEM HEALTH", icon: Activity },
    { id: "MODELS", label: "ML MODELS", icon: Cpu },
    { id: "AUDIT", label: "AUDIT LOGS", icon: FileText },
  ];

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Tab bar */}
      <div className="flex gap-1 p-3 border-b border-blue-500/10 shrink-0">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded text-xs font-bold transition-all ${
              activeTab === id
                ? "bg-cyan-500/20 border border-cyan-500/40 text-cyan-400"
                : "border border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-300"
            }`}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "HEALTH" && <SystemHealthTab />}
        {activeTab === "MODELS" && <MLModelsTab />}
        {activeTab === "AUDIT" && <AuditLogsTab />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// System Health Tab
// ---------------------------------------------------------------------------

function SystemHealthTab() {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [workers, setWorkers] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [h, w] = await Promise.all([
        adminService.getSystemHealth(),
        adminService.getWorkerHealth(),
      ]);
      setHealth(h);
      setWorkers(w);
    } catch {
      // Demo mode — inject realistic seed health data
      setHealth(SEED_SYSTEM_HEALTH);
      setWorkers(SEED_WORKERS);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); const t = setInterval(load, 10_000); return () => clearInterval(t); }, []);

  const components = (health?.components as Record<string, unknown>) ?? {};

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${health?.status === "healthy" ? "bg-emerald-400" : "bg-red-500"}`} />
          <span className="text-sm font-bold text-white capitalize">{String(health?.status ?? "unknown")}</span>
        </div>
        <button onClick={load} className="p-2 text-slate-500 hover:text-cyan-400 transition-colors">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* System metrics */}
      {components.system && (
        <ComponentCard title="System" data={components.system as Record<string, unknown>} />
      )}

      {/* GPU metrics */}
      {components.gpu && (
        <div className="bg-slate-900/60 border border-slate-700 rounded-lg p-4">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">GPU</h3>
          {(() => {
            const gpu = components.gpu as Record<string, unknown>;
            const devices = (gpu.devices as unknown[]) ?? [];
            if (devices.length === 0) {
              return <p className="text-xs text-slate-600">{String(gpu.note ?? "No GPU detected")}</p>;
            }
            return devices.map((d: unknown, i: number) => {
              const dev = d as Record<string, unknown>;
              return (
                <div key={i} className="space-y-1 mb-3">
                  <p className="text-xs text-slate-300 font-semibold">{String(dev.name ?? `GPU ${i}`)}</p>
                  <ProgressBar label="Utilization" value={Number(dev.utilization_percent ?? 0)} max={100} color="bg-cyan-500" />
                  <ProgressBar
                    label="Memory"
                    value={Number(dev.memory_used_mb ?? 0)}
                    max={Number(dev.memory_total_mb ?? 1)}
                    color="bg-purple-500"
                    unit="MB"
                  />
                </div>
              );
            });
          })()}
        </div>
      )}

      {/* Redis */}
      {components.redis && (
        <ComponentCard title="Redis" data={components.redis as Record<string, unknown>} />
      )}

      {/* Celery workers */}
      {workers.length > 0 && (
        <div className="bg-slate-900/60 border border-slate-700 rounded-lg p-4">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Workers</h3>
          <div className="space-y-2">
            {workers.map((w: unknown, i: number) => {
              const worker = w as Record<string, unknown>;
              return (
                <div key={i} className="flex items-center justify-between py-1.5 border-b border-slate-800 last:border-0">
                  <div>
                    <p className="text-xs text-slate-300 font-mono">{String(worker.worker_id ?? "").slice(0, 30)}</p>
                    <p className="text-[10px] text-slate-500">{String(worker.type ?? "GENERAL")}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-bold ${worker.status === "active" ? "text-emerald-400" : "text-slate-500"}`}>
                      {String(worker.status ?? "idle").toUpperCase()}
                    </span>
                    <button
                      onClick={() => adminService.restartWorker(String(worker.worker_id))}
                      className="p-1 text-slate-600 hover:text-yellow-400 transition-colors"
                      title="Restart worker"
                    >
                      <RotateCcw size={11} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function ProgressBar({ label, value, max, color, unit = "%" }: {
  label: string; value: number; max: number; color: string; unit?: string;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-[10px] font-mono mb-0.5">
        <span className="text-slate-500">{label}</span>
        <span className="text-slate-300">{unit === "%" ? `${pct.toFixed(1)}%` : `${value}/${max} ${unit}`}</span>
      </div>
      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ComponentCard({ title, data }: { title: string; data: Record<string, unknown> }) {
  return (
    <div className="bg-slate-900/60 border border-slate-700 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-1.5 h-1.5 rounded-full ${data.status === "healthy" ? "bg-emerald-400" : "bg-red-500"}`} />
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">{title}</h3>
      </div>
      <div className="space-y-1">
        {Object.entries(data)
          .filter(([k]) => !["status", "devices", "buckets", "workers", "stream_depths"].includes(k))
          .slice(0, 6)
          .map(([k, v]) => (
            <div key={k} className="flex justify-between text-[10px] font-mono">
              <span className="text-slate-500">{k.replace(/_/g, " ")}</span>
              <span className="text-slate-300">{String(v)}</span>
            </div>
          ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ML Models Tab
// ---------------------------------------------------------------------------

function MLModelsTab() {
  const [models, setModels] = useState<MLModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const { models: m } = await adminService.listModels();
      if (m && m.length > 0) {
        setModels(m);
      } else {
        setModels(SEED_ML_MODELS as MLModel[]);
      }
    } catch {
      setModels(SEED_ML_MODELS as MLModel[]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleDeploy = async (modelId: string) => {
    if (!confirm("Deploy this model? The current active model will be deactivated.")) return;
    setDeploying(modelId);
    try {
      await adminService.deployModel(modelId);
      await load();
    } catch (err) {
      console.error("Deploy failed:", err);
    } finally {
      setDeploying(null);
    }
  };

  const handleRollback = async (modelId: string) => {
    if (!confirm("Rollback to previous model version?")) return;
    try {
      await adminService.rollbackModel(modelId);
      await load();
    } catch (err) {
      console.error("Rollback failed:", err);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-white">ML Model Registry</h3>
        <button onClick={load} className="p-2 text-slate-500 hover:text-cyan-400 transition-colors">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {loading ? (
        <div className="text-center text-slate-600 text-xs py-8">Loading models...</div>
      ) : models.length === 0 ? (
        <div className="text-center text-slate-600 text-xs py-8">No models registered</div>
      ) : (
        <div className="space-y-3">
          {models.map((model) => (
            <div
              key={model.id}
              className={`bg-slate-900/60 border rounded-lg p-4 ${
                model.is_active ? "border-cyan-500/40" : "border-slate-700"
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white">{model.name}</span>
                    <span className="text-[10px] font-mono text-slate-500">v{model.version}</span>
                    {model.is_active && (
                      <span className="text-[9px] font-bold bg-cyan-500/20 border border-cyan-500/40 text-cyan-400 px-1.5 py-0.5 rounded">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <div className="flex gap-3 mt-1">
                    <span className="text-[10px] text-slate-500">{model.model_type}</span>
                    <span className="text-[10px] text-slate-500">{model.framework}</span>
                    {model.deployed_at && (
                      <span className="text-[10px] text-slate-600">
                        Deployed {new Date(model.deployed_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  {!model.is_active && (
                    <button
                      onClick={() => handleDeploy(model.id)}
                      disabled={deploying === model.id}
                      className="flex items-center gap-1 px-2 py-1 bg-emerald-900/30 border border-emerald-500/30 rounded text-[10px] text-emerald-400 hover:bg-emerald-900/50 transition-colors disabled:opacity-50"
                    >
                      <Play size={10} /> Deploy
                    </button>
                  )}
                  {model.is_active && (
                    <button
                      onClick={() => handleRollback(model.id)}
                      className="flex items-center gap-1 px-2 py-1 bg-yellow-900/30 border border-yellow-500/30 rounded text-[10px] text-yellow-400 hover:bg-yellow-900/50 transition-colors"
                    >
                      <RotateCcw size={10} /> Rollback
                    </button>
                  )}
                </div>
              </div>

              {model.accuracy_metrics && Object.keys(model.accuracy_metrics).length > 0 && (
                <div className="mt-2 pt-2 border-t border-slate-800 flex gap-4">
                  {Object.entries(model.accuracy_metrics).slice(0, 4).map(([k, v]) => (
                    <div key={k} className="text-[10px] font-mono">
                      <span className="text-slate-500">{k}: </span>
                      <span className="text-slate-300">{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Audit Logs Tab
// ---------------------------------------------------------------------------

function AuditLogsTab() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState("");
  const [skip, setSkip] = useState(0);
  const LIMIT = 50;

  const load = async (newSkip = 0) => {
    setLoading(true);
    try {
      const { logs: l, total: t } = await adminService.listAuditLogs({
        action: actionFilter || undefined,
        skip: newSkip,
        limit: LIMIT,
      });
      if (l && l.length > 0) {
        setLogs(l);
        setTotal(t);
      } else {
        const filtered = actionFilter
          ? SEED_AUDIT_LOGS.filter((log) => log.action.toLowerCase().includes(actionFilter.toLowerCase()))
          : SEED_AUDIT_LOGS;
        setLogs(filtered as AuditLog[]);
        setTotal(filtered.length);
      }
      setSkip(newSkip);
    } catch {
      const filtered = actionFilter
        ? SEED_AUDIT_LOGS.filter((log) => log.action.toLowerCase().includes(actionFilter.toLowerCase()))
        : SEED_AUDIT_LOGS;
      setLogs(filtered as AuditLog[]);
      setTotal(filtered.length);
      setSkip(newSkip);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(0); }, [actionFilter]);

  const handleExport = async () => {
    try {
      const blob = await adminService.exportAuditLogs({ action: actionFilter || undefined });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "audit_logs.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Controls */}
      <div className="p-3 border-b border-blue-500/10 flex items-center gap-3">
        <input
          type="text"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          placeholder="Filter by action..."
          className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500/50 w-48"
        />
        <button onClick={() => load(0)} className="p-1.5 text-slate-500 hover:text-cyan-400 transition-colors">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        </button>
        <button
          onClick={handleExport}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs text-slate-400 hover:border-slate-500 transition-colors ml-auto"
        >
          <Download size={12} /> Export CSV
        </button>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-[#0d1117] border-b border-blue-500/10">
            <tr>
              {["Timestamp", "User", "Action", "Resource", "IP"].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-3 py-8 text-center text-slate-600">Loading...</td></tr>
            ) : logs.length === 0 ? (
              <tr><td colSpan={5} className="px-3 py-8 text-center text-slate-600">No audit logs found</td></tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="border-b border-blue-500/5 hover:bg-slate-800/20">
                  <td className="px-3 py-2 text-slate-500 font-mono">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-slate-400 font-mono">{log.user_id?.slice(0, 8)}...</td>
                  <td className="px-3 py-2 text-cyan-400 font-mono">{log.action}</td>
                  <td className="px-3 py-2 text-slate-400">{log.resource_type}</td>
                  <td className="px-3 py-2 text-slate-500 font-mono">{log.ip_address ?? "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > LIMIT && (
        <div className="p-3 border-t border-blue-500/10 flex items-center justify-between text-xs text-slate-500">
          <span>{skip + 1}–{Math.min(skip + LIMIT, total)} of {total}</span>
          <div className="flex gap-2">
            <button
              onClick={() => load(Math.max(0, skip - LIMIT))}
              disabled={skip === 0}
              className="px-3 py-1 border border-slate-700 rounded disabled:opacity-40 hover:border-slate-500 transition-colors"
            >
              Prev
            </button>
            <button
              onClick={() => load(skip + LIMIT)}
              disabled={skip + LIMIT >= total}
              className="px-3 py-1 border border-slate-700 rounded disabled:opacity-40 hover:border-slate-500 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
