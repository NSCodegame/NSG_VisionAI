/**
 * Reports Page — Phase 27.4
 *
 * Left: report list panel | Right: report editor/preview
 */

import { useState, useEffect } from "react";
import { FileText, Plus, Download, RefreshCw, CheckCircle, Clock, XCircle } from "lucide-react";
import { reportsService, type Report, type CreateReportRequest } from "../services/reportsService";

const REPORT_TYPES = [
  "INCIDENT_REPORT",
  "PERSON_REPORT",
  "ZONE_ACTIVITY",
  "OPERATION_SUMMARY",
  "FORENSIC_TIMELINE",
];

const CLASSIFICATIONS = ["RESTRICTED", "CONFIDENTIAL", "SECRET"];

const STATUS_ICON: Record<string, React.ReactNode> = {
  COMPLETED: <CheckCircle size={12} className="text-emerald-400" />,
  PENDING: <Clock size={12} className="text-yellow-400" />,
  FAILED: <XCircle size={12} className="text-red-400" />,
};

const CLASSIFICATION_COLORS: Record<string, string> = {
  RESTRICTED: "text-red-400 border-red-500/40",
  CONFIDENTIAL: "text-blue-400 border-blue-500/40",
  SECRET: "text-purple-400 border-purple-500/40",
};

