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
import { useSeedData } from "../data/useSeedData";
import { SEED_TRACKED_PERSONS, SEED_ANALYTICS_SUMMARY } from "../data/seedData";

export function DashboardPage() {
  const { isConnected } = useAlertStream();
  const { alerts, unreadCount } = useAlertStore();
  const { feeds, setFeeds } = useFeedStore();

  // Inject seed data when backend is unavailable
  useSeedData();

  // Load initial data
  useEffect(() => {
    alertService.list({ status: "ACTIVE", limit: 50 })
      .then((res) => {
        if (res.alerts?.length > 0) useAlertStore.getState().setAlerts(res.alerts);
      })
      .catch(() => {});

    feedService.list()
      .then((feeds) => {
        if (Array.isArray(feeds) && feeds.length > 0) setFeeds(feeds as any);
      })
      .catch(() => {});
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
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {SEED_TRACKED_PERSONS.map((person) => (
              <div
                key={person.id}
                className={`bg-slate-900/60 border rounded-lg p-2.5 ${
                  person.watchlist_match_id ? "border-red-500/30" : "border-slate-700"
                }`}
              >
                <div className="flex items-start justify-between gap-1 mb-1">
                  <p className="text-[11px] font-bold text-slate-200 leading-tight">{person.name}</p>
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0 ${
                    person.label === "SUSPECT"
                      ? "bg-red-900/40 text-red-400 border border-red-500/30"
                      : "bg-slate-800 text-slate-400 border border-slate-600"
                  }`}>
                    {person.label}
                  </span>
                </div>
                <div className="text-[9px] font-mono text-slate-500 space-y-0.5">
                  <p>TRK: {person.track_id}</p>
                  <p>CAM: {person.feed_name}</p>
                  <p className="text-cyan-400/70">CONF: {(person.confidence * 100).toFixed(0)}%</p>
                </div>
              </div>
            ))}
          </div>
          {/* Quick stats */}
          <div className="p-3 border-t border-blue-500/10 space-y-2">
            {[
              { label: "Total Tracked", value: String(SEED_TRACKED_PERSONS.length) },
              { label: "Watchlist Matches", value: String(SEED_TRACKED_PERSONS.filter((p) => p.watchlist_match_id).length) },
              { label: "Zone Breaches Today", value: String(SEED_ANALYTICS_SUMMARY.zone_breaches) },
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
