/**
 * NSG VisionAI — World-Class Cinematic Homepage
 * Premium defense-tech landing page
 */
import { useState, useEffect, useRef } from "react";
import {
  Shield, Eye, Brain, Map, Bell, Search, FileText, BarChart2,
  Camera, Cpu, Lock, ChevronRight, Activity,
  Globe, Users,
  AlertTriangle, Crosshair, Server, Wifi, Target,
  TrendingUp, Database, Network, Layers, Monitor,
  ChevronDown,
} from "lucide-react";

interface HomePageProps { onEnter: () => void; }

/* ── Typing hook ─────────────────────────────────────────────────────────── */
function useTyping(text: string, speed = 55, delay = 600) {
  const [out, setOut] = useState("");
  useEffect(() => {
    const t0 = setTimeout(() => {
      let i = 0;
      const id = setInterval(() => {
        i++;
        setOut(text.slice(0, i));
        if (i >= text.length) clearInterval(id);
      }, speed);
      return () => clearInterval(id);
    }, delay);
    return () => clearTimeout(t0);
  }, [text, speed, delay]);
  return out;
}

/* ── Counter hook ────────────────────────────────────────────────────────── */
function useCounter(target: number, active: boolean, duration = 2000) {
  const [val, setVal] = useState(0);
  const ran = useRef(false);
  useEffect(() => {
    if (!active || ran.current) return;
    ran.current = true;
    let start: number | null = null;
    const raf = (ts: number) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      setVal(Math.floor((1 - Math.pow(1 - p, 3)) * target));
      if (p < 1) requestAnimationFrame(raf);
    };
    requestAnimationFrame(raf);
  }, [active, target, duration]);
  return val;
}

/* ── Intersection observer hook ─────────────────────────────────────────── */
function useOnScreen(threshold = 0.1) {
  const ref = useRef<HTMLDivElement>(null);
  const [vis, setVis] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setVis(true); obs.disconnect(); } },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, vis };
}

/* ── Metric card ─────────────────────────────────────────────────────────── */
function MetricCard({ Icon, label, value, suffix, color, delay = 0 }: {
  Icon: React.ElementType; label: string; value: number;
  suffix: string; color: string; delay?: number;
}) {
  const { ref, vis } = useOnScreen(0.2);
  const count = useCounter(value, vis);
  return (
    <div ref={ref} className="hp-card-hover"
      style={{
        padding: "28px 20px", borderRadius: 16, textAlign: "center",
        background: "rgba(10,16,30,0.9)", border: `1px solid ${color}30`,
        animationDelay: `${delay}ms`,
      }}
      onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = `0 16px 40px ${color}20`; (e.currentTarget as HTMLDivElement).style.borderColor = `${color}60`; }}
      onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = "none"; (e.currentTarget as HTMLDivElement).style.borderColor = `${color}30`; }}>
      <div style={{ marginBottom: 14, display: "flex", justifyContent: "center" }}>
        <div style={{ width: 48, height: 48, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", background: `${color}12`, border: `1px solid ${color}30` }}>
          <Icon size={22} color={color} />
        </div>
      </div>
      <div style={{ fontSize: 34, fontWeight: 900, fontFamily: "monospace", color, marginBottom: 6, letterSpacing: "-1px" }}>
        {count.toLocaleString()}{suffix}
      </div>
      <div style={{ fontSize: 10, color: "#64748b", letterSpacing: "0.14em", textTransform: "uppercase", fontFamily: "monospace" }}>{label}</div>
    </div>
  );
}

/* ── Section reveal wrapper ──────────────────────────────────────────────── */
function Reveal({ children, delay = 0, className = "" }: {
  children: React.ReactNode; delay?: number; className?: string;
}) {
  const { ref, vis } = useOnScreen(0.08);
  return (
    <div ref={ref} className={className} style={{
      opacity: vis ? 1 : 0,
      transform: vis ? "translateY(0)" : "translateY(32px)",
      transition: `opacity 0.75s ease ${delay}ms, transform 0.75s cubic-bezier(0.22,1,0.36,1) ${delay}ms`,
    }}>
      {children}
    </div>
  );
}

/* ── Section label ───────────────────────────────────────────────────────── */
function SLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 8,
      fontSize: 10, fontFamily: "monospace", letterSpacing: "0.2em",
      color: "rgba(0,242,255,0.65)", marginBottom: 16,
      padding: "5px 16px", borderRadius: 999,
      background: "rgba(0,242,255,0.06)", border: "1px solid rgba(0,242,255,0.18)",
    }}>{children}</div>
  );
}

/* ── Neon divider ────────────────────────────────────────────────────────── */
function NDivider() {
  return <div style={{ height: 1, background: "linear-gradient(90deg,transparent,rgba(0,242,255,0.18),transparent)", margin: "0" }} />;
}

/* ── DATA ────────────────────────────────────────────────────────────────── */
const METRICS = [
  { Icon: Camera,        label: "Active Camera Feeds",    value: 5,    suffix: "",     color: "#00f2ff", delay: 0   },
  { Icon: AlertTriangle, label: "Alerts This Week",       value: 47,   suffix: "",     color: "#ef4444", delay: 80  },
  { Icon: Users,         label: "Watchlist Matches",      value: 5,    suffix: "",     color: "#a855f7", delay: 160 },
  { Icon: Activity,      label: "AI Detection Accuracy",  value: 91,   suffix: ".4%",  color: "#22c55e", delay: 240 },
  { Icon: Crosshair,     label: "Persons Tracked",        value: 23,   suffix: "",     color: "#f97316", delay: 320 },
  { Icon: Globe,         label: "Security Zones — NCR",   value: 5,    suffix: "",     color: "#3b82f6", delay: 400 },
];

