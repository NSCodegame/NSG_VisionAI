/**
 * VideoPlayer — Real MJPEG stream player
 *
 * Connects to /api/v1/streams/{feedId}/mjpeg for live RTSP feeds.
 * Falls back to a tactical placeholder when stream is unavailable.
 * Shows connection state, FPS, AI status, and stream health.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Maximize2, Minimize2, Pause, Play, AlertTriangle,
  Wifi, WifiOff, Activity, Cpu, RefreshCw,
} from "lucide-react";

interface VideoPlayerProps {
  feedId: string;
  feedName: string;
  /** "ACTIVE" | "OFFLINE" | "DEGRADED" | "MAINTENANCE" | legacy "active" | "offline" | "alert" */
  status: string;
  aiEnabled?: boolean;
  location?: string;
  resolution?: string;
  fps?: number;
  /** If true, use the webcam MJPEG endpoint instead of the feed endpoint */
  isWebcam?: boolean;
}

const BASE = import.meta.env.VITE_API_URL ?? "/api/v1";

function getStreamUrl(feedId: string, isWebcam: boolean): string {
  const token = localStorage.getItem("access_token") ?? "";
  if (isWebcam) return `${BASE}/webcam/stream?token=${token}`;
  return `${BASE}/streams/${feedId}/mjpeg?token=${token}`;
}

function isActive(status: string) {
  return status === "ACTIVE" || status === "active";
}
function isOffline(status: string) {
  return status === "OFFLINE" || status === "offline";
}
function isAlert(status: string) {
  return status === "alert";
}
function isDegraded(status: string) {
  return status === "DEGRADED" || status === "degraded";
}

