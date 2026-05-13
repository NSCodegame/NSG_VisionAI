/**
 * NSG VisionAI — Landing Page (Rewritten)
 * Clean animation system using CSS keyframes + IntersectionObserver
 */
import { useState, useEffect, useRef, useCallback } from "react";
import {
  Shield, Eye, Brain, Map, Bell, Search, FileText,
  BarChart2, Camera, Cpu, Lock, ChevronRight, Activity,
  Zap, Globe, Users, AlertTriangle, Radio, Crosshair,
} from "lucide-react";

interface HomePageProps { onEnter: () => void; }

/* ── CSS injected once ─────────────────────────────────────────────────── */
const CSS = `
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(32px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0; }
}
@keyframes bounce-arrow {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(6px); }
}
@keyframes count-glow {
  from { text-shadow: 0 0 0px currentColor; }
  to   { text-shadow: 0 0 12px currentColor; }
}
.anim-fade-up   { animation: fadeUp 0.7s cubic-bezier(.22,1,.36,1) both; }
.anim-fade-in   { animation: fadeIn 0.6s ease both; }
.anim-bounce    { animation: bounce-arrow 1.4s ease-in-out infinite; }
.anim-pulse-dot { animation: pulse-dot 1s ease-in-out infinite; }
.hero-card:hover { transform: translateY(-4px); transition: transform 0.25s ease, box-shadow 0.25s ease; }
.hero-card       { transition: transform 0.25s ease, box-shadow 0.25s ease; }
`;

/* ── Typing hook ───────────────────────────────────────────────────────── */
function useTyping(text: string, speed = 55) {
  const [out, setOut] = useState("");
  useEffect(() => {
    setOut("");
    let i = 0;
    const id = setInterval(() => {
      i++;
      setOut(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]);
  return out;
}

/* ── Counter hook ──────────────────────────────────────────────────────── */
function useCounter(target: number, active: boolean, duration = 1800) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!active) return;
    let start: number | null = null;
    const raf = (ts: number) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      const e = 1 - Math.pow(1 - p, 3);
      setVal(Math.floor(e * target));
      if (p < 1) requestAnimationFrame(raf);
    };
    requestAnimationFrame(raf);
  }, [active, target, duration]);
  return val;
}

/* ── Intersection hook ─────────────────────────────────────────────────── */
function useVisible(threshold = 0.15) {
  const ref = useRef<HTMLElement>(null);
  const [vis, setVis] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setVis(true); obs.disconnect(); } }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, vis };
}

/* ── StatItem ──────────────────────────────────────────────────────────── */
function StatItem({ label, value, suffix, Icon, color, active }: {
  label: string; value: number; suffix: string;
  Icon: React.ElementType; color: string; active: boolean;
}) {
  const n = useCounter(value, active);
  return (
    <div className="flex flex-col items-center gap-1 text-center">
      <Icon size={22} className={color} />
      <div className={`text-3xl font-black font-mono ${color}`} style={{ fontVariantNumeric: "tabular-nums" }}>
        {n.toLocaleString()}{suffix}
      </div>
      <div className="text-[10px] text-slate-500 uppercase tracking-widest font-mono">{label}</div>
    </div>
  );
}

/* ── Data ──────────────────────────────────────────────────────────────── */
const STATS = [
  { label: "Camera Feeds",      value: 500,   suffix: "+",   Icon: Camera,    color: "text-cyan-400"   },
  { label: "Detections / Day",  value: 50000, suffix: "+",   Icon: Brain,     color: "text-purple-400" },
  { label: "AI Accuracy",       value: 91,    suffix: "%",   Icon: Crosshair, color: "text-emerald-400"},
  { label: "Uptime",            value: 99,    suffix: ".9%", Icon: Activity,  color: "text-yellow-400" },
  { label: "Watchlist Entries", value: 2400,  suffix: "+",   Icon: Users,     color: "text-orange-400" },
  { label: "Zones Monitored",   value: 120,   suffix: "+",   Icon: Globe,     color: "text-blue-400"   },
];

