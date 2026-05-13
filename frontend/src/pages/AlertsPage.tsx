/**
 * Alerts Management Page
 * Split view: alert table (left) | alert detail panel (right)
 * All actions work locally (optimistic update) — no DB required.
 */

import { useState, useEffect } from "react";
import { AlertTriangle, CheckCircle, XCircle, Filter, RefreshCw, Bell } from "lucide-react";
import { alertService, type AlertItem } from "../services/alertService";

const PRIORITY_COLORS: Record<string, string> = {
  P1_CRITICAL: "text-red-400 bg-red-900/30 border-red-500/40",
  P2_HIGH:     "text-orange-400 bg-orange-900/30 border-orange-500/40",
  P3_MEDIUM:   "text-yellow-400 bg-yellow-900/30 border-yellow-500/40",
  P4_LOW:      "text-blue-400 bg-blue-900/30 border-blue-500/40",
};

// ── Local state mutation helpers (instant, no DB needed) ──────────────────

function localAcknowledge(alert: AlertItem): AlertItem {
  return {
    ...alert,
    status: "ACKNOWLEDGED",
    acknowledged_at: new Date().toISOString(),
    acknowledged_by: "NSG/OP/0001",
  };
}

function localResolve(alert: AlertItem, notes: string): AlertItem {
  return {
    ...alert,
    status: "RESOLVED",
    resolved_at: new Date().toISOString(),
    resolution_notes: notes,
  };
}

function localFalsePositive(alert: AlertItem, reason: string): AlertItem {
  return {
    ...alert,
    status: "FALSE_POSITIVE",
    false_positive_reason: reason,
    resolved_at: new Date().toISOString(),
  };
}