const MODULES = [
  { Icon: Monitor,   name: "Dashboard",    desc: "Live ops overview with real-time alert feed, tracked persons, and video grid",  color: "#00f2ff" },
  { Icon: Camera,    name: "Feeds",        desc: "MJPEG/HLS streams from RTSP cameras, drones, and body cams with AI overlay",    color: "#a855f7" },
  { Icon: Wifi,      name: "IP Cameras",   desc: "Auto-discover and configure IP cameras on your LAN with one-click setup",       color: "#22c55e" },
  { Icon: Eye,       name: "Webcam AI",    desc: "Live YOLOv8 detection + face analysis from laptop webcam in real-time",         color: "#f97316" },
  { Icon: Map,       name: "Tactical Map", desc: "Camera markers, security zone polygons, UAV tracking, and threat overlays",     color: "#3b82f6" },
  { Icon: Bell,      name: "Alerts",       desc: "P1-P4 priority alerts with acknowledge, resolve, and false-positive workflows",  color: "#ef4444" },
  { Icon: Search,    name: "Forensics",    desc: "Face search, object search, zone activity, and timeline reconstruction",        color: "#eab308" },
  { Icon: Users,     name: "Watchlist",    desc: "ArcFace biometric database with real-time matching across all camera feeds",    color: "#ec4899" },
  { Icon: FileText,  name: "Reports",      desc: "Auto-generated classified PDF intelligence reports with full incident detail",   color: "#06b6d4" },
  { Icon: BarChart2, name: "Analytics",    desc: "Alert trends, threat distribution, detection accuracy, and zone heatmaps",      color: "#8b5cf6" },
  { Icon: Cpu,       name: "Admin",        desc: "ML model registry, system health monitoring, audit logs, user management",      color: "#64748b" },
];

const AI_CAPS = [
  { Icon: Eye,        title: "Face Recognition",    desc: "ArcFace 512-dim embeddings. 99.83% LFW accuracy. Real-time watchlist matching across all feeds.",  color: "#00f2ff" },
  { Icon: Target,     title: "Object Detection",    desc: "YOLOv8n at 25-40 FPS on CPU. 80+ classes. Weapon, vehicle, bag, drone detection with remapping.",   color: "#a855f7" },
  { Icon: TrendingUp, title: "Anomaly Detection",   desc: "LSTM-based suspicious movement pattern recognition. AUC-ROC 0.934. Real-time scoring.",              color: "#22c55e" },
  { Icon: Users,      title: "Crowd Analysis",      desc: "Density estimation, loitering detection, crowd behaviour classification and alert generation.",      color: "#f97316" },
  { Icon: Brain,      title: "Behavioural AI",      desc: "Emotion mapping, threat behaviour classification, ARMED_THREAT and AGGRESSIVE detection.",           color: "#ef4444" },
  { Icon: Crosshair,  title: "Person Tracking",     desc: "ByteTrack cross-camera Re-ID. MOTA 80.1%. Persistent track IDs across all feeds and zones.",        color: "#eab308" },
];

const TIMELINE = [
  { time: "08:42:17", type: "WATCHLIST MATCH",  loc: "Connaught Place Gate A",    p: "P1", color: "#ef4444", note: "Rashid Ahmed Khan — 94% confidence match" },
  { time: "08:44:03", type: "WEAPON DETECTED",  loc: "Connaught Place Gate A",    p: "P1", color: "#ef4444", note: "Weapon-like object detected — 87% confidence" },
  { time: "06:12:44", type: "ZONE BREACH",      loc: "IGI Airport T3 Restricted", p: "P2", color: "#f97316", note: "Salma Qureshi — Airside access violation" },
  { time: "07:58:22", type: "LOITERING",        loc: "Rajiv Chowk Metro Gate 2",  p: "P3", color: "#eab308", note: "Farhan Siddiqui — 16 min loiter detected" },
  { time: "19:17:05", type: "WATCHLIST MATCH",  loc: "Cyber City DLF Tower",      p: "P2", color: "#f97316", note: "Devraj Menon — 88% confidence match" },
];

const INFRA = [
  { Icon: Lock,     title: "AES-256-GCM Encryption",  desc: "All RTSP URLs and video segments encrypted at rest. Zero plaintext storage." },
  { Icon: Server,   title: "Edge AI Processing",       desc: "On-premise inference — no cloud dependency. Air-gappable deployment." },
  { Icon: Network,  title: "WebSocket Gateway",        desc: "Sub-100ms real-time alert push to all connected operators simultaneously." },
  { Icon: Database, title: "TimescaleDB + pgvector",   desc: "Time-series detection events + 512-dim biometric embeddings at scale." },
  { Icon: Shield,   title: "JWT RS256 Authentication", desc: "8h access tokens, 30d refresh, RBAC role hierarchy with 4 clearance levels." },
  { Icon: Layers,   title: "Celery Task Queue",        desc: "Async ML pipeline — detection, face recognition, tracking, archival." },
];

