/**
 * WebcamPage — Live laptop camera with YOLO + face analysis
 *
 * Uses MJPEG <img> stream (fastest — single persistent HTTP connection, no polling overhead)
 * with a watchdog that auto-reconnects if the stream stalls.
 * Detection JSON is polled separately every 500ms.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Camera, CameraOff, Activity, User, AlertTriangle, RefreshCw, WifiOff,
} from "lucide-react";
import apiClient from "../services/api";

interface Detection {
  class: string;
  confidence: number;
  behaviour: string;
  threat: boolean;
  bbox: { x1: number; y1: number; x2: number; y2: number };
}

interface FaceResult {
  age: number;
  gender: string;
  emotion: string;
  behaviour: string;
  bbox: { x1: number; y1: number; x2: number; y2: number };
}

interface DetectionResult {
  frame_count: number;
  fps: number;
  started_at: string | null;
  detections: Detection[];
  faces: FaceResult[];
  timestamp: string;
}

const BEHAVIOUR_COLOURS: Record<string, string> = {
  ARMED_THREAT:     "text-red-400 bg-red-500/10 border-red-500/30",
  POTENTIAL_THREAT: "text-orange-400 bg-orange-500/10 border-orange-500/30",
  AGGRESSIVE:       "text-red-400 bg-red-500/10 border-red-500/30",
  FEARFUL:          "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
  DISTRESSED:       "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
  MONITORING:       "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  CALM:             "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  WORKING:          "text-cyan-400 bg-cyan-500/10 border-cyan-500/30",
  USING_PHONE:      "text-orange-300 bg-orange-500/10 border-orange-500/30",
  CARRYING_BAG:     "text-slate-300 bg-slate-500/10 border-slate-500/30",
  CARRYING_LUGGAGE: "text-slate-300 bg-slate-500/10 border-slate-500/30",
  CARRYING_OBJECT:  "text-slate-400 bg-slate-800/50 border-slate-700",
  SEATED:           "text-green-300 bg-green-500/10 border-green-500/30",
  VEHICLE_PRESENT:  "text-purple-400 bg-purple-500/10 border-purple-500/30",
  UNKNOWN:          "text-slate-500 bg-slate-800/50 border-slate-700",
};

function getBehaviourClass(b: string) {
  return BEHAVIOUR_COLOURS[b] ?? BEHAVIOUR_COLOURS.UNKNOWN;
}

// Build MJPEG stream URL with token in query param
function buildStreamUrl(): string {
  const token = localStorage.getItem("access_token") ?? "";
  return `/api/v1/webcam/stream?token=${encodeURIComponent(token)}&t=${Date.now()}`;
}

export function WebcamPage() {
  const [running, setRunning]         = useState(false);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState<string | null>(null);
  const [detections, setDetections]   = useState<DetectionResult | null>(null);
  const [streamOk, setStreamOk]       = useState(true);
  const [modelLoading, setModelLoading] = useState(false);
  const [streamUrl, setStreamUrl]     = useState<string>("");

  const imgRef      = useRef<HTMLImageElement>(null);
  const pollRef     = useRef<ReturnType<typeof setInterval> | null>(null);
  const watchdogRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastFrameTs = useRef<number>(0);
  const mountedRef  = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    // Check if already running on mount
    apiClient.get("/webcam/status").then(({ data }) => {
      if (data.running && mountedRef.current) {
        setRunning(true);
        setStreamUrl(buildStreamUrl());
      }
    }).catch(() => {});
    return () => {
      mountedRef.current = false;
      clearAllTimers();
    };
  }, []);

  const clearAllTimers = () => {
    if (pollRef.current)     clearInterval(pollRef.current);
    if (watchdogRef.current) clearInterval(watchdogRef.current);
  };

  // Reconnect MJPEG stream by changing the src URL (forces browser to re-open connection)
  const reconnectStream = useCallback(() => {
    if (!mountedRef.current || !running) return;
    setStreamUrl(buildStreamUrl());
    setStreamOk(true);
  }, [running]);

  // Watchdog: if no frame received for 8 seconds, reconnect
  const startWatchdog = useCallback(() => {
    if (watchdogRef.current) clearInterval(watchdogRef.current);
    lastFrameTs.current = Date.now();
    watchdogRef.current = setInterval(() => {
      if (!mountedRef.current) return;
      const age = Date.now() - lastFrameTs.current;
      if (age > 8000) {
        // Stream stalled — reconnect
        setStreamOk(false);
        reconnectStream();
      }
    }, 2000);
  }, [reconnectStream]);

  // Poll detection JSON every 500ms
  const startPoll = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      if (!mountedRef.current) return;
      try {
        const { data } = await apiClient.get<DetectionResult>("/webcam/detections");
        if (mountedRef.current) {
          setDetections(data);
          if (data.frame_count > 0) setModelLoading(false);
        }
      } catch { /* ignore — backend may be busy */ }
    }, 500);
  }, []);

  // Start everything when running becomes true
  useEffect(() => {
    if (running) {
      startWatchdog();
      startPoll();
    } else {
      clearAllTimers();
      setDetections(null);
      setStreamUrl("");
    }
    return clearAllTimers;
  }, [running, startWatchdog, startPoll]);

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    try {
      await apiClient.post("/webcam/start");
      setRunning(true);
      setModelLoading(true);
      setStreamUrl(buildStreamUrl());
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err.response?.data?.detail ?? "Failed to start webcam. Is another app using the camera?");
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await apiClient.post("/webcam/stop");
    } catch { /* ignore */ } finally {
      setRunning(false);
      setModelLoading(false);
      setLoading(false);
    }
  };

  const hasThreat = detections?.detections.some((d) => d.threat) ||
    detections?.faces.some((f) => ["AGGRESSIVE", "FEARFUL"].includes(f.behaviour));

  return (
    <div className="h-full flex flex-col overflow-hidden bg-[#05070a] text-white">
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-500/10 bg-[#0d1117]/60 shrink-0">
        <div className="flex items-center gap-3">
          <Camera size={18} className="text-cyan-400" />
          <span className="text-sm font-bold tracking-wider text-slate-200">LIVE WEBCAM DETECTION</span>

          {running && !modelLoading && streamOk && (
            <span className="flex items-center gap-1.5 text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              LIVE
            </span>
          )}
          {running && modelLoading && (
            <span className="flex items-center gap-1.5 text-[10px] font-mono text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 px-2 py-0.5 rounded-full">
              <RefreshCw size={9} className="animate-spin" />
              LOADING MODEL...
            </span>
          )}
          {running && !streamOk && (
            <span className="flex items-center gap-1.5 text-[10px] font-mono text-orange-400 bg-orange-500/10 border border-orange-500/20 px-2 py-0.5 rounded-full">
              <RefreshCw size={9} className="animate-spin" />
              RECONNECTING...
            </span>
          )}
          {hasThreat && (
            <span className="flex items-center gap-1.5 text-[10px] font-mono text-red-400 bg-red-500/10 border border-red-500/30 px-2 py-0.5 rounded-full animate-pulse">
              <AlertTriangle size={10} /> THREAT DETECTED
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {running && detections && !modelLoading && (
            <span className="text-xs font-mono text-slate-500">
              {detections.fps} FPS · Frame #{detections.frame_count}
            </span>
          )}
          {running ? (
            <button onClick={handleStop} disabled={loading}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 transition-colors disabled:opacity-50">
              <CameraOff size={13} /> STOP
            </button>
          ) : (
            <button onClick={handleStart} disabled={loading}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20 transition-colors disabled:opacity-50">
              {loading ? <RefreshCw size={13} className="animate-spin" /> : <Camera size={13} />}
              {loading ? "STARTING..." : "START CAMERA"}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mx-4 mt-3 flex items-center gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm shrink-0">
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {/* ── Main content ── */}
      <div className="flex-1 flex overflow-hidden">

        {/* Video */}
        <div className="flex-1 flex items-center justify-center p-4 overflow-hidden relative">
          {running ? (
            <div className="relative w-full h-full flex items-center justify-center">
              {/* MJPEG stream — single persistent connection, browser handles frame decoding */}
              {streamUrl && (
                <img
                  ref={imgRef}
                  src={streamUrl}
                  alt="Live webcam feed"
                  className="max-w-full max-h-full rounded-xl border object-contain"
                  style={{
                    borderColor: hasThreat ? "rgba(239,68,68,0.5)" : "rgba(0,242,255,0.2)",
                    boxShadow: hasThreat
                      ? "0 0 30px rgba(239,68,68,0.4)"
                      : "0 0 20px rgba(0,242,255,0.08)",
                  }}
                  onLoad={() => {
                    // Each MJPEG frame fires onLoad — update watchdog timestamp
                    lastFrameTs.current = Date.now();
                    setStreamOk(true);
                    setModelLoading(false);
                  }}
                  onError={() => {
                    setStreamOk(false);
                    // Auto-reconnect after 2s
                    setTimeout(() => {
                      if (mountedRef.current && running) reconnectStream();
                    }, 2000);
                  }}
                />
              )}

              {modelLoading && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[#05070a]/85 rounded-xl">
                  <RefreshCw size={32} className="text-cyan-400 animate-spin" />
                  <p className="text-sm font-mono text-cyan-400">Loading YOLO model...</p>
                  <p className="text-xs text-slate-500">This takes ~5s on first run</p>
                </div>
              )}

              {/* Corner markers */}
              <div className="absolute top-4 left-4 w-6 h-6 border-t-2 border-l-2 border-cyan-400/40 rounded-tl pointer-events-none" />
              <div className="absolute top-4 right-4 w-6 h-6 border-t-2 border-r-2 border-cyan-400/40 rounded-tr pointer-events-none" />
              <div className="absolute bottom-4 left-4 w-6 h-6 border-b-2 border-l-2 border-cyan-400/40 rounded-bl pointer-events-none" />
              <div className="absolute bottom-4 right-4 w-6 h-6 border-b-2 border-r-2 border-cyan-400/40 rounded-br pointer-events-none" />
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4 text-slate-600">
              <CameraOff size={64} />
              <p className="text-sm font-mono">Camera offline</p>
              <p className="text-xs text-slate-700">Click START CAMERA to begin detection</p>
            </div>
          )}
        </div>

        {/* Detection panel */}
        <div className="w-72 shrink-0 border-l border-blue-500/10 flex flex-col overflow-hidden">

          {/* Objects */}
          <div className="p-3 border-b border-blue-500/10">
            <div className="flex items-center gap-2 mb-2">
              <Activity size={13} className="text-cyan-400" />
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Objects ({detections?.detections.length ?? 0})
              </span>
            </div>
            <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
              {detections?.detections.length ? (
                detections.detections.map((d, i) => (
                  <div key={i}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg border text-[11px] font-mono ${getBehaviourClass(d.behaviour)}`}>
                    <div className="flex items-center gap-1.5">
                      {d.threat && <AlertTriangle size={10} className="text-red-400 shrink-0" />}
                      <span className="font-bold uppercase truncate max-w-[90px]">{d.class}</span>
                    </div>
                    <div className="flex flex-col items-end gap-0.5 shrink-0">
                      <span>{(d.confidence * 100).toFixed(0)}%</span>
                      <span className="text-[9px] opacity-70">{d.behaviour}</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-[10px] text-slate-600 text-center py-4">
                  {running && modelLoading ? "Waiting for model..." : "No objects detected"}
                </p>
              )}
            </div>
          </div>

          {/* Faces */}
          <div className="p-3 flex-1 overflow-hidden flex flex-col">
            <div className="flex items-center gap-2 mb-2">
              <User size={13} className="text-cyan-400" />
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Faces ({detections?.faces.length ?? 0})
              </span>
            </div>
            <div className="space-y-2 overflow-y-auto flex-1 pr-1">
              {detections?.faces.length ? (
                detections.faces.map((f, i) => (
                  <div key={i}
                    className={`px-2.5 py-2 rounded-lg border text-[11px] font-mono ${getBehaviourClass(f.behaviour)}`}>
                    <div className="flex justify-between mb-1">
                      <span className="font-bold">{f.gender}, ~{f.age}y</span>
                      <span className="uppercase text-[9px] opacity-80">{f.behaviour}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[9px] opacity-60">EMOTION:</span>
                      <span className="uppercase font-bold">{f.emotion}</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-[10px] text-slate-600 text-center py-4">
                  {running && modelLoading ? "Waiting for model..." : "No faces detected"}
                </p>
              )}
            </div>
          </div>

          {/* Stats */}
          <div className="p-3 border-t border-blue-500/10 space-y-1.5">
            {[
              { label: "Total Objects", value: detections?.detections.length ?? 0 },
              { label: "Faces Analysed", value: detections?.faces.length ?? 0 },
              { label: "Threats", value: detections?.detections.filter(d => d.threat).length ?? 0 },
              { label: "Stream FPS", value: detections?.fps ?? 0 },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between text-[10px] font-mono">
                <span className="text-slate-500 uppercase">{label}</span>
                <span className={label === "Threats" && Number(value) > 0 ? "text-red-400 font-bold" : "text-slate-300"}>
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