export function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [selected, setSelected] = useState<AlertItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [toast, setToast] = useState<{ msg: string; type: "success" | "warn" } | null>(null);

  const showToast = (msg: string, type: "success" | "warn" = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  };

  const applyUpdate = (updated: AlertItem) => {
    setAlerts((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
    setSelected(updated);
  };

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const res = await alertService.list({ limit: 200 });
      if (res.alerts && res.alerts.length > 0) {
        setAlerts(res.alerts);
      } else {
        const { SEED_ALERTS } = await import("../data/seedData");
        setAlerts([...SEED_ALERTS] as AlertItem[]);
      }
    } catch {
      const { SEED_ALERTS } = await import("../data/seedData");
      setAlerts([...SEED_ALERTS] as AlertItem[]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAlerts(); }, []);

  const handleAcknowledge = (alertId: string) => {
    const alert = alerts.find((a) => a.id === alertId);
    if (!alert) return;
    const updated = localAcknowledge(alert);
    applyUpdate(updated);
    showToast("Alert acknowledged", "warn");
    alertService.acknowledge(alertId).then(applyUpdate).catch(() => {});
  };

  const handleResolve = (alertId: string) => {
    if (!resolutionNotes.trim()) {
      showToast("Enter resolution notes first", "warn");
      return;
    }
    const alert = alerts.find((a) => a.id === alertId);
    if (!alert) return;
    const updated = localResolve(alert, resolutionNotes);
    applyUpdate(updated);
    setResolutionNotes("");
    showToast("Alert resolved", "success");
    alertService.resolve(alertId, resolutionNotes).then(applyUpdate).catch(() => {});
  };

  const handleFalsePositive = (alertId: string) => {
    const reason = prompt("Reason for false positive:");
    if (!reason) return;
    const alert = alerts.find((a) => a.id === alertId);
    if (!alert) return;
    const updated = localFalsePositive(alert, reason);
    applyUpdate(updated);
    showToast("Marked as false positive", "success");
    alertService.markFalsePositive(alertId, reason).then(applyUpdate).catch(() => {});
  };

  // Apply filters client-side after local mutations
  const visibleAlerts = alerts.filter((a) => {
    if (priorityFilter !== "ALL" && a.priority !== priorityFilter) return false;
    if (statusFilter !== "ALL" && a.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="h-full flex overflow-hidden relative">
      {/* Toast */}
      {toast && (
        <div className={`absolute top-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-4 py-2 rounded-lg border text-xs font-bold shadow-xl ${
          toast.type === "success"
            ? "bg-emerald-900/95 border-emerald-500/50 text-emerald-300"
            : "bg-yellow-900/95 border-yellow-500/50 text-yellow-300"
        }`}>
          {toast.type === "success" ? <CheckCircle size={13} /> : <Bell size={13} />}
          {toast.msg}
        </div>
      )}

      {/* Left: Alert table */}
      <div className="flex-1 flex flex-col overflow-hidden border-r border-blue-500/10">
        {/* Filter bar */}
        <div className="p-4 border-b border-blue-500/10 flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-slate-500" />
            <span className="text-xs text-slate-500 uppercase font-mono">Priority:</span>
            {["ALL", "P1_CRITICAL", "P2_HIGH", "P3_MEDIUM", "P4_LOW"].map((p) => (
              <button
                key={p}
                onClick={() => setPriorityFilter(p)}
                className={`px-2 py-1 rounded text-[10px] font-bold border transition-all ${
                  priorityFilter === p
                    ? "bg-cyan-500/20 border-cyan-500/50 text-cyan-400"
                    : "border-slate-700 text-slate-500 hover:border-slate-500"
                }`}
              >
                {p === "ALL" ? "ALL" : p.replace("_", " ")}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 ml-4">
            <span className="text-xs text-slate-500 uppercase font-mono">Status:</span>
            {["ALL", "ACTIVE", "ACKNOWLEDGED", "RESOLVED"].map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-2 py-1 rounded text-[10px] font-bold border transition-all ${
                  statusFilter === s
                    ? "bg-cyan-500/20 border-cyan-500/50 text-cyan-400"
                    : "border-slate-700 text-slate-500 hover:border-slate-500"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
          <button onClick={loadAlerts} className="ml-auto p-2 text-slate-500 hover:text-cyan-400 transition-colors">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-32 text-slate-600 text-sm">Loading alerts...</div>
          ) : visibleAlerts.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-slate-600 text-sm">No alerts found</div>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-[#0d1117] border-b border-blue-500/10">
                <tr>
                  {["Priority", "Type", "Feed", "Confidence", "Triggered", "Status", "Actions"].map((h) => (
                    <th key={h} className="px-3 py-2 text-left text-[10px] font-bold text-slate-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleAlerts.map((alert) => (
                  <tr
                    key={alert.id}
                    onClick={() => setSelected(alert)}
                    className={`border-b border-blue-500/5 cursor-pointer transition-colors hover:bg-slate-800/30 ${
                      selected?.id === alert.id ? "bg-slate-800/50" : ""
                    } ${alert.priority === "P1_CRITICAL" && alert.status === "ACTIVE" ? "border-l-2 border-l-red-500" : ""}`}
                  >
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded border text-[10px] font-bold ${PRIORITY_COLORS[alert.priority] ?? ""}`}>
                        {alert.priority.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-300 font-mono">{alert.alert_type.replace(/_/g, " ")}</td>
                    <td className="px-3 py-2 text-slate-500 font-mono">{alert.feed_id?.slice(0, 8)}...</td>
                    <td className="px-3 py-2 text-slate-400">
                      {alert.confidence_score != null ? `${(alert.confidence_score * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-3 py-2 text-slate-500 font-mono">
                      {new Date(alert.triggered_at).toLocaleTimeString()}
                    </td>
                    <td className="px-3 py-2">
                      <span className={`text-[10px] font-bold ${
                        alert.status === "ACTIVE"          ? "text-red-400"     :
                        alert.status === "ACKNOWLEDGED"    ? "text-yellow-400"  :
                        alert.status === "RESOLVED"        ? "text-emerald-400" :
                        alert.status === "FALSE_POSITIVE"  ? "text-slate-500"   : "text-slate-500"
                      }`}>
                        {alert.status}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-1">
                        {alert.status === "ACTIVE" && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleAcknowledge(alert.id); }}
                            className="px-2 py-0.5 bg-yellow-900/30 border border-yellow-500/30 rounded text-[10px] text-yellow-400 hover:bg-yellow-900/50 transition-colors"
                          >
                            ACK
                          </button>
                        )}
                        <button
                          onClick={(e) => { e.stopPropagation(); setSelected(alert); }}
                          className="px-2 py-0.5 bg-blue-900/30 border border-blue-500/30 rounded text-[10px] text-blue-400 hover:bg-blue-900/50 transition-colors"
                        >
                          VIEW
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Right: Detail panel */}
      <div className="w-96 shrink-0 flex flex-col overflow-hidden">
        {selected ? (
          <>
            <div className="p-4 border-b border-blue-500/10">
              <div className="flex items-center gap-3 mb-2">
                <span className={`px-2 py-1 rounded border text-xs font-bold ${PRIORITY_COLORS[selected.priority] ?? ""}`}>
                  {selected.priority.replace("_", " ")}
                </span>
                <span className="text-sm font-bold text-white">{selected.alert_type.replace(/_/g, " ")}</span>
              </div>
              <p className="text-xs text-slate-500 font-mono">ID: {selected.id}</p>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Status badge */}
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-bold ${
                selected.status === "ACTIVE"          ? "bg-red-900/20 border-red-500/30 text-red-400"           :
                selected.status === "ACKNOWLEDGED"    ? "bg-yellow-900/20 border-yellow-500/30 text-yellow-400"  :
                selected.status === "RESOLVED"        ? "bg-emerald-900/20 border-emerald-500/30 text-emerald-400" :
                "bg-slate-800 border-slate-700 text-slate-400"
              }`}>
                {selected.status === "ACTIVE"        && <AlertTriangle size={13} />}
                {selected.status === "ACKNOWLEDGED"  && <Bell size={13} />}
                {selected.status === "RESOLVED"      && <CheckCircle size={13} />}
                {selected.status === "FALSE_POSITIVE"&& <XCircle size={13} />}
                {selected.status}
              </div>

              {/* Details */}
              <div className="space-y-2">
                {[
                  ["Feed",        selected.feed_id ?? "—"],
                  ["Zone",        selected.zone_id ?? "—"],
                  ["Confidence",  selected.confidence_score != null ? `${(selected.confidence_score * 100).toFixed(2)}%` : "—"],
                  ["Triggered",   new Date(selected.triggered_at).toLocaleString()],
                  ["Occurrences", String(selected.occurrence_count)],
                  ...(selected.acknowledged_at  ? [["Acknowledged", new Date(selected.acknowledged_at).toLocaleString()]] : []),
                  ...(selected.acknowledged_by  ? [["Ack. By",      selected.acknowledged_by]] : []),
                  ...(selected.resolved_at      ? [["Resolved",     new Date(selected.resolved_at).toLocaleString()]] : []),
                  ...(selected.resolution_notes ? [["Notes",        selected.resolution_notes]] : []),
                  ...(selected.false_positive_reason ? [["FP Reason", selected.false_positive_reason]] : []),
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between text-xs gap-2">
                    <span className="text-slate-500 uppercase font-mono shrink-0">{label}</span>
                    <span className="text-slate-300 font-mono text-right break-all">{value}</span>
                  </div>
                ))}
              </div>

              {/* Resolution notes */}
              {selected.status === "ACKNOWLEDGED" && (
                <div>
                  <label className="block text-xs text-slate-500 uppercase font-mono mb-1">
                    Resolution Notes *
                  </label>
                  <textarea
                    value={resolutionNotes}
                    onChange={(e) => setResolutionNotes(e.target.value)}
                    rows={3}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-xs text-white resize-none focus:outline-none focus:border-cyan-500/50"
                    placeholder="Describe resolution actions taken..."
                  />
                </div>
              )}
            </div>

            {/* Action buttons */}
            <div className="p-4 border-t border-blue-500/10 space-y-2">
              {selected.status === "ACTIVE" && (
                <button
                  onClick={() => handleAcknowledge(selected.id)}
                  className="w-full flex items-center justify-center gap-2 py-2.5 bg-yellow-900/30 border border-yellow-500/30 rounded text-xs text-yellow-400 hover:bg-yellow-900/50 transition-colors font-bold"
                >
                  <Bell size={14} /> Acknowledge Alert
                </button>
              )}
              {selected.status === "ACKNOWLEDGED" && (
                <button
                  onClick={() => handleResolve(selected.id)}
                  className="w-full flex items-center justify-center gap-2 py-2.5 bg-emerald-900/30 border border-emerald-500/30 rounded text-xs text-emerald-400 hover:bg-emerald-900/50 transition-colors font-bold"
                >
                  <CheckCircle size={14} /> Mark Resolved
                </button>
              )}
              {["ACTIVE", "ACKNOWLEDGED"].includes(selected.status) && (
                <button
                  onClick={() => handleFalsePositive(selected.id)}
                  className="w-full flex items-center justify-center gap-2 py-2 bg-slate-800 border border-slate-700 rounded text-xs text-slate-400 hover:bg-slate-700 transition-colors"
                >
                  <XCircle size={14} /> Mark False Positive
                </button>
              )}
              {["RESOLVED", "FALSE_POSITIVE"].includes(selected.status) && (
                <p className="text-center text-[10px] text-slate-600 font-mono py-1">
                  No further actions available
                </p>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <AlertTriangle size={32} className="text-slate-700 mx-auto mb-3" />
              <p className="text-xs text-slate-600">Select an alert to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