const ROLES = [
  { role: "OPERATOR",  badge: "L1", color: "#3b82f6", items: ["Dashboard", "Live Feeds", "Webcam AI", "Tactical Map", "Alerts"] },
  { role: "ANALYST",   badge: "L2", color: "#10b981", items: ["All Operator", "Forensics", "Watchlist", "Reports", "Analytics"] },
  { role: "COMMANDER", badge: "L3", color: "#eab308", items: ["All Analyst", "Mission Control", "Priority Alerts", "Zone Mgmt"] },
  { role: "ADMIN",     badge: "L4", color: "#ef4444", items: ["Full Access", "ML Models", "Audit Logs", "User Mgmt", "Sys Health"] },
];

/* ── MAIN COMPONENT ──────────────────────────────────────────────────────── */
export function HomePage({ onEnter }: HomePageProps) {
  const typed = useTyping("Sarvatra Sarvottam Suraksha", 55, 800);
  const [tick, setTick] = useState(true);
  useEffect(() => {
    const id = setInterval(() => setTick(t => !t), 600);
    return () => clearInterval(id);
  }, []);

  const scrollTo = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="page-scroll" style={{ background: "#05070a", color: "#fff" }}>

      {/* ── FIXED BACKGROUND ── */}
      <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0,
        backgroundImage: "linear-gradient(rgba(0,242,255,0.022) 1px,transparent 1px),linear-gradient(90deg,rgba(0,242,255,0.022) 1px,transparent 1px)",
        backgroundSize: "52px 52px" }} />
      <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0,
        background: "radial-gradient(ellipse 90% 50% at 50% -5%,rgba(0,80,200,0.14) 0%,transparent 65%)" }} />

      {/* ── STICKY NAV ── */}
      <nav style={{ position: "sticky", top: 0, zIndex: 200, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "13px 40px", background: "rgba(5,7,10,0.92)", backdropFilter: "blur(20px)", borderBottom: "1px solid rgba(0,242,255,0.07)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 36, height: 36, borderRadius: 9, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,242,255,0.1)", border: "1px solid rgba(0,242,255,0.3)", boxShadow: "0 0 12px rgba(0,242,255,0.15)" }}>
            <Shield size={17} color="#00f2ff" />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 15, letterSpacing: "-0.3px" }}>NSG <span style={{ color: "#00f2ff" }}>VisionAI</span></div>
            <div style={{ fontSize: 9, fontFamily: "monospace", color: "#475569", letterSpacing: "0.16em" }}>TACTICAL INTELLIGENCE PLATFORM</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10, fontFamily: "monospace", color: "#475569", background: "rgba(15,23,42,0.8)", padding: "6px 14px", borderRadius: 999, border: "1px solid #1e293b" }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#22c55e", boxShadow: "0 0 6px #22c55e", animation: "hp-blink 2s ease-in-out infinite" }} />
          <span style={{ marginLeft: 4 }}>SECURE NODE: ALPHA-01</span>
          <span style={{ margin: "0 8px", color: "#1e293b" }}>|</span>
          <span style={{ color: "#22c55e" }}>ONLINE</span>
        </div>
        <button onClick={onEnter} style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 22px", borderRadius: 10, fontSize: 12, fontWeight: 700, cursor: "pointer", background: "linear-gradient(135deg,rgba(0,242,255,0.12),rgba(0,128,255,0.12))", border: "1px solid rgba(0,242,255,0.32)", color: "#00f2ff", transition: "all 0.2s" }}
          onMouseEnter={e => { e.currentTarget.style.background = "linear-gradient(135deg,rgba(0,242,255,0.22),rgba(0,128,255,0.22))"; e.currentTarget.style.boxShadow = "0 0 20px rgba(0,242,255,0.25)"; }}
          onMouseLeave={e => { e.currentTarget.style.background = "linear-gradient(135deg,rgba(0,242,255,0.12),rgba(0,128,255,0.12))"; e.currentTarget.style.boxShadow = "none"; }}>
          <Lock size={12} /> Sign In
        </button>
      </nav>

      {/* ══════════════════════════════════════════════════════════════════
          HERO
      ══════════════════════════════════════════════════════════════════ */}
      <section id="hero" style={{ position: "relative", zIndex: 1, minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "80px 24px 60px", overflow: "hidden" }}>

        {/* Scan line effect */}
        <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
          <div style={{ position: "absolute", left: 0, right: 0, height: 2, background: "linear-gradient(90deg,transparent,rgba(0,242,255,0.15),transparent)", animation: "hp-scan 6s linear infinite" }} />
        </div>

        {/* Corner HUD brackets */}
        {[
          { top: 24, left: 24, borderTop: "2px solid rgba(0,242,255,0.4)", borderLeft: "2px solid rgba(0,242,255,0.4)" },
          { top: 24, right: 24, borderTop: "2px solid rgba(0,242,255,0.4)", borderRight: "2px solid rgba(0,242,255,0.4)" },
          { bottom: 24, left: 24, borderBottom: "2px solid rgba(0,242,255,0.4)", borderLeft: "2px solid rgba(0,242,255,0.4)" },
          { bottom: 24, right: 24, borderBottom: "2px solid rgba(0,242,255,0.4)", borderRight: "2px solid rgba(0,242,255,0.4)" },
        ].map((s, i) => (
          <div key={i} style={{ position: "absolute", width: 24, height: 24, ...s }} />
        ))}

        {/* Restricted badge */}
        <div className="hp-fade-up" style={{ animationDelay: "0.1s", display: "inline-flex", alignItems: "center", gap: 8, padding: "5px 16px", borderRadius: 999, fontSize: 10, fontFamily: "monospace", letterSpacing: "0.12em", marginBottom: 32, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.28)", color: "#fca5a5" }}>
          <AlertTriangle size={10} /> RESTRICTED — AUTHORISED PERSONNEL ONLY <AlertTriangle size={10} />
        </div>

        {/* Main headline */}
        <h1 className="hp-fade-up" style={{ animationDelay: "0.2s", fontSize: "clamp(56px,9.5vw,104px)", fontWeight: 900, letterSpacing: "-4px", lineHeight: 0.95, marginBottom: 24, background: "linear-gradient(135deg,#ffffff 0%,#00f2ff 50%,#0066ff 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          NSG VisionAI
        </h1>

        {/* Tagline */}
        <div className="hp-fade-up" style={{ animationDelay: "0.35s", fontSize: "clamp(14px,2vw,20px)", fontFamily: "monospace", color: "rgba(0,242,255,0.8)", marginBottom: 16, minHeight: 32 }}>
          "{typed}"<span style={{ opacity: tick ? 1 : 0, transition: "opacity 0.1s", color: "#00f2ff" }}>_</span>
        </div>

        {/* Description */}
        <p className="hp-fade-up" style={{ animationDelay: "0.45s", color: "#94a3b8", fontSize: "clamp(13px,1.4vw,16px)", maxWidth: 600, lineHeight: 1.8, marginBottom: 48 }}>
          Defense-grade AI/ML surveillance platform for India's National Security Guard.
          Real-time video intelligence, biometric recognition, and tactical situational awareness
          — unified in a single secure command dashboard.
        </p>

        {/* CTAs */}
        <div className="hp-fade-up" style={{ animationDelay: "0.55s", display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center", marginBottom: 72 }}>
          <button onClick={onEnter} className="hp-glow" style={{ display: "flex", alignItems: "center", gap: 12, padding: "16px 40px", borderRadius: 12, fontWeight: 800, fontSize: 13, letterSpacing: "0.1em", cursor: "pointer", border: "none", background: "linear-gradient(135deg,#00f2ff,#0066ff)", color: "#05070a", transition: "all 0.2s" }}
            onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px) scale(1.02)"; }}
            onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0) scale(1)"; }}>
            <Shield size={16} /> ENTER PLATFORM <ChevronRight size={16} />
          </button>
          <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: 10, padding: "16px 32px", borderRadius: 12, fontWeight: 700, fontSize: 13, letterSpacing: "0.1em", textDecoration: "none", background: "rgba(15,25,50,0.7)", border: "1px solid rgba(0,242,255,0.2)", color: "#94a3b8", transition: "all 0.2s" }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(0,242,255,0.45)"; e.currentTarget.style.color = "#e2e8f0"; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(0,242,255,0.2)"; e.currentTarget.style.color = "#94a3b8"; }}>
            <FileText size={16} /> API DOCUMENTATION
          </a>
        </div>

        {/* Scroll cue */}
        <button onClick={() => scrollTo("metrics")} className="hp-bounce" style={{ background: "none", border: "none", cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: 8, color: "#334155", transition: "color 0.2s" }}
          onMouseEnter={e => e.currentTarget.style.color = "#64748b"}
          onMouseLeave={e => e.currentTarget.style.color = "#334155"}>
          <span style={{ fontSize: 10, fontFamily: "monospace", letterSpacing: "0.18em" }}>SCROLL TO EXPLORE</span>
          <ChevronDown size={18} />
        </button>
      </section>

      <NDivider />

      {/* ══════════════════════════════════════════════════════════════════
          METRICS
      ══════════════════════════════════════════════════════════════════ */}
      <section id="metrics" style={{ position: "relative", zIndex: 1, padding: "88px 24px", background: "rgba(0,242,255,0.012)" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <Reveal>
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <SLabel>LIVE SYSTEM METRICS</SLabel>
              <h2 style={{ fontSize: "clamp(26px,4vw,44px)", fontWeight: 900, marginBottom: 12, color: "#fff" }}>Platform at a Glance</h2>
              <p style={{ color: "#64748b", fontSize: 14, maxWidth: 480, margin: "0 auto", lineHeight: 1.7 }}>Real-time operational statistics from the NSG VisionAI tactical grid — updated continuously.</p>
            </div>
          </Reveal>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 18 }}>
            {METRICS.map(m => <MetricCard key={m.label} {...m} />)}
          </div>
        </div>
      </section>

      <NDivider />

      {/* ══════════════════════════════════════════════════════════════════
          MODULES
      ══════════════════════════════════════════════════════════════════ */}
      <section id="modules" style={{ position: "relative", zIndex: 1, padding: "96px 24px" }}>
        <div style={{ maxWidth: 1300, margin: "0 auto" }}>
          <Reveal>
            <div style={{ textAlign: "center", marginBottom: 60 }}>
              <SLabel>PLATFORM MODULES</SLabel>
              <h2 style={{ fontSize: "clamp(26px,4vw,44px)", fontWeight: 900, marginBottom: 12, color: "#fff" }}>Every Tool You Need</h2>
              <p style={{ color: "#64748b", fontSize: 14, maxWidth: 520, margin: "0 auto", lineHeight: 1.7 }}>11 purpose-built modules covering the full intelligence lifecycle — from ingestion to reporting.</p>
            </div>
          </Reveal>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(230px,1fr))", gap: 14 }}>
            {MODULES.map((m, i) => (
              <Reveal key={m.name} delay={i * 40}>
                <div className="hp-card-hover" style={{ padding: "22px 20px", borderRadius: 14, background: "rgba(10,16,30,0.88)", border: `1px solid ${m.color}20`, height: "100%" }}
                  onMouseEnter={e => { const el = e.currentTarget as HTMLDivElement; el.style.boxShadow = `0 16px 40px ${m.color}15`; el.style.borderColor = `${m.color}50`; }}
                  onMouseLeave={e => { const el = e.currentTarget as HTMLDivElement; el.style.boxShadow = "none"; el.style.borderColor = `${m.color}20`; }}>
                  <div style={{ width: 42, height: 42, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14, background: `${m.color}10`, border: `1px solid ${m.color}30` }}>
                    <m.Icon size={19} color={m.color} />
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8, color: "#e2e8f0" }}>{m.name}</div>
                  <div style={{ fontSize: 11, color: "#64748b", lineHeight: 1.65 }}>{m.desc}</div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <NDivider />

      {/* ══════════════════════════════════════════════════════════════════
          TACTICAL MAP PREVIEW
      ══════════════════════════════════════════════════════════════════ */}
      <section id="map" style={{ position: "relative", zIndex: 1, padding: "96px 24px", background: "rgba(0,0,0,0.38)" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <Reveal>
            <div style={{ textAlign: "center", marginBottom: 52 }}>
              <SLabel>TACTICAL OPERATIONS</SLabel>
              <h2 style={{ fontSize: "clamp(26px,4vw,44px)", fontWeight: 900, marginBottom: 12, color: "#fff" }}>Command-Level Situational Awareness</h2>
              <p style={{ color: "#64748b", fontSize: 14, maxWidth: 540, margin: "0 auto", lineHeight: 1.7 }}>Real-time tactical map with camera markers, security zone overlays, UAV tracking, and threat hotspots across Delhi NCR.</p>
            </div>
          </Reveal>
          <Reveal delay={150}>
            <div style={{ borderRadius: 20, overflow: "hidden", border: "1px solid rgba(0,242,255,0.14)", boxShadow: "0 0 80px rgba(0,242,255,0.06), 0 40px 80px rgba(0,0,0,0.4)", position: "relative", height: 440, background: "linear-gradient(135deg,#05070a 0%,#080f1e 50%,#05070a 100%)" }}>
              <div style={{ position: "absolute", inset: 0, backgroundImage: "linear-gradient(rgba(0,242,255,0.035) 1px,transparent 1px),linear-gradient(90deg,rgba(0,242,255,0.035) 1px,transparent 1px)", backgroundSize: "30px 30px" }} />
              {/* HUD panels */}
              <div style={{ position: "absolute", top: 20, left: 20, zIndex: 10, background: "rgba(5,7,10,0.92)", border: "1px solid rgba(0,242,255,0.2)", borderRadius: 10, padding: "12px 16px", fontFamily: "monospace" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#00f2ff", animation: "hp-blink 1.5s ease-in-out infinite" }} />
                  <span style={{ fontSize: 10, color: "#00f2ff", letterSpacing: "0.15em" }}>NSG TACTICAL GRID</span>
                </div>
                {[["CAMERAS","5"],["ACTIVE","4"],["ALERTS","3"],["UAV","1"]].map(([k,v]) => (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 28, fontSize: 10, color: "#64748b", marginBottom: 3 }}>
                    <span>{k}</span><span style={{ color: "#e2e8f0", fontWeight: 700 }}>{v}</span>
                  </div>
                ))}
              </div>
              <div style={{ position: "absolute", top: 20, right: 20, zIndex: 10, background: "rgba(5,7,10,0.92)", border: "1px solid rgba(0,242,255,0.2)", borderRadius: 10, padding: "10px 14px", fontFamily: "monospace" }}>
                <div style={{ fontSize: 9, color: "#64748b", letterSpacing: "0.12em", marginBottom: 4 }}>UAV ALPHA-01</div>
                <div style={{ fontSize: 11, color: "#00f2ff", fontWeight: 700 }}>28.63150, 77.21970</div>
                <div style={{ fontSize: 9, color: "#22c55e", marginTop: 3 }}>ALT: 120m · 15 m/s</div>
              </div>
              <div style={{ position: "absolute", top: 20, left: "50%", transform: "translateX(-50%)", zIndex: 10, fontSize: 10, fontFamily: "monospace", color: "rgba(0,242,255,0.35)", letterSpacing: "0.22em" }}>TACTICAL VIEW — DELHI NCR</div>
              {/* Camera dots */}
              {[
                { x: "28%", y: "36%", color: "#00f2ff", label: "CP-GATE-A",    delay: 0   },
                { x: "46%", y: "43%", color: "#00f2ff", label: "METRO-RCH-02", delay: 400 },
                { x: "17%", y: "66%", color: "#ef4444", label: "IGI-T3",       delay: 800 },
                { x: "73%", y: "56%", color: "#f59e0b", label: "NOIDA-S18",    delay: 1200 },
                { x: "61%", y: "31%", color: "#00f2ff", label: "GGN-CC-01",    delay: 1600 },
              ].map((cam) => (
                <div key={cam.label} style={{ position: "absolute", left: cam.x, top: cam.y, zIndex: 5 }}>
                  <div style={{ position: "absolute", inset: -10, borderRadius: "50%", border: `1px solid ${cam.color}`, animation: `hp-pulse-ring 2.5s ease-out infinite`, animationDelay: `${cam.delay}ms` }} />
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: cam.color, boxShadow: `0 0 12px ${cam.color}`, position: "relative", zIndex: 2 }} />
                  <div style={{ position: "absolute", top: 14, left: "50%", transform: "translateX(-50%)", fontSize: 8, fontFamily: "monospace", color: cam.color, whiteSpace: "nowrap", background: "rgba(5,7,10,0.85)", padding: "2px 6px", borderRadius: 4 }}>{cam.label}</div>
                </div>
              ))}
              {/* Zones */}
              <div style={{ position: "absolute", left: "21%", top: "27%", width: 130, height: 85, border: "1px solid rgba(239,68,68,0.45)", borderRadius: 8, background: "rgba(239,68,68,0.04)", zIndex: 3 }}>
                <div style={{ position: "absolute", top: -18, left: 4, fontSize: 8, fontFamily: "monospace", color: "#ef4444" }}>ZONE RED — CP</div>
              </div>
              <div style={{ position: "absolute", left: "56%", top: "46%", width: 105, height: 72, border: "1px solid rgba(34,197,94,0.38)", borderRadius: 8, background: "rgba(34,197,94,0.03)", zIndex: 3 }}>
                <div style={{ position: "absolute", top: -18, left: 4, fontSize: 8, fontFamily: "monospace", color: "#22c55e" }}>ZONE GREEN — GGN</div>
              </div>
              {/* UAV path SVG */}
              <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", zIndex: 4, pointerEvents: "none" }}>
                <path d="M 190 290 Q 270 230 355 265 Q 440 300 510 245" stroke="rgba(0,242,255,0.35)" strokeWidth="1.5" fill="none" strokeDasharray="7 5" />
              </svg>
              {/* Legend */}
              <div style={{ position: "absolute", bottom: 20, left: 20, zIndex: 10, background: "rgba(5,7,10,0.92)", border: "1px solid rgba(0,242,255,0.1)", borderRadius: 8, padding: "10px 14px", fontFamily: "monospace" }}>
                {[["#00f2ff","Active Camera"],["#ef4444","Alert Camera"],["#f59e0b","Degraded"],["#22c55e","Zone GREEN"],["#ef4444","Zone RED"]].map(([c,l]) => (
                  <div key={l} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 9, color: "#94a3b8", marginBottom: 4 }}>
                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: c, flexShrink: 0 }} />{l}
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <NDivider />

      {/* ══════════════════════════════════════════════════════════════════
          AI CAPABILITIES
      ══════════════════════════════════════════════════════════════════ */}
      <section id="ai" style={{ position: "relative", zIndex: 1, padding: "96px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <Reveal>
            <div style={{ textAlign: "center", marginBottom: 60 }}>
              <SLabel>AI / ML ENGINE</SLabel>
              <h2 style={{ fontSize: "clamp(26px,4vw,44px)", fontWeight: 900, marginBottom: 12, color: "#fff" }}>Intelligence That Never Sleeps</h2>
              <p style={{ color: "#64748b", fontSize: 14, maxWidth: 520, margin: "0 auto", lineHeight: 1.7 }}>Six AI systems running in parallel — detecting, recognising, tracking, and analysing 24/7 across all feeds.</p>
            </div>
          </Reveal>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(310px,1fr))", gap: 16 }}>
            {AI_CAPS.map((f, i) => (
              <Reveal key={f.title} delay={i * 60}>
                <div className="hp-card-hover" style={{ display: "flex", gap: 16, padding: "24px 20px", borderRadius: 14, background: "rgba(10,16,30,0.88)", border: `1px solid ${f.color}20`, height: "100%" }}
                  onMouseEnter={e => { const el = e.currentTarget as HTMLDivElement; el.style.boxShadow = `0 16px 40px ${f.color}15`; el.style.borderColor = `${f.color}50`; }}
                  onMouseLeave={e => { const el = e.currentTarget as HTMLDivElement; el.style.boxShadow = "none"; el.style.borderColor = `${f.color}20`; }}>
                  <div style={{ width: 46, height: 46, borderRadius: 12, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", background: `${f.color}10`, border: `1px solid ${f.color}30` }}>
                    <f.Icon size={21} color={f.color} />
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, color: "#e2e8f0" }}>{f.title}</div>
                    <div style={{ fontSize: 12, color: "#64748b", lineHeight: 1.7 }}>{f.desc}</div>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <NDivider />

      {/* ══════════════════════════════════════════════════════════════════
          ALERTS TIMELINE
      ══════════════════════════════════════════════════════════════════ */}
      <section id="timeline" style={{ position: "relative", zIndex: 1, padding: "96px 24px", background: "rgba(0,0,0,0.32)" }}>
        <div style={{ maxWidth: 820, margin: "0 auto" }}>
          <Reveal>
            <div style={{ textAlign: "center", marginBottom: 60 }}>
              <SLabel>LIVE INCIDENT TIMELINE</SLabel>
              <h2 style={{ fontSize: "clamp(26px,4vw,44px)", fontWeight: 900, marginBottom: 12, color: "#fff" }}>Real-Time Threat Activity</h2>
              <p style={{ color: "#64748b", fontSize: 14, maxWidth: 480, margin: "0 auto", lineHeight: 1.7 }}>Latest incidents from the NSG VisionAI tactical grid — 13 May 2026, Delhi NCR operations.</p>
            </div>
          </Reveal>
          <div style={{ position: "relative" }}>
            <div style={{ position: "absolute", left: 20, top: 0, bottom: 0, width: 1, background: "linear-gradient(to bottom,rgba(0,242,255,0.35),rgba(0,242,255,0.04))" }} />
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              {TIMELINE.map((a, i) => (
                <Reveal key={i} delay={i * 80}>
                  <div style={{ display: "flex", gap: 20, paddingLeft: 50, position: "relative" }}>
                    <div style={{ position: "absolute", left: 14, top: 20, width: 12, height: 12, borderRadius: "50%", background: a.color, border: `2px solid ${a.color}55`, boxShadow: `0 0 10px ${a.color}60` }} />
                    <div style={{ flex: 1, padding: "16px 20px", borderRadius: 12, background: "rgba(10,16,30,0.92)", border: `1px solid ${a.color}20` }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                          <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 8px", borderRadius: 4, background: `${a.color}18`, border: `1px solid ${a.color}40`, color: a.color, fontFamily: "monospace" }}>{a.p}</span>
                          <span style={{ fontSize: 12, fontWeight: 700, color: "#e2e8f0" }}>{a.type}</span>
                        </div>
                        <span style={{ fontSize: 10, fontFamily: "monospace", color: "#475569" }}>{a.time} IST</span>
                      </div>
                      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>{a.loc}</div>
                      <div style={{ fontSize: 11, color: "#94a3b8", fontStyle: "italic" }}>{a.note}</div>
                    </div>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </div>
      </section>

      <NDivider />

      {/* ══════════════════════════════════════════════════════════════════
          INFRASTRUCTURE
      ══════════════════════════════════════════════════════════════════ */}
      <section id="infra" style={{ position: "relative", zIndex: 1, padding: "96px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <Reveal>
            <div style={{ textAlign: "center", marginBottom: 60 }}>
              <SLabel>SECURITY INFRASTRUCTURE</SLabel>
              <h2 style={{ fontSize: "clamp(26px,4vw,44px)", fontWeight: 900, marginBottom: 12, color: "#fff" }}>Defense-Grade Architecture</h2>
              <p style={{ color: "#64748b", fontSize: 14, maxWidth: 520, margin: "0 auto", lineHeight: 1.7 }}>Built for national security — encrypted, air-gappable, and resilient under operational stress.</p>
            </div>
          </Reveal>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(290px,1fr))", gap: 14, marginBottom: 40 }}>
            {INFRA.map((item, i) => (
              <Reveal key={item.title} delay={i * 50}>
                <div className="hp-card-hover" style={{ display: "flex", gap: 14, padding: "20px 18px", borderRadius: 12, background: "rgba(10,16,30,0.88)", border: "1px solid #1e293b", height: "100%" }}
                  onMouseEnter={e => { const el = e.currentTarget as HTMLDivElement; el.style.borderColor = "rgba(0,242,255,0.28)"; el.style.boxShadow = "0 8px 24px rgba(0,242,255,0.06)"; }}
                  onMouseLeave={e => { const el = e.currentTarget as HTMLDivElement; el.style.borderColor = "#1e293b"; el.style.boxShadow = "none"; }}>
                  <div style={{ width: 42, height: 42, borderRadius: 10, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,242,255,0.07)", border: "1px solid rgba(0,242,255,0.18)" }}>
                    <item.Icon size={18} color="#00f2ff" />
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 13, color: "#e2e8f0", marginBottom: 6 }}>{item.title}</div>
                    <div style={{ fontSize: 11, color: "#64748b", lineHeight: 1.65 }}>{item.desc}</div>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
          {/* Data flow */}
          <Reveal delay={200}>
            <div style={{ padding: "28px 32px", borderRadius: 16, background: "rgba(0,242,255,0.025)", border: "1px solid rgba(0,242,255,0.1)" }}>
              <div style={{ fontSize: 10, fontFamily: "monospace", color: "rgba(0,242,255,0.45)", letterSpacing: "0.18em", marginBottom: 20, textAlign: "center" }}>DATA FLOW ARCHITECTURE</div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, flexWrap: "wrap" }}>
                {["IP CAMERA","→","RTSP INGESTER","→","REDIS STREAMS","→","YOLO WORKER","→","ALERT ENGINE","→","OPERATOR"].map((node, i) => (
                  <div key={i} style={{ padding: node === "→" ? "0 2px" : "8px 14px", borderRadius: node === "→" ? 0 : 8, background: node === "→" ? "transparent" : "rgba(0,242,255,0.055)", border: node === "→" ? "none" : "1px solid rgba(0,242,255,0.14)", fontSize: 10, fontFamily: "monospace", color: node === "→" ? "rgba(0,242,255,0.28)" : "rgba(0,242,255,0.72)", fontWeight: node === "→" ? 400 : 700 }}>{node}</div>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <NDivider />

      {/* ══════════════════════════════════════════════════════════════════
          ROLES
      ══════════════════════════════════════════════════════════════════ */}
      <section id="roles" style={{ position: "relative", zIndex: 1, padding: "96px 24px", background: "rgba(0,0,0,0.28)" }}>
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <Reveal>
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <SLabel>ACCESS CONTROL</SLabel>
              <h2 style={{ fontSize: "clamp(26px,4vw,44px)", fontWeight: 900, marginBottom: 12, color: "#fff" }}>Role-Based Clearance</h2>
              <p style={{ color: "#64748b", fontSize: 14, maxWidth: 480, margin: "0 auto", lineHeight: 1.7 }}>Four clearance levels — each with precisely scoped permissions and audit trails.</p>
            </div>
          </Reveal>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(210px,1fr))", gap: 16 }}>
            {ROLES.map((r, i) => (
              <Reveal key={r.role} delay={i * 80}>
                <div className="hp-card-hover" style={{ borderRadius: 14, padding: "22px 20px", background: `${r.color}08`, border: `1px solid ${r.color}28`, height: "100%" }}
                  onMouseEnter={e => { const el = e.currentTarget as HTMLDivElement; el.style.boxShadow = `0 12px 32px ${r.color}15`; el.style.borderColor = `${r.color}50`; }}
                  onMouseLeave={e => { const el = e.currentTarget as HTMLDivElement; el.style.boxShadow = "none"; el.style.borderColor = `${r.color}28`; }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                    <span style={{ fontWeight: 900, fontSize: 14, color: r.color }}>{r.role}</span>
                    <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 8px", borderRadius: 999, border: `1px solid ${r.color}45`, color: r.color, background: `${r.color}12` }}>{r.badge}</span>
                  </div>
                  <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                    {r.items.map(item => (
                      <li key={item} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: "#94a3b8" }}>
                        <div style={{ width: 4, height: 4, borderRadius: "50%", background: r.color, flexShrink: 0 }} />{item}
                      </li>
                    ))}
                  </ul>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <NDivider />

      {/* ══════════════════════════════════════════════════════════════════
          FINAL CTA
      ══════════════════════════════════════════════════════════════════ */}
      <section id="cta" style={{ position: "relative", zIndex: 1, padding: "120px 24px", textAlign: "center", background: "radial-gradient(ellipse 80% 70% at 50% 100%,rgba(0,60,180,0.14) 0%,transparent 70%)" }}>
        <Reveal>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "5px 16px", borderRadius: 999, fontSize: 10, fontFamily: "monospace", letterSpacing: "0.12em", marginBottom: 28, background: "rgba(0,242,255,0.07)", border: "1px solid rgba(0,242,255,0.18)", color: "#67e8f9" }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#22c55e", animation: "hp-blink 2s ease-in-out infinite" }} />
            SYSTEM OPERATIONAL — ALPHA-01
          </div>
          <h2 style={{ fontSize: "clamp(34px,6vw,68px)", fontWeight: 900, marginBottom: 20, background: "linear-gradient(135deg,#fff 0%,#00f2ff 55%,#0066ff 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Ready to Secure the Nation?
          </h2>
          <p style={{ color: "#64748b", fontSize: 15, maxWidth: 460, margin: "0 auto 52px", lineHeight: 1.75 }}>
            Authenticate with your NSG service credentials to access the tactical intelligence platform.
          </p>
          <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
            <button onClick={onEnter} className="hp-glow" style={{ display: "flex", alignItems: "center", gap: 14, padding: "20px 52px", borderRadius: 14, fontWeight: 900, fontSize: 15, letterSpacing: "0.1em", cursor: "pointer", border: "none", background: "linear-gradient(135deg,#00f2ff,#0066ff)", color: "#05070a", transition: "all 0.2s" }}
              onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-3px) scale(1.02)"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0) scale(1)"; }}>
              <Shield size={20} /> ENTER PLATFORM <ChevronRight size={20} />
            </button>
            <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: 10, padding: "20px 36px", borderRadius: 14, fontWeight: 700, fontSize: 14, textDecoration: "none", background: "rgba(15,25,50,0.7)", border: "1px solid rgba(0,242,255,0.2)", color: "#94a3b8", transition: "all 0.2s" }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(0,242,255,0.45)"; e.currentTarget.style.color = "#e2e8f0"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(0,242,255,0.2)"; e.currentTarget.style.color = "#94a3b8"; }}>
              <FileText size={16} /> VIEW API DOCS
            </a>
          </div>
          <p style={{ marginTop: 32, fontSize: 10, fontFamily: "monospace", color: "#1e293b" }}>
            Unauthorised access is a criminal offence under IT Act 2000 and Official Secrets Act 1923
          </p>
        </Reveal>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{ position: "relative", zIndex: 1, padding: "24px 40px", borderTop: "1px solid rgba(0,242,255,0.06)", display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Shield size={13} color="rgba(0,242,255,0.3)" />
          <span style={{ fontSize: 10, fontFamily: "monospace", color: "#334155" }}>NSG VisionAI v1.0.0 — Ministry of Home Affairs, India</span>
        </div>
        <div style={{ fontSize: 10, fontFamily: "monospace", color: "#1e293b" }}>2024–2026 National Security Guard · All Rights Reserved</div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10, fontFamily: "monospace", color: "#1e293b" }}>
          <Lock size={10} /> AES-256-GCM · JWT RS256 · TLS 1.3
        </div>
      </footer>

    </div>
  );
}