const FEATURES = [
  { Icon: Eye,      title: "Live Video Intelligence",  desc: "MJPEG/HLS from RTSP cameras, drones, body cams. Real-time AI overlay at 25–40 FPS.",          color: "text-cyan-400",   bg: "rgba(0,242,255,0.06)",   border: "rgba(0,242,255,0.2)"   },
  { Icon: Brain,    title: "AI/ML Detection Pipeline", desc: "YOLOv8n object detection + RetinaFace + ArcFace biometric recognition pipeline.",              color: "text-purple-400", bg: "rgba(168,85,247,0.06)",  border: "rgba(168,85,247,0.2)"  },
  { Icon: Map,      title: "Tactical Map",             desc: "Camera markers, security zone polygons, UAV tracking, and threat-level overlays.",              color: "text-emerald-400",bg: "rgba(52,211,153,0.06)",  border: "rgba(52,211,153,0.2)"  },
  { Icon: Bell,     title: "Alert Management",         desc: "P1–P4 priority alerts with acknowledge, resolve, and false-positive workflows.",                color: "text-red-400",    bg: "rgba(239,68,68,0.06)",   border: "rgba(239,68,68,0.2)"   },
  { Icon: Search,   title: "Forensic Search",          desc: "Face similarity, object class, zone activity, and timeline reconstruction across all feeds.",   color: "text-yellow-400", bg: "rgba(234,179,8,0.06)",   border: "rgba(234,179,8,0.2)"   },
  { Icon: Users,    title: "Biometric Watchlist",      desc: "ArcFace 512-dim embeddings with pgvector similarity search. Real-time watchlist matching.",     color: "text-orange-400", bg: "rgba(249,115,22,0.06)",  border: "rgba(249,115,22,0.2)"  },
  { Icon: FileText, title: "Intelligence Reports",     desc: "Auto-generated classified PDF reports: incident, person, zone activity, forensic timeline.",    color: "text-blue-400",   bg: "rgba(59,130,246,0.06)",  border: "rgba(59,130,246,0.2)"  },
  { Icon: BarChart2,title: "Mission Analytics",        desc: "Alert trends, threat distribution, detection accuracy, camera uptime, and zone heatmaps.",      color: "text-pink-400",   bg: "rgba(236,72,153,0.06)",  border: "rgba(236,72,153,0.2)"  },
];

const TECH = [
  { Icon: Cpu,      label: "YOLOv8n Detection",      sub: "80+ classes · 25–40 FPS on CPU"       },
  { Icon: Eye,      label: "RetinaFace",              sub: "96.1% precision · real-time"          },
  { Icon: Users,    label: "ArcFace Recognition",     sub: "512-dim · 99.83% LFW accuracy"        },
  { Icon: Activity, label: "ByteTrack Tracking",      sub: "Cross-camera Re-ID · MOTA 80.1%"      },
  { Icon: Zap,      label: "LSTM Anomaly Detection",  sub: "AUC-ROC 0.934 · real-time"            },
  { Icon: Lock,     label: "AES-256-GCM Encryption",  sub: "All streams encrypted at rest"        },
  { Icon: Radio,    label: "WebSocket Gateway",       sub: "Sub-100ms push to all operators"      },
  { Icon: Shield,   label: "JWT RS256 Auth",          sub: "8h access · 30d refresh · RBAC"       },
];

const ROLES = [
  { role: "OPERATOR",  badge: "L1", color: "#3b82f6", items: ["Dashboard","Live Feeds","Webcam AI","Tactical Map","Alerts"] },
  { role: "ANALYST",   badge: "L2", color: "#10b981", items: ["All Operator","Forensics","Watchlist","Reports","Analytics"] },
  { role: "COMMANDER", badge: "L3", color: "#eab308", items: ["All Analyst","Mission Control","Priority Alerts","Zone Mgmt"] },
  { role: "ADMIN",     badge: "L4", color: "#ef4444", items: ["Full Access","ML Models","Audit Logs","User Mgmt","Sys Health"] },
];

