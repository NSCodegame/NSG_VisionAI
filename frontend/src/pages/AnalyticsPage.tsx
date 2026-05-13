/**
 * Analytics Page — Phase 28.1
 *
 * Dashboard grid with metric cards, charts (Recharts), and zone heatmap.
 */

import { useState, useEffect } from "react";
import { RefreshCw, TrendingUp, AlertTriangle, Users, Eye, Target, Clock } from "lucide-react";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { analyticsService, type AnalyticsSummary, type TimelineBucket, type AlertDistributionItem } from "../services/analyticsService";

const PRIORITY_COLORS: Record<string, string> = {
  P1_CRITICAL: "#ef4444",
  P2_HIGH: "#f97316",
  P3_MEDIUM: "#eab308",
  P4_LOW: "#3b82f6",
};

const PIE_COLORS = ["#ef4444", "#f97316", "#eab308", "#3b82f6", "#8b5cf6", "#06b6d4", "#10b981"];

function MetricCard({
  label, value, sub, icon: Icon, color = "text-cyan-400",
}: {
  label: string; value: string | number; sub?: string;
  icon: React.ElementType; color?: string;
}) {
  return (
    <div className="bg-slate-900/60 border border-slate-700 rounded-lg p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
          {sub && <p className="text-[10px] text-slate-600 mt-0.5">{sub}</p>}
        </div>
        <Icon size={20} className={`${color} opacity-60`} />
      </div>
    </div>
  );
}

export function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [timeline, setTimeline] = useState<TimelineBucket[]>([]);
  const [distribution, setDistribution] = useState<AlertDistributionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  const load = async () => {
    setLoading(true);
    try {
      const now = new Date();
      const from = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
      const fromStr = from.toISOString();
      const toStr = now.toISOString();

      const [s, t, d] = await Promise.all([
        analyticsService.getSummary(fromStr, toStr),
        analyticsService.getAlertsTimeline(fromStr, toStr, days <= 2 ? "hour" : "day"),
        analyticsService.getAlertDistribution(fromStr, toStr),
      ]);

      // Use seed data when API returns empty (demo / no-DB mode)
      const seed = await import("../data/seedData");
      setSummary(s?.total_alerts != null ? s : seed.SEED_ANALYTICS_SUMMARY as typeof s);
      setTimeline(t?.length > 0 ? t : seed.SEED_ANALYTICS_TIMELINE as typeof t);
      setDistribution(d?.length > 0 ? d : seed.SEED_ANALYTICS_DISTRIBUTION as typeof d);
    } catch {
      const seed = await import("../data/seedData");
      setSummary(seed.SEED_ANALYTICS_SUMMARY as typeof summary);
      setTimeline(seed.SEED_ANALYTICS_TIMELINE as typeof timeline);
      setDistribution(seed.SEED_ANALYTICS_DISTRIBUTION as typeof distribution);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [days]);

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-white">Mission Analytics</h2>
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            {[1, 7, 30].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                  days === d
                    ? "bg-cyan-500/20 border border-cyan-500/40 text-cyan-400"
                    : "border border-slate-700 text-slate-500 hover:border-slate-500"
                }`}
              >
                {d === 1 ? "24h" : `${d}d`}
              </button>
            ))}
          </div>
          <button
            onClick={load}
            className="p-2 text-slate-500 hover:text-cyan-400 transition-colors"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Metric cards */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          <MetricCard
            label="Total Alerts" value={summary.total_alerts}
            icon={AlertTriangle} color="text-red-400"
          />
          <MetricCard
            label="P1 Critical" value={summary.alerts_by_priority?.P1_CRITICAL ?? 0}
            icon={AlertTriangle} color="text-red-500"
          />
          <MetricCard
            label="Watchlist Matches" value={summary.watchlist_matches}
            icon={Target} color="text-orange-400"
          />
          <MetricCard
            label="Zone Breaches" value={summary.zone_breaches}
            icon={Eye} color="text-yellow-400"
          />
          <MetricCard
            label="Persons Tracked" value={summary.persons_tracked}
            icon={Users} color="text-blue-400"
          />
          <MetricCard
            label="False Positive Rate"
            value={`${summary.false_positive_rate}%`}
            sub={`${summary.false_positives} total`}
            icon={TrendingUp}
            color={summary.false_positive_rate > 20 ? "text-red-400" : "text-emerald-400"}
          />
        </div>
      )}

      {/* Charts row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Alerts timeline */}
        <div className="xl:col-span-2 bg-slate-900/60 border border-slate-700 rounded-lg p-4">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">
            Alerts Over Time
          </h3>
          {timeline.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="timestamp"
                  tick={{ fontSize: 9, fill: "#64748b" }}
                  tickFormatter={(v) => {
                    const d = new Date(v);
                    return days <= 2 ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : d.toLocaleDateString([], { month: "short", day: "numeric" });
                  }}
                />
                <YAxis tick={{ fontSize: 9, fill: "#64748b" }} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 11 }}
                  labelStyle={{ color: "#94a3b8" }}
                />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                {Object.entries(PRIORITY_COLORS).map(([key, color]) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    stroke={color}
                    strokeWidth={1.5}
                    dot={false}
                    name={key.replace("_", " ")}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-slate-600 text-xs">
              {loading ? "Loading..." : "No data for selected period"}
            </div>
          )}
        </div>

        {/* Alert type distribution */}
        <div className="bg-slate-900/60 border border-slate-700 rounded-lg p-4">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">
            Alert Distribution
          </h3>
          {distribution.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={distribution}
                    dataKey="count"
                    nameKey="alert_type"
                    cx="50%"
                    cy="50%"
                    outerRadius={65}
                    innerRadius={35}
                  >
                    {distribution.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 11 }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1 mt-2">
                {distribution.slice(0, 5).map((item, i) => (
                  <div key={item.alert_type} className="flex items-center justify-between text-[10px]">
                    <div className="flex items-center gap-1.5">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ background: PIE_COLORS[i % PIE_COLORS.length] }}
                      />
                      <span className="text-slate-400">{item.alert_type.replace(/_/g, " ")}</span>
                    </div>
                    <span className="text-slate-300 font-mono">{item.percentage}%</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-48 flex items-center justify-center text-slate-600 text-xs">
              {loading ? "Loading..." : "No data"}
            </div>
          )}
        </div>
      </div>

      {/* Priority breakdown bar chart */}
      {summary && (
        <div className="bg-slate-900/60 border border-slate-700 rounded-lg p-4">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">
            Alerts by Priority
          </h3>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart
              data={Object.entries(summary.alerts_by_priority ?? {}).map(([k, v]) => ({
                priority: k.replace("_", " "),
                count: v,
                fill: PRIORITY_COLORS[k] ?? "#64748b",
              }))}
              layout="vertical"
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 9, fill: "#64748b" }} />
              <YAxis type="category" dataKey="priority" tick={{ fontSize: 9, fill: "#64748b" }} width={80} />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 11 }}
              />
              <Bar dataKey="count" radius={[0, 3, 3, 0]}>
                {Object.entries(summary.alerts_by_priority ?? {}).map(([k], i) => (
                  <Cell key={i} fill={PRIORITY_COLORS[k] ?? "#64748b"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