export const VideoPlayer = ({
  feedId,
  feedName,
  status,
  aiEnabled = false,
  location,
  resolution,
  fps,
  isWebcam = false,
}: VideoPlayerProps) => {
  const [streamState, setStreamState] = useState<"loading" | "live" | "error" | "paused">("loading");
  const [isHovered, setIsHovered] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [paused, setPaused] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const streamUrl = getStreamUrl(feedId, isWebcam);

  const startStream = useCallback(() => {
    if (!imgRef.current || isOffline(status) || paused) return;
    setStreamState("loading");
    // Setting src triggers the browser to open the MJPEG connection
    imgRef.current.src = streamUrl + `&_t=${Date.now()}`;
  }, [streamUrl, status, paused]);

  useEffect(() => {
    if (!isOffline(status) && !paused) {
      startStream();
    }
    return () => {
      if (retryTimer.current) clearTimeout(retryTimer.current);
      // Stop stream by clearing src
      if (imgRef.current) imgRef.current.src = "";
    };
  }, [feedId, status, paused]);

  const handleLoad = () => setStreamState("live");

  const handleError = () => {
    setStreamState("error");
    // Auto-retry with exponential backoff (max 30s)
    const delay = Math.min(2000 * Math.pow(1.5, retryCount), 30000);
    retryTimer.current = setTimeout(() => {
      setRetryCount((c) => c + 1);
      startStream();
    }, delay);
  };

  const togglePause = () => {
    setPaused((p) => {
      if (!p) {
        // Pausing — clear src to stop MJPEG connection
        if (imgRef.current) imgRef.current.src = "";
        setStreamState("paused");
      } else {
        // Resuming
        setRetryCount(0);
      }
      return !p;
    });
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  // Status colour
  const statusColor =
    isActive(status) && streamState === "live" ? "#10b981" :
    isAlert(status) ? "#ef4444" :
    isDegraded(status) ? "#f59e0b" :
    "#475569";

  const statusLabel =
    streamState === "loading" ? "CONNECTING" :
    streamState === "live"    ? (isAlert(status) ? "ALERT" : "LIVE") :
    streamState === "paused"  ? "PAUSED" :
    streamState === "error"   ? "RECONNECTING" :
    isOffline(status)         ? "OFFLINE" : "UNKNOWN";

  return (
    <div
      ref={containerRef}
      className="relative rounded-lg overflow-hidden group h-full"
      style={{
        background: "#05070a",
        border: `1px solid ${isAlert(status) ? "rgba(239,68,68,0.4)" : "rgba(59,130,246,0.12)"}`,
        boxShadow: isAlert(status) ? "0 0 20px rgba(239,68,68,0.15)" : "none",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* ── STREAM IMAGE (MJPEG) ── */}
      {!isOffline(status) && !paused ? (
        <img
          ref={imgRef}
          alt={feedName}
          onLoad={handleLoad}
          onError={handleError}
          style={{
            position: "absolute", inset: 0, width: "100%", height: "100%",
            objectFit: "cover",
            opacity: streamState === "live" ? 1 : 0,
            transition: "opacity 0.3s ease",
          }}
        />
      ) : null}

      {/* ── PLACEHOLDER (offline / loading / error) ── */}
      {(isOffline(status) || streamState !== "live") && (
        <div style={{
          position: "absolute", inset: 0, display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: 8,
          background: "linear-gradient(135deg,#05070a,#0a1020)",
        }}>
          {/* Tactical grid overlay */}
          <div style={{
            position: "absolute", inset: 0, opacity: 0.15,
            backgroundImage: "linear-gradient(rgba(0,242,255,0.3) 1px,transparent 1px),linear-gradient(90deg,rgba(0,242,255,0.3) 1px,transparent 1px)",
            backgroundSize: "20px 20px",
          }} />

          {isOffline(status) ? (
            <>
              <WifiOff size={28} color="#475569" />
              <span style={{ fontSize: 10, fontFamily: "monospace", color: "#475569", letterSpacing: "0.15em" }}>FEED DISCONNECTED</span>
            </>
          ) : streamState === "loading" ? (
            <>
              <RefreshCw size={22} color="#00f2ff" style={{ animation: "spin 1s linear infinite" }} />
              <span style={{ fontSize: 10, fontFamily: "monospace", color: "#00f2ff", letterSpacing: "0.12em" }}>CONNECTING...</span>
            </>
          ) : streamState === "error" ? (
            <>
              <AlertTriangle size={24} color="#f59e0b" />
              <span style={{ fontSize: 10, fontFamily: "monospace", color: "#f59e0b", letterSpacing: "0.12em" }}>RECONNECTING ({retryCount})</span>
            </>
          ) : streamState === "paused" ? (
            <>
              <Pause size={24} color="#64748b" />
              <span style={{ fontSize: 10, fontFamily: "monospace", color: "#64748b", letterSpacing: "0.12em" }}>STREAM PAUSED</span>
            </>
          ) : null}
        </div>
      )}

      {/* ── TOP HUD ── */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, padding: "8px 10px",
        display: "flex", justifyContent: "space-between", alignItems: "flex-start",
        background: "linear-gradient(to bottom,rgba(0,0,0,0.7),transparent)",
        zIndex: 10,
      }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#e2e8f0", letterSpacing: "0.1em", textTransform: "uppercase" }}>{feedName}</div>
          {location && <div style={{ fontSize: 8, color: "#64748b", fontFamily: "monospace", marginTop: 1 }}>{location}</div>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          {/* AI badge */}
          {aiEnabled && (
            <div style={{ display: "flex", alignItems: "center", gap: 3, padding: "2px 6px", borderRadius: 4, background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)" }}>
              <Cpu size={8} color="#10b981" />
              <span style={{ fontSize: 8, color: "#10b981", fontFamily: "monospace", fontWeight: 700 }}>AI</span>
            </div>
          )}
          {/* Status dot */}
          <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "2px 6px", borderRadius: 4, background: "rgba(0,0,0,0.5)", border: `1px solid ${statusColor}40` }}>
            <div style={{ width: 5, height: 5, borderRadius: "50%", background: statusColor,
              boxShadow: streamState === "live" ? `0 0 6px ${statusColor}` : "none",
              animation: streamState === "live" && isActive(status) ? "hp-blink 2s ease-in-out infinite" : "none",
            }} />
            <span style={{ fontSize: 8, color: statusColor, fontFamily: "monospace", fontWeight: 700 }}>{statusLabel}</span>
          </div>
        </div>
      </div>

      {/* ── BOTTOM HUD ── */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0, padding: "6px 10px",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        background: "linear-gradient(to top,rgba(0,0,0,0.75),transparent)",
        zIndex: 10,
        opacity: isHovered ? 1 : 0.4,
        transition: "opacity 0.2s ease",
      }}>
        {/* Stream info */}
        <div style={{ display: "flex", gap: 8, fontSize: 8, fontFamily: "monospace", color: "#64748b" }}>
          {resolution && <span>{resolution}</span>}
          {fps && <span>{fps}fps</span>}
          {streamState === "live" && <span style={{ color: "#10b981" }}>●LIVE</span>}
        </div>

        {/* Controls */}
        <div style={{ display: "flex", gap: 4, opacity: isHovered ? 1 : 0, transition: "opacity 0.2s" }}>
          <button onClick={togglePause} style={{ padding: 4, background: "rgba(0,0,0,0.6)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 4, cursor: "pointer", color: "#94a3b8", transition: "color 0.15s" }}
            onMouseEnter={e => e.currentTarget.style.color = "#00f2ff"}
            onMouseLeave={e => e.currentTarget.style.color = "#94a3b8"}>
            {paused ? <Play size={11} /> : <Pause size={11} />}
          </button>
          <button onClick={toggleFullscreen} style={{ padding: 4, background: "rgba(0,0,0,0.6)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 4, cursor: "pointer", color: "#94a3b8", transition: "color 0.15s" }}
            onMouseEnter={e => e.currentTarget.style.color = "#00f2ff"}
            onMouseLeave={e => e.currentTarget.style.color = "#94a3b8"}>
            {isFullscreen ? <Minimize2 size={11} /> : <Maximize2 size={11} />}
          </button>
        </div>
      </div>

      {/* ── ALERT BORDER FLASH ── */}
      {isAlert(status) && (
        <div style={{
          position: "absolute", inset: 0, borderRadius: "inherit",
          border: "2px solid rgba(239,68,68,0.6)",
          animation: "hp-glow-pulse 1.5s ease-in-out infinite",
          pointerEvents: "none", zIndex: 5,
        }} />
      )}

      {/* ── TACTICAL CORNER BRACKETS ── */}
      {[
        { top: 4, left: 4, borderTop: "1px solid rgba(0,242,255,0.3)", borderLeft: "1px solid rgba(0,242,255,0.3)" },
        { top: 4, right: 4, borderTop: "1px solid rgba(0,242,255,0.3)", borderRight: "1px solid rgba(0,242,255,0.3)" },
        { bottom: 4, left: 4, borderBottom: "1px solid rgba(0,242,255,0.3)", borderLeft: "1px solid rgba(0,242,255,0.3)" },
        { bottom: 4, right: 4, borderBottom: "1px solid rgba(0,242,255,0.3)", borderRight: "1px solid rgba(0,242,255,0.3)" },
      ].map((s, i) => (
        <div key={i} style={{ position: "absolute", width: 10, height: 10, pointerEvents: "none", zIndex: 6, ...s }} />
      ))}
    </div>
  );
};