/* ── Main component ────────────────────────────────────────────────────── */
export function HomePage({ onEnter }: HomePageProps) {
  const tagline = useTyping("Sarvatra Sarvottam Suraksha", 55);
  const { ref: statsRef, vis: statsVis } = useVisible(0.1) as { ref: React.RefObject<HTMLElement>; vis: boolean };
  const { ref: featRef, vis: featVis }   = useVisible(0.05) as { ref: React.RefObject<HTMLElement>; vis: boolean };
  const { ref: techRef, vis: techVis }   = useVisible(0.05) as { ref: React.RefObject<HTMLElement>; vis: boolean };
  const { ref: roleRef, vis: roleVis }   = useVisible(0.05) as { ref: React.RefObject<HTMLElement>; vis: boolean };

  /* inject CSS once */
  useEffect(() => {
    if (document.getElementById("hp-css")) return;
    const s = document.createElement("style");
    s.id = "hp-css";
    s.textContent = CSS;
    document.head.appendChild(s);
    return () => { document.getElementById("hp-css")?.remove(); };
  }, []);

  const scrollToStats = useCallback(() => {
    statsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [statsRef]);

  return (
    <div style={{ background: "#05070a", color: "#fff", minHeight: "100vh", position: "relative" }}>

      {/* grid bg */}
      <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0,
        backgroundImage: "linear-gradient(rgba(0,242,255,0.025) 1px,transparent 1px),linear-gradient(90deg,rgba(0,242,255,0.025) 1px,transparent 1px)",
        backgroundSize: "48px 48px" }} />
      {/* radial glow */}
      <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0,
        background: "radial-gradient(ellipse 80% 40% at 50% -5%,rgba(0,100,255,0.14) 0%,transparent 70%)" }} />

      {/* ── NAV ── */}
      <nav style={{ position: "sticky", top: 0, zIndex: 50, display: "flex", alignItems: "center",
        justifyContent: "space-between", padding: "14px 32px",
        background: "rgba(5,7,10,0.88)", backdropFilter: "blur(14px)",
        borderBottom: "1px solid rgba(0,242,255,0.08)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 36, height: 36, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center",
            background: "rgba(0,242,255,0.1)", border: "1px solid rgba(0,242,255,0.3)" }}>
            <Shield size={17} color="#00f2ff" />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 15, letterSpacing: "-0.3px" }}>
              NSG <span style={{ color: "#00f2ff" }}>VisionAI</span>
            </div>
            <div style={{ fontSize: 9, fontFamily: "monospace", color: "#475569", letterSpacing: "0.15em" }}>
              TACTICAL INTELLIGENCE PLATFORM
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10, fontFamily: "monospace",
          color: "#475569", background: "rgba(15,23,42,0.7)", padding: "6px 14px",
          borderRadius: 999, border: "1px solid #1e293b" }}>
          <Activity size={9} color="#34d399" />
          <span style={{ marginLeft: 4 }}>SECURE NODE: ALPHA-01</span>
          <span style={{ margin: "0 8px", color: "#1e293b" }}>|</span>
          <span style={{ color: "#34d399" }}>ONLINE</span>
        </div>

        <button onClick={onEnter} style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 20px",
          borderRadius: 10, fontSize: 12, fontWeight: 700, cursor: "pointer",
          background: "linear-gradient(135deg,rgba(0,242,255,0.15),rgba(0,128,255,0.15))",
          border: "1px solid rgba(0,242,255,0.35)", color: "#00f2ff", transition: "all 0.2s" }}
          onMouseEnter={e => { e.currentTarget.style.background = "linear-gradient(135deg,rgba(0,242,255,0.28),rgba(0,128,255,0.28))"; e.currentTarget.style.boxShadow = "0 0 20px rgba(0,242,255,0.25)"; }}
          onMouseLeave={e => { e.currentTarget.style.background = "linear-gradient(135deg,rgba(0,242,255,0.15),rgba(0,128,255,0.15))"; e.currentTarget.style.boxShadow = "none"; }}>
          <Lock size={12} /> Sign In
        </button>
      </nav>

      {/* ── HERO ── */}
      <section style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column",
        alignItems: "center", textAlign: "center", padding: "96px 24px 80px" }}>

        {/* restricted badge */}
        <div className="anim-fade-up" style={{ animationDelay: "0.05s",
          display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 16px",
          borderRadius: 999, fontSize: 10, fontWeight: 700, fontFamily: "monospace", letterSpacing: "0.12em",
          marginBottom: 32, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#fca5a5" }}>
          <AlertTriangle size={10} /> RESTRICTED — AUTHORISED PERSONNEL ONLY <AlertTriangle size={10} />
        </div>

        {/* headline */}
        <h1 className="anim-fade-up" style={{ animationDelay: "0.15s",
          fontSize: "clamp(48px,8vw,88px)", fontWeight: 900, letterSpacing: "-2px",
          lineHeight: 1.05, marginBottom: 16,
          background: "linear-gradient(135deg,#fff 0%,#00f2ff 55%,#0080ff 100%)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          NSG VisionAI
        </h1>

        {/* typing tagline */}
        <div className="anim-fade-in" style={{ animationDelay: "0.3s",
          fontSize: "clamp(14px,2vw,20px)", fontFamily: "monospace", color: "rgba(0,242,255,0.85)",
          marginBottom: 12, minHeight: 32 }}>
          "{tagline}"<span className="anim-pulse-dot" style={{ color: "#00f2ff" }}>_</span>
        </div>

        {/* description */}
        <p className="anim-fade-up" style={{ animationDelay: "0.4s",
          color: "#94a3b8", fontSize: "clamp(13px,1.5vw,16px)", maxWidth: 600,
          lineHeight: 1.7, marginBottom: 40 }}>
          Defense-grade AI/ML surveillance platform for India's National Security Guard.
          Real-time video intelligence, biometric recognition, and tactical situational awareness
          — unified in a single secure dashboard.
        </p>

        {/* CTAs */}
        <div className="anim-fade-up" style={{ animationDelay: "0.5s",
          display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center" }}>
          <button onClick={onEnter} style={{ display: "flex", alignItems: "center", gap: 12,
            padding: "16px 32px", borderRadius: 12, fontWeight: 800, fontSize: 13,
            letterSpacing: "0.1em", cursor: "pointer", border: "none",
            background: "linear-gradient(135deg,#00f2ff,#0080ff)", color: "#05070a",
            boxShadow: "0 0 32px rgba(0,242,255,0.45),0 4px 20px rgba(0,0,0,0.4)",
            transition: "all 0.2s" }}
            onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 0 55px rgba(0,242,255,0.65),0 4px 20px rgba(0,0,0,0.4)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
            onMouseLeave={e => { e.currentTarget.style.boxShadow = "0 0 32px rgba(0,242,255,0.45),0 4px 20px rgba(0,0,0,0.4)"; e.currentTarget.style.transform = "translateY(0)"; }}>
            <Shield size={16} /> ENTER PLATFORM <ChevronRight size={16} />
          </button>

          <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer"
            style={{ display: "flex", alignItems: "center", gap: 10, padding: "16px 32px",
              borderRadius: 12, fontWeight: 700, fontSize: 13, letterSpacing: "0.1em",
              textDecoration: "none", background: "rgba(15,25,50,0.7)",
              border: "1px solid rgba(0,242,255,0.2)", color: "#94a3b8", transition: "all 0.2s" }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(0,242,255,0.45)"; e.currentTarget.style.color = "#e2e8f0"; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(0,242,255,0.2)"; e.currentTarget.style.color = "#94a3b8"; }}>
            <FileText size={16} /> API DOCS
          </a>
        </div>

        {/* scroll cue */}
        <button onClick={scrollToStats} style={{ marginTop: 64, display: "flex", flexDirection: "column",
          alignItems: "center", gap: 8, background: "none", border: "none", cursor: "pointer",
          color: "#475569", transition: "color 0.2s" }}
          onMouseEnter={e => e.currentTarget.style.color = "#94a3b8"}
          onMouseLeave={e => e.currentTarget.style.color = "#475569"}>
          <span style={{ fontSize: 10, fontFamily: "monospace", letterSpacing: "0.15em" }}>SCROLL TO EXPLORE</span>
          <div className="anim-bounce" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
            <div style={{ width: 1, height: 28, background: "linear-gradient(to bottom,#475569,transparent)" }} />
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "rgba(0,242,255,0.5)" }} />
          </div>
        </button>
      </section>

      {/* ── STATS ── */}
      <section ref={statsRef as React.RefObject<HTMLDivElement>} style={{ position: "relative", zIndex: 1,
        padding: "56px 24px", borderTop: "1px solid rgba(0,242,255,0.08)",
        borderBottom: "1px solid rgba(0,242,255,0.08)", background: "rgba(0,242,255,0.02)" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto",
          display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 32 }}>
          {STATS.map(s => (
            <StatItem key={s.label} label={s.label} value={s.value} suffix={s.suffix}
              Icon={s.Icon} color={s.color} active={statsVis} />
          ))}
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section ref={featRef as React.RefObject<HTMLDivElement>} style={{ position: "relative", zIndex: 1,
        padding: "80px 24px", maxWidth: 1280, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 56 }}
          className={featVis ? "anim-fade-up" : ""} >
          <div style={{ fontSize: 10, fontFamily: "monospace", color: "rgba(0,242,255,0.5)",
            letterSpacing: "0.18em", marginBottom: 12 }}>PLATFORM CAPABILITIES</div>
          <h2 style={{ fontSize: "clamp(24px,4vw,40px)", fontWeight: 900, marginBottom: 14 }}>
            Full-Spectrum Surveillance Intelligence
          </h2>
          <p style={{ color: "#64748b", fontSize: 14, maxWidth: 520, margin: "0 auto" }}>
            Every module purpose-built for national security — from real-time detection to forensic analysis.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(240px,1fr))", gap: 16 }}>
          {FEATURES.map((f, i) => (
            <div key={f.title} className={`hero-card ${featVis ? "anim-fade-up" : ""}`}
              style={{ animationDelay: `${0.05 * i}s`, borderRadius: 14, padding: 20,
                background: "rgba(13,17,23,0.85)", border: `1px solid ${f.border}`,
                cursor: "default" }}
              onMouseEnter={e => { e.currentTarget.style.background = f.bg; e.currentTarget.style.boxShadow = `0 8px 32px ${f.bg}`; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(13,17,23,0.85)"; e.currentTarget.style.boxShadow = "none"; }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, display: "flex",
                alignItems: "center", justifyContent: "center", marginBottom: 14,
                background: f.bg, border: `1px solid ${f.border}` }}>
                <f.Icon size={18} color={f.border} />
              </div>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>{f.title}</div>
              <div style={{ fontSize: 11, color: "#64748b", lineHeight: 1.6 }}>{f.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── TECH ── */}
      <section ref={techRef as React.RefObject<HTMLDivElement>} style={{ position: "relative", zIndex: 1,
        padding: "64px 24px", background: "rgba(0,0,0,0.35)",
        borderTop: "1px solid rgba(0,242,255,0.06)", borderBottom: "1px solid rgba(0,242,255,0.06)" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 40 }}
            className={techVis ? "anim-fade-up" : ""}>
            <div style={{ fontSize: 10, fontFamily: "monospace", color: "rgba(0,242,255,0.5)",
              letterSpacing: "0.18em", marginBottom: 10 }}>TECHNICAL SPECIFICATIONS</div>
            <h2 style={{ fontSize: "clamp(20px,3vw,30px)", fontWeight: 900 }}>AI / ML Engine</h2>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 12 }}>
            {TECH.map((t, i) => (
              <div key={t.label} className={techVis ? "anim-fade-up" : ""}
                style={{ animationDelay: `${0.06 * i}s`, display: "flex", alignItems: "flex-start",
                  gap: 12, padding: 16, borderRadius: 10,
                  background: "rgba(15,23,42,0.5)", border: "1px solid #1e293b",
                  transition: "border-color 0.2s" }}
                onMouseEnter={e => e.currentTarget.style.borderColor = "#334155"}
                onMouseLeave={e => e.currentTarget.style.borderColor = "#1e293b"}>
                <div style={{ width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  background: "rgba(0,242,255,0.08)", border: "1px solid rgba(0,242,255,0.2)" }}>
                  <t.Icon size={14} color="#00f2ff" />
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "#e2e8f0" }}>{t.label}</div>
                  <div style={{ fontSize: 10, color: "#64748b", fontFamily: "monospace", marginTop: 3 }}>{t.sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── ROLES ── */}
      <section ref={roleRef as React.RefObject<HTMLDivElement>} style={{ position: "relative", zIndex: 1,
        padding: "80px 24px", maxWidth: 1000, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}
          className={roleVis ? "anim-fade-up" : ""}>
          <div style={{ fontSize: 10, fontFamily: "monospace", color: "rgba(0,242,255,0.5)",
            letterSpacing: "0.18em", marginBottom: 12 }}>ACCESS CONTROL</div>
          <h2 style={{ fontSize: "clamp(22px,3.5vw,36px)", fontWeight: 900, marginBottom: 10 }}>
            Role-Based Clearance
          </h2>
          <p style={{ color: "#64748b", fontSize: 14 }}>Four clearance levels — each with precisely scoped permissions.</p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 16 }}>
          {ROLES.map((r, i) => (
            <div key={r.role} className={roleVis ? "anim-fade-up" : ""}
              style={{ animationDelay: `${0.1 * i}s`, borderRadius: 14, padding: 20,
                background: `${r.color}0d`, border: `1px solid ${r.color}33` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <span style={{ fontWeight: 900, fontSize: 14, color: r.color }}>{r.role}</span>
                <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 8px", borderRadius: 999,
                  border: `1px solid ${r.color}55`, color: r.color, background: `${r.color}15` }}>{r.badge}</span>
              </div>
              <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                {r.items.map(item => (
                  <li key={item} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: "#94a3b8" }}>
                    <div style={{ width: 4, height: 4, borderRadius: "50%", background: r.color, flexShrink: 0 }} />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* ── FINAL CTA ── */}
      <section style={{ position: "relative", zIndex: 1, padding: "96px 24px", textAlign: "center",
        borderTop: "1px solid rgba(0,242,255,0.08)", background: "rgba(0,242,255,0.015)" }}>
        <div className="anim-fade-up" style={{ display: "inline-flex", alignItems: "center", gap: 8,
          padding: "6px 16px", borderRadius: 999, fontSize: 10, fontFamily: "monospace",
          letterSpacing: "0.12em", marginBottom: 24,
          background: "rgba(0,242,255,0.08)", border: "1px solid rgba(0,242,255,0.2)", color: "#67e8f9" }}>
          <Activity size={10} color="#34d399" /> SYSTEM OPERATIONAL — ALPHA-01
        </div>
        <h2 className="anim-fade-up" style={{ animationDelay: "0.1s",
          fontSize: "clamp(28px,5vw,52px)", fontWeight: 900, marginBottom: 16,
          background: "linear-gradient(135deg,#fff,#00f2ff)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          Ready to Secure the Nation?
        </h2>
        <p className="anim-fade-up" style={{ animationDelay: "0.2s",
          color: "#64748b", fontSize: 14, maxWidth: 420, margin: "0 auto 40px" }}>
          Authenticate with your NSG service credentials to access the tactical intelligence platform.
        </p>
        <button onClick={onEnter} className="anim-fade-up"
          style={{ animationDelay: "0.3s", display: "inline-flex", alignItems: "center", gap: 14,
            padding: "20px 44px", borderRadius: 14, fontWeight: 900, fontSize: 15,
            letterSpacing: "0.1em", cursor: "pointer", border: "none",
            background: "linear-gradient(135deg,#00f2ff,#0080ff)", color: "#05070a",
            boxShadow: "0 0 44px rgba(0,242,255,0.5),0 8px 32px rgba(0,0,0,0.5)",
            transition: "all 0.2s" }}
          onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 0 70px rgba(0,242,255,0.7),0 8px 32px rgba(0,0,0,0.5)"; e.currentTarget.style.transform = "translateY(-3px) scale(1.02)"; }}
          onMouseLeave={e => { e.currentTarget.style.boxShadow = "0 0 44px rgba(0,242,255,0.5),0 8px 32px rgba(0,0,0,0.5)"; e.currentTarget.style.transform = "translateY(0) scale(1)"; }}>
          <Shield size={20} /> ENTER PLATFORM <ChevronRight size={20} />
        </button>
        <p style={{ marginTop: 24, fontSize: 10, fontFamily: "monospace", color: "#334155" }}>
          Unauthorised access is a criminal offence under IT Act 2000 &amp; Official Secrets Act 1923
        </p>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{ position: "relative", zIndex: 1, padding: "24px 32px",
        borderTop: "1px solid rgba(0,242,255,0.06)",
        display: "flex", flexWrap: "wrap", alignItems: "center",
        justifyContent: "space-between", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Shield size={13} color="rgba(0,242,255,0.4)" />
          <span style={{ fontSize: 10, fontFamily: "monospace", color: "#334155" }}>
            NSG VisionAI v1.0.0 — Ministry of Home Affairs, India
          </span>
        </div>
        <div style={{ fontSize: 10, fontFamily: "monospace", color: "#1e293b" }}>
          © 2024–2026 National Security Guard · All Rights Reserved
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10, fontFamily: "monospace", color: "#1e293b" }}>
          <Lock size={10} /> AES-256-GCM · JWT RS256 · TLS 1.3
        </div>
      </footer>

    </div>
  );
}