export function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [selected, setSelected] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [showNewForm, setShowNewForm] = useState(false);
  const [generating, setGenerating] = useState(false);

  // New report form
  const [newTitle, setNewTitle] = useState("");
  const [newType, setNewType] = useState("INCIDENT_REPORT");
  const [newClassification, setNewClassification] = useState("RESTRICTED");
  const [newSummary, setNewSummary] = useState("");
  const [newNotes, setNewNotes] = useState("");

  const loadReports = async () => {
    setLoading(true);
    try {
      const data = await reportsService.list();
      if (data && data.length > 0) {
        setReports(data);
      } else {
        // Fall back to seed reports in demo mode
        const { SEED_REPORTS } = await import("../data/seedData");
        setReports(SEED_REPORTS as typeof data);
      }
    } catch {
      const { SEED_REPORTS } = await import("../data/seedData");
      setReports(SEED_REPORTS as Report[]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadReports(); }, []);

  const handleGenerate = async () => {
    if (!newTitle.trim()) return;
    setGenerating(true);
    try {
      const req: CreateReportRequest = {
        title: newTitle,
        report_type: newType,
        classification: newClassification,
        summary: newSummary || undefined,
        analyst_notes: newNotes || undefined,
      };
      const report = await reportsService.create(req);
      setReports((prev) => [report, ...prev]);
      setSelected(report);
      setShowNewForm(false);
      setNewTitle("");
      setNewSummary("");
      setNewNotes("");
    } catch (err) {
      console.error("Report generation failed:", err);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (reportId: string) => {
    try {
      const { download_url } = await reportsService.getDownloadUrl(reportId);
      window.open(download_url, "_blank");
    } catch (err) {
      console.error("Download failed:", err);
    }
  };

  return (
    <div className="h-full flex overflow-hidden">
      {/* Left: Report list */}
      <div className="w-80 shrink-0 border-r border-blue-500/10 flex flex-col overflow-hidden">
        <div className="p-3 border-b border-blue-500/10 flex items-center justify-between">
          <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">Reports</span>
          <div className="flex gap-1">
            <button
              onClick={loadReports}
              className="p-1.5 text-slate-500 hover:text-cyan-400 transition-colors"
            >
              <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            </button>
            <button
              onClick={() => setShowNewForm(true)}
              className="flex items-center gap-1 px-2 py-1 bg-cyan-500/20 border border-cyan-500/40 rounded text-[10px] text-cyan-400 hover:bg-cyan-500/30 transition-colors"
            >
              <Plus size={11} /> New
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-24 text-slate-600 text-xs">Loading...</div>
          ) : reports.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 gap-2">
              <FileText size={24} className="text-slate-700" />
              <p className="text-xs text-slate-600">No reports yet</p>
            </div>
          ) : (
            reports.map((report) => (
              <button
                key={report.id}
                onClick={() => setSelected(report)}
                className={`w-full text-left p-3 border-b border-blue-500/5 hover:bg-slate-800/30 transition-colors ${
                  selected?.id === report.id ? "bg-slate-800/50" : ""
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-slate-200 truncate">{report.title}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5 font-mono">
                      {report.report_type.replace(/_/g, " ")}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {STATUS_ICON[report.status]}
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className={`text-[9px] font-bold border px-1.5 py-0.5 rounded ${CLASSIFICATION_COLORS[report.classification] ?? ""}`}>
                    {report.classification}
                  </span>
                  <span className="text-[9px] text-slate-600 font-mono">
                    {report.generated_at ? new Date(report.generated_at).toLocaleDateString() : "—"}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Right: Editor / Preview */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {showNewForm ? (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-2xl mx-auto space-y-5">
              <h2 className="text-lg font-bold text-white">New Intelligence Report</h2>

              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Title *</label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="Report title..."
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/50"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Report Type</label>
                  <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/50"
                  >
                    {REPORT_TYPES.map((t) => (
                      <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Classification</label>
                  <select
                    value={newClassification}
                    onChange={(e) => setNewClassification(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/50"
                  >
                    {CLASSIFICATIONS.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Executive Summary</label>
                <textarea
                  value={newSummary}
                  onChange={(e) => setNewSummary(e.target.value)}
                  rows={4}
                  placeholder="Describe the incident or operation..."
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white resize-none focus:outline-none focus:border-cyan-500/50"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Analyst Notes</label>
                <textarea
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  rows={3}
                  placeholder="Additional analyst observations..."
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white resize-none focus:outline-none focus:border-cyan-500/50"
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleGenerate}
                  disabled={!newTitle.trim() || generating}
                  className="flex items-center gap-2 px-6 py-2.5 bg-cyan-500 hover:bg-cyan-400 disabled:bg-slate-700 disabled:cursor-not-allowed text-slate-900 font-bold rounded text-sm transition-all"
                >
                  {generating ? <RefreshCw size={14} className="animate-spin" /> : <FileText size={14} />}
                  {generating ? "Generating..." : "Generate PDF Report"}
                </button>
                <button
                  onClick={() => setShowNewForm(false)}
                  className="px-4 py-2.5 border border-slate-700 rounded text-sm text-slate-400 hover:border-slate-500 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        ) : selected ? (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-2xl mx-auto">
              {/* Report header */}
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h2 className="text-xl font-bold text-white">{selected.title}</h2>
                  <p className="text-sm text-slate-500 mt-1 font-mono">
                    {selected.report_type.replace(/_/g, " ")}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-bold border px-2 py-1 rounded ${CLASSIFICATION_COLORS[selected.classification] ?? ""}`}>
                    {selected.classification}
                  </span>
                  <div className="flex items-center gap-1">
                    {STATUS_ICON[selected.status]}
                    <span className="text-xs text-slate-400">{selected.status}</span>
                  </div>
                </div>
              </div>

              {/* Metadata */}
              <div className="bg-slate-900/60 border border-slate-700 rounded-lg p-4 space-y-2 mb-6">
                {[
                  ["Report ID", selected.id],
                  ["Generated", selected.generated_at ? new Date(selected.generated_at).toLocaleString() : "—"],
                  ["Status", selected.status],
                  ["Storage", selected.file_path ?? "Not stored"],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between text-xs">
                    <span className="text-slate-500 uppercase font-mono">{label}</span>
                    <span className="text-slate-300 font-mono text-right max-w-xs truncate">{value}</span>
                  </div>
                ))}
              </div>

              {/* Actions */}
              {selected.status === "COMPLETED" && (
                <button
                  onClick={() => handleDownload(selected.id)}
                  className="flex items-center gap-2 px-5 py-2.5 bg-emerald-900/30 border border-emerald-500/40 rounded text-sm text-emerald-400 hover:bg-emerald-900/50 transition-colors"
                >
                  <Download size={14} /> Download PDF
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <FileText size={48} className="text-slate-700 mx-auto mb-4" />
              <p className="text-slate-500 text-sm">Select a report or create a new one</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
