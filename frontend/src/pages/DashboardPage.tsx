/**
 * Dashboard Page — Phase 25.5
 *
 * Fixed full-viewport layout: Alert panel (left) | Video grid (centre) | Tracked persons (right)
 */

import { useEffect } from "react";
import { VideoGrid } from "../components/VideoGrid";
import { AlertInbox } from "../components/AlertInbox";
import { useAlertStream } from "../hooks/useAlertStream";
import { useAlertStore, useFeedStore } from "../stores";
import { alertService } from "../services/alertService";
import { feedService } from "../services/feedService";
import { Activity, Users, Radio } from "lucide-react";

export function DashboardPage() {
  const { isConnected } = useAlertStream();
  const { alerts, unreadCount } = useAlertStore();
  const { feeds, setFeeds } = useFeedStore();

  // Load initial data
  useEffect(() => {
    alertService.list({ status: "ACTIVE", limit: 50 })
      .then((res) => {
        useAlertStore.getState().setAlerts(res.alerts ?? []);
      })
      .catch(() => {
        // DB not available — start with empty alerts, WebSocket will populate
        useAlertStore.getState().setAlerts([]);
      });

    feedService.list()
      .then((feeds) => setFeeds(Array.isArray(feeds) ? feeds : []))
      .catch(() => setFeeds([]));
  }, [setFeeds]);

  const activeFeeds = feeds.filter((f) => f.status === "ACTIVE").length;
  const criticalAlerts = alerts.filter((a) => a.priority === "P1_CRITICAL" && a.status === "ACTIVE").length;

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Status bar */}
      <div className="flex items-center gap-6 px-4 py-2 border-b border-blue-500/10 bg-[#0d1117]/60 text-xs font-mono shrink-0">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-emerald-400" : "bg-red-500"}`} />
          <span className="text-slate-500">{isConnected ? "LIVE" : "RECONNECTING"}</span>
        </div>
        <div className="flex items-center gap-2 text-slate-500">
          <Radio size={12} className="text-cyan-400" />
          <span>{activeFeeds} ACTIVE FEEDS</span>
        </div>
        <div className="flex items-center gap-2 text-slate-500">
          <Activity size={12} className={criticalAlerts > 0 ? "text-red-400" : "text-slate-600"} />
          <span className={criticalAlerts > 0 ? "text-red-400 font-bold" : ""}>
            {unreadCount} UNACKNOWLEDGED
          </span>
        </div>
      </div>

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Alert panel */}
        <div className="w-80 shrink-0 border-r border-blue-500/10 overflow-hidden flex flex-col">
          <AlertInbox />
        </div>

        {/* Centre: Video grid */}
        <div className="flex-1 overflow-hidden p-3">
          <VideoGrid />
        </div>

        {/* Right: Tracked persons summary */}
        <div className="w-64 shrink-0 border-l border-blue-500/10 overflow-hidden flex flex-col">
          <div className="p-3 border-b border-blue-500/10">
            <div className="flex items-center gap-2">
              <Users size={14} className="text-cyan-400" />
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Tracked Persons
              </span>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            <p className="text-xs text-slate-600 text-center mt-8">
              No active tracks
            </p>
          </div>
          {/* Quick stats */}
          <div className="p-3 border-t border-blue-500/10 space-y-2">
            {[
              { label: "Total Tracked", value: "0" },
              { label: "Watchlist Matches", value: "0" },
              { label: "Zone Breaches Today", value: "0" },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between text-[10px] font-mono">
                <span className="text-slate-500 uppercase">{label}</span>
                <span className="text-slate-300">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
