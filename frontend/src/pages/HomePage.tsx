/**
 * NSG VisionAI — Cinematic Landing Page
 * Full single-page scrolling experience with Framer Motion
 */
import { useEffect, useRef, useState } from "react";
import { motion, useScroll, useTransform, useInView, AnimatePresence } from "framer-motion";
import {
  Shield, Eye, Brain, Map, Bell, Search, FileText, BarChart2,
  Camera, Cpu, Lock, ChevronRight, Activity, Zap, Globe, Users,
  AlertTriangle, Radio, Crosshair, Server, Wifi, Target, Clock,
  TrendingUp, Database, Network, Layers, Monitor, Fingerprint,
} from "lucide-react";

interface HomePageProps { onEnter: () => void; }

/* ─── Shared animation variants ─────────────────────────────────────────── */
const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] } },
};
const fadeIn = {
  hidden: { opacity: 0 },
  show:   { opacity: 1, transition: { duration: 0.6 } },
};
const stagger = (delay = 0.08) => ({
  show: { transition: { staggerChildren: delay } },
});

/* ─── Animated counter ───────────────────────────────────────────────────── */
function Counter({ to, suffix = "", duration = 2 }: { to: number; suffix?: string; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!inView) return;
    let start: number | null = null;
    const step = (ts: number) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / (duration * 1000), 1);
      const e = 1 - Math.pow(1 - p, 3);
      setVal(Math.floor(e * to));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [inView, to, duration]);
  return <span ref={ref}>{val.toLocaleString()}{suffix}</span>;
}

/* ─── Section wrapper — uses whileInView directly (no useInView hook needed) ─ */
function Section({ children, className = "", id = "", style = {} }: {
  children: React.ReactNode; className?: string; id?: string; style?: React.CSSProperties;
}) {
  return (
    <section id={id} className={className} style={style}>
      {children}
    </section>
  );
}

/* ─── Glowing label ──────────────────────────────────────────────────────── */
function Label({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 8,
      fontSize: 10, fontFamily: "monospace", letterSpacing: "0.18em",
      color: "rgba(0,242,255,0.6)", marginBottom: 14,
      padding: "4px 14px", borderRadius: 999,
      background: "rgba(0,242,255,0.06)", border: "1px solid rgba(0,242,255,0.15)",
    }}>
      {children}
    </div>
  );
}

/* ─── Neon divider ───────────────────────────────────────────────────────── */
function Divider() {
  return (
    <div style={{ width: "100%", height: 1, margin: "0 auto",
      background: "linear-gradient(90deg,transparent,rgba(0,242,255,0.2),transparent)" }} />
  );
}

/* ─── DATA ───────────────────────────────────────────────────────────────── */
const METRICS = [
  { icon: Camera,      label: "Active Cameras",      value: 500,   suffix: "+",   color: "#00f2ff" },
  { icon: Brain,       label: "AI Detections Today", value: 50000, suffix: "+",   color: "#a855f7" },
  { icon: AlertTriangle,label:"Active Alerts",       value: 47,    suffix: "",    color: "#ef4444" },
  { icon: Activity,    label: "System Uptime",       value: 99,    suffix: ".9%", color: "#22c55e" },
  { icon: Fingerprint, label: "Biometric Scans",     value: 12400, suffix: "+",   color: "#f97316" },
  { icon: Globe,       label: "Zones Monitored",     value: 120,   suffix: "+",   color: "#3b82f6" },
];

const MODULES = [
  { icon: Monitor,     name: "Dashboard",    desc: "Live ops overview with real-time alert feed and tracked persons",  color: "#00f2ff" },
  { icon: Camera,      name: "Feeds",        desc: "MJPEG/HLS streams from RTSP cameras, drones, and body cams",       color: "#a855f7" },
  { icon: Wifi,        name: "IP Cameras",   desc: "Auto-discover and configure IP cameras on your LAN",               color: "#22c55e" },
  { icon: Eye,         name: "Webcam AI",    desc: "Live YOLO detection + face analysis from laptop webcam",           color: "#f97316" },
  { icon: Map,         name: "Tactical Map", desc: "Camera markers, zone polygons, UAV tracking, threat overlays",     color: "#3b82f6" },
  { icon: Bell,        name: "Alerts",       desc: "P1–P4 priority alerts with acknowledge and resolve workflows",      color: "#ef4444" },
  { icon: Search,      name: "Forensics",    desc: "Face search, object search, zone activity, timeline reconstruction",color: "#eab308" },
  { icon: Users,       name: "Watchlist",    desc: "ArcFace biometric database with real-time matching across feeds",  color: "#ec4899" },
  { icon: FileText,    name: "Reports",      desc: "Auto-generated classified PDF intelligence reports",               color: "#06b6d4" },
  { icon: BarChart2,   name: "Analytics",    desc: "Alert trends, threat distribution, detection accuracy metrics",    color: "#8b5cf6" },
  { icon: Cpu,         name: "Admin",        desc: "ML model registry, system health, audit logs, user management",    color: "#64748b" },
];

const AI_FEATURES = [
  { icon: Eye,         title: "Face Recognition",          desc: "ArcFace 512-dim embeddings. 99.83% LFW accuracy. Real-time watchlist matching.",    color: "#00f2ff" },
  { icon: Target,      title: "Object Detection",          desc: "YOLOv8n at 25–40 FPS. 80+ classes. Weapon, vehicle, bag, drone detection.",         color: "#a855f7" },
  { icon: TrendingUp,  title: "Anomaly Detection",         desc: "LSTM-based suspicious movement pattern recognition. AUC-ROC 0.934.",                 color: "#22c55e" },
  { icon: Users,       title: "Crowd Analysis",            desc: "Density estimation, loitering detection, crowd behaviour classification.",           color: "#f97316" },
  { icon: Brain,       title: "Behavioural AI",            desc: "Emotion mapping, threat behaviour classification, ARMED_THREAT detection.",          color: "#ef4444" },
  { icon: Crosshair,   title: "Person Tracking",           desc: "ByteTrack cross-camera Re-ID. MOTA 80.1%. Persistent track IDs across feeds.",      color: "#eab308" },
];

const ALERTS_TIMELINE = [
  { time: "08:42:17", type: "WATCHLIST MATCH",  loc: "Connaught Place Gate A",    priority: "P1", color: "#ef4444", suspect: "Rashid Ahmed Khan — 94% confidence" },
  { time: "08:44:03", type: "WEAPON DETECTED",  loc: "Connaught Place Gate A",    priority: "P1", color: "#ef4444", suspect: "Weapon-like object in frame — 87%" },
  { time: "06:12:44", type: "ZONE BREACH",      loc: "IGI Airport T3 Restricted", priority: "P2", color: "#f97316", suspect: "Salma Qureshi — Airside access violation" },
  { time: "07:58:22", type: "LOITERING",        loc: "Rajiv Chowk Metro Gate 2",  priority: "P3", color: "#eab308", suspect: "Farhan Siddiqui — 16 min loiter detected" },
  { time: "19:17:05", type: "WATCHLIST MATCH",  loc: "Cyber City DLF Tower",      priority: "P2", color: "#f97316", suspect: "Devraj Menon — 88% confidence" },
];

const INFRA = [
  { icon: Lock,     title: "AES-256-GCM Encryption",  desc: "All RTSP URLs and video segments encrypted at rest" },
  { icon: Server,   title: "Edge AI Processing",       desc: "On-premise inference — no cloud dependency" },
  { icon: Network,  title: "WebSocket Gateway",        desc: "Sub-100ms real-time alert push to all operators" },
  { icon: Database, title: "TimescaleDB + pgvector",   desc: "Time-series events + 512-dim biometric embeddings" },
  { icon: Shield,   title: "JWT RS256 Auth",           desc: "8h access tokens, 30d refresh, RBAC role hierarchy" },
  { icon: Layers,   title: "Celery Task Queue",        desc: "Async ML pipeline — detection, tracking, archival" },
];

/* ─── MAIN COMPONENT ─────────────────────────────────────────────────────── */
export function HomePage({ onEnter }: HomePageProps) {
  const heroRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ["start start", "end start"] });
  const heroY    = useTransform(scrollYProgress, [0, 1], ["0%", "25%"]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.7], [1, 0]);

  /* typing effect */
  const [typed, setTyped] = useState("");
  const TAGLINE = "Sarvatra Sarvottam Suraksha";
  useEffect(() => {
    let i = 0;
    const id = setInterval(() => { i++; setTyped(TAGLINE.slice(0, i)); if (i >= TAGLINE.length) clearInterval(id); }, 55);
    return () => clearInterval(id);
  }, []);

  return (
    <div style={{ background: "#05070a", color: "#fff", overflowX: "hidden" }}>

      {/* ══════════════════════════════════════════════════════════════════
          1. HERO
      ══════════════════════════════════════════════════════════════════ */}
      <div ref={heroRef} style={{ position: "relative", minHeight: "100vh", overflow: "hidden" }}>

        {/* parallax bg */}
        <motion.div style={{ y: heroY, position: "absolute", inset: 0, zIndex: 0 }}>
          {/* grid */}
          <div style={{ position: "absolute", inset: 0,
            backgroundImage: "linear-gradient(rgba(0,242,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,242,255,0.03) 1px,transparent 1px)",
            backgroundSize: "48px 48px" }} />
          {/* radial glow */}
          <div style={{ position: "absolute", inset: 0,
            background: "radial-gradient(ellipse 80% 50% at 50% -5%,rgba(0,100,255,0.18) 0%,transparent 70%)" }} />
          {/* corner accents */}
          <div style={{ position: "absolute", top: 80, left: 80, width: 200, height: 200, borderRadius: "50%",
            background: "radial-gradient(circle,rgba(0,242,255,0.06) 0%,transparent 70%)", filter: "blur(20px)" }} />
          <div style={{ position: "absolute", top: 120, right: 100, width: 160, height: 160, borderRadius: "50%",
            background: "radial-gradient(circle,rgba(168,85,247,0.07) 0%,transparent 70%)", filter: "blur(20px)" }} />
        </motion.div>

        {/* sticky nav */}
        <nav style={{ position: "sticky", top: 0, zIndex: 50, display: "flex", alignItems: "center",
          justifyContent: "space-between", padding: "14px 40px",
          background: "rgba(5,7,10,0.85)", backdropFilter: "blur(16px)",
          borderBottom: "1px solid rgba(0,242,255,0.08)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <motion.div whileHover={{ scale: 1.05 }} style={{ width: 36, height: 36, borderRadius: 8,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "rgba(0,242,255,0.1)", border: "1px solid rgba(0,242,255,0.3)" }}>
              <Shield size={17} color="#00f2ff" />
            </motion.div>
            <div>
              <div style={{ fontWeight: 800, fontSize: 15 }}>NSG <span style={{ color: "#00f2ff" }}>VisionAI</span></div>
              <div style={{ fontSize: 9, fontFamily: "monospace", color: "#475569", letterSpacing: "0.15em" }}>TACTICAL INTELLIGENCE PLATFORM</div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10, fontFamily: "monospace",
            color: "#475569", background: "rgba(15,23,42,0.7)", padding: "6px 14px",
            borderRadius: 999, border: "1px solid #1e293b" }}>
            <motion.div animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 2, repeat: Infinity }}
              style={{ width: 6, height: 6, borderRadius: "50%", background: "#22c55e" }} />
            <span style={{ marginLeft: 4 }}>SECURE NODE: ALPHA-01</span>
            <span style={{ margin: "0 8px", color: "#1e293b" }}>|</span>
            <span style={{ color: "#22c55e" }}>ONLINE</span>
          </div>
          <motion.button onClick={onEnter} whileHover={{ scale: 1.04, boxShadow: "0 0 24px rgba(0,242,255,0.3)" }}
            whileTap={{ scale: 0.97 }}
            style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 20px",
              borderRadius: 10, fontSize: 12, fontWeight: 700, cursor: "pointer",
              background: "linear-gradient(135deg,rgba(0,242,255,0.15),rgba(0,128,255,0.15))",
              border: "1px solid rgba(0,242,255,0.35)", color: "#00f2ff" }}>
            <Lock size={12} /> Sign In
          </motion.button>
        </nav>

        {/* hero content */}
        <motion.div style={{ opacity: heroOpacity, position: "relative", zIndex: 1,
          display: "flex", flexDirection: "column", alignItems: "center",
          textAlign: "center", padding: "100px 24px 80px" }}>

          <motion.div variants={fadeIn} initial="hidden" animate="show"
            style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "5px 16px",
              borderRadius: 999, fontSize: 10, fontFamily: "monospace", letterSpacing: "0.12em",
              marginBottom: 28, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#fca5a5" }}>
            <AlertTriangle size={10} /> RESTRICTED — AUTHORISED PERSONNEL ONLY <AlertTriangle size={10} />
          </motion.div>

          <motion.h1 variants={fadeUp} initial="hidden" animate="show"
            style={{ fontSize: "clamp(52px,9vw,96px)", fontWeight: 900, letterSpacing: "-3px",
              lineHeight: 1.0, marginBottom: 20,
              background: "linear-gradient(135deg,#fff 0%,#00f2ff 55%,#0080ff 100%)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            NSG VisionAI
          </motion.h1>

          <motion.div variants={fadeUp} initial="hidden" animate="show"
            transition={{ delay: 0.15 }}
            style={{ fontSize: "clamp(15px,2.2vw,22px)", fontFamily: "monospace",
              color: "rgba(0,242,255,0.85)", marginBottom: 14, minHeight: 34 }}>
            "{typed}"<motion.span animate={{ opacity: [1, 0, 1] }} transition={{ duration: 1, repeat: Infinity }}>_</motion.span>
          </motion.div>

          <motion.p variants={fadeUp} initial="hidden" animate="show" transition={{ delay: 0.25 }}
            style={{ color: "#94a3b8", fontSize: "clamp(13px,1.5vw,16px)", maxWidth: 580,
              lineHeight: 1.75, marginBottom: 44 }}>
            Defense-grade AI/ML surveillance platform for India's National Security Guard.
            Real-time video intelligence, biometric recognition, and tactical situational awareness
            — unified in a single secure command dashboard.
          </motion.p>

          <motion.div variants={stagger(0.1)} initial="hidden" animate="show"
            style={{ display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center" }}>
            <motion.button variants={fadeUp} onClick={onEnter}
              whileHover={{ scale: 1.04, boxShadow: "0 0 55px rgba(0,242,255,0.65)" }}
              whileTap={{ scale: 0.97 }}
              style={{ display: "flex", alignItems: "center", gap: 12, padding: "16px 36px",
                borderRadius: 12, fontWeight: 800, fontSize: 13, letterSpacing: "0.1em",
                cursor: "pointer", border: "none",
                background: "linear-gradient(135deg,#00f2ff,#0080ff)", color: "#05070a",
                boxShadow: "0 0 32px rgba(0,242,255,0.45)" }}>
              <Shield size={16} /> ENTER PLATFORM <ChevronRight size={16} />
            </motion.button>
            <motion.a variants={fadeUp} href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer"
              whileHover={{ borderColor: "rgba(0,242,255,0.5)", color: "#e2e8f0" }}
              style={{ display: "flex", alignItems: "center", gap: 10, padding: "16px 32px",
                borderRadius: 12, fontWeight: 700, fontSize: 13, letterSpacing: "0.1em",
                textDecoration: "none", background: "rgba(15,25,50,0.7)",
                border: "1px solid rgba(0,242,255,0.2)", color: "#94a3b8", transition: "all 0.2s" }}>
              <FileText size={16} /> API DOCS
            </motion.a>
          </motion.div>

          {/* scroll cue */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.2 }}
            style={{ marginTop: 72, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 10, fontFamily: "monospace", letterSpacing: "0.15em", color: "#334155" }}>SCROLL TO EXPLORE</span>
            <motion.div animate={{ y: [0, 8, 0] }} transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
              style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
              <div style={{ width: 1, height: 32, background: "linear-gradient(to bottom,#334155,transparent)" }} />
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: "rgba(0,242,255,0.5)" }} />
            </motion.div>
          </motion.div>
        </motion.div>
      </div>

      <Divider />

      {/* ══════════════════════════════════════════════════════════════════
          2. LIVE SYSTEM METRICS
      ══════════════════════════════════════════════════════════════════ */}
      <Section id="metrics" style={{ padding: "80px 24px", background: "rgba(0,242,255,0.015)" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", textAlign: "center" }}>
          <Label><Activity size={10} /> LIVE SYSTEM METRICS</Label>
          <h2 style={{ fontSize: "clamp(24px,4vw,42px)", fontWeight: 900, marginBottom: 12 }}>
            Platform at a Glance
          </h2>
          <p style={{ color: "#64748b", fontSize: 14, marginBottom: 56, maxWidth: 480, margin: "0 auto 56px" }}>
            Real-time operational statistics from the NSG VisionAI tactical grid.
          </p>
          <motion.div variants={stagger(0.07)} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-60px" }}
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 20 }}>
            {METRICS.map(m => (
              <motion.div key={m.label} variants={fadeUp}
                whileHover={{ scale: 1.04, boxShadow: `0 0 24px ${m.color}22` }}
                style={{ padding: "28px 16px", borderRadius: 14, textAlign: "center",
                  background: "rgba(13,17,23,0.9)", border: `1px solid ${m.color}33`,
                  transition: "box-shadow 0.2s" }}>
                <motion.div animate={{ opacity: [0.7, 1, 0.7] }} transition={{ duration: 2.5, repeat: Infinity }}
                  style={{ marginBottom: 12 }}>
                  <m.icon size={24} color={m.color} />
                </motion.div>
                <div style={{ fontSize: 30, fontWeight: 900, fontFamily: "monospace", color: m.color, marginBottom: 6 }}>
                  <Counter to={m.value} suffix={m.suffix} />
                </div>
                <div style={{ fontSize: 10, color: "#64748b", letterSpacing: "0.12em", textTransform: "uppercase", fontFamily: "monospace" }}>
                  {m.label}
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </Section>

      <Divider />

      {/* ══════════════════════════════════════════════════════════════════
          3. MODULE SHOWCASE
      ══════════════════════════════════════════════════════════════════ */}
      <Section id="modules" style={{ padding: "96px 24px" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 60 }}>
            <Label><Layers size={10} /> PLATFORM MODULES</Label>
            <h2 style={{ fontSize: "clamp(24px,4vw,42px)", fontWeight: 900, marginBottom: 12 }}>
              Every Tool You Need
            </h2>
            <p style={{ color: "#64748b", fontSize: 14, maxWidth: 500, margin: "0 auto" }}>
              11 purpose-built modules covering the full intelligence lifecycle — from ingestion to reporting.
            </p>
          </div>
          <motion.div variants={stagger(0.05)} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-40px" }}
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 14 }}>
            {MODULES.map(mod => (
              <motion.div key={mod.name} variants={fadeUp}
                whileHover={{ y: -5, boxShadow: `0 12px 40px ${mod.color}18`, borderColor: `${mod.color}55` }}
                style={{ padding: "22px 20px", borderRadius: 14, cursor: "default",
                  background: "rgba(13,17,23,0.85)", border: `1px solid ${mod.color}22`,
                  transition: "all 0.25s" }}>
                <div style={{ width: 40, height: 40, borderRadius: 10, display: "flex",
                  alignItems: "center", justifyContent: "center", marginBottom: 14,
                  background: `${mod.color}12`, border: `1px solid ${mod.color}33` }}>
                  <mod.icon size={18} color={mod.color} />
                </div>
                <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8, color: "#e2e8f0" }}>{mod.name}</div>
                <div style={{ fontSize: 11, color: "#64748b", lineHeight: 1.6 }}>{mod.desc}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </Section>

      <Divider />

      {/* ══════════════════════════════════════════════════════════════════
          4. TACTICAL MAP PREVIEW
      ══════════════════════════════════════════════════════════════════ */}
      <Section id="map-preview" style={{ padding: "96px 24px", background: "rgba(0,0,0,0.4)" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 56 }}>
            <Label><Map size={10} /> TACTICAL OPERATIONS</Label>
            <h2 style={{ fontSize: "clamp(24px,4vw,42px)", fontWeight: 900, marginBottom: 12 }}>
              Command-Level Situational Awareness
            </h2>
            <p style={{ color: "#64748b", fontSize: 14, maxWidth: 520, margin: "0 auto" }}>
              Real-time tactical map with camera markers, security zone overlays, UAV tracking, and threat hotspots.
            </p>
          </div>

          {/* Simulated map UI */}
          <motion.div initial={{ opacity: 0, scale: 0.96 }} whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: "-60px" }} transition={{ duration: 0.8, ease: [0.22,1,0.36,1] }}
            style={{ borderRadius: 20, overflow: "hidden", border: "1px solid rgba(0,242,255,0.15)",
              boxShadow: "0 0 60px rgba(0,242,255,0.08)", position: "relative", height: 420,
              background: "linear-gradient(135deg,#05070a 0%,#0a1628 50%,#05070a 100%)" }}>

            {/* grid overlay */}
            <div style={{ position: "absolute", inset: 0,
              backgroundImage: "linear-gradient(rgba(0,242,255,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(0,242,255,0.04) 1px,transparent 1px)",
              backgroundSize: "32px 32px" }} />

            {/* HUD top-left */}
            <div style={{ position: "absolute", top: 20, left: 20, zIndex: 10,
              background: "rgba(5,7,10,0.9)", border: "1px solid rgba(0,242,255,0.2)",
              borderRadius: 10, padding: "12px 16px", fontFamily: "monospace" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                <motion.div animate={{ opacity: [1,0.3,1] }} transition={{ duration: 1.5, repeat: Infinity }}
                  style={{ width: 6, height: 6, borderRadius: "50%", background: "#00f2ff" }} />
                <span style={{ fontSize: 10, color: "#00f2ff", letterSpacing: "0.15em" }}>NSG TACTICAL GRID</span>
              </div>
              {[["CAMERAS","5"],["ACTIVE","4"],["ALERTS","3"]].map(([k,v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 24, fontSize: 10, color: "#64748b", marginBottom: 3 }}>
                  <span>{k}</span><span style={{ color: "#e2e8f0", fontWeight: 700 }}>{v}</span>
                </div>
              ))}
            </div>

            {/* UAV indicator */}
            <div style={{ position: "absolute", top: 20, right: 20, zIndex: 10,
              background: "rgba(5,7,10,0.9)", border: "1px solid rgba(0,242,255,0.2)",
              borderRadius: 10, padding: "10px 14px", fontFamily: "monospace" }}>
              <div style={{ fontSize: 9, color: "#64748b", letterSpacing: "0.12em", marginBottom: 4 }}>UAV ALPHA-01</div>
              <div style={{ fontSize: 11, color: "#00f2ff", fontWeight: 700 }}>28.63150, 77.21970</div>
            </div>

            {/* Animated camera dots */}
            {[
              { x: "28%", y: "35%", color: "#00f2ff", label: "CP-GATE-A",    status: "ACTIVE"  },
              { x: "45%", y: "42%", color: "#00f2ff", label: "METRO-RCH-02", status: "ACTIVE"  },
              { x: "18%", y: "65%", color: "#ef4444", label: "IGI-T3",       status: "ALERT"   },
              { x: "72%", y: "55%", color: "#f59e0b", label: "NOIDA-S18",    status: "DEGRADED"},
              { x: "60%", y: "30%", color: "#00f2ff", label: "GGN-CC-01",    status: "ACTIVE"  },
            ].map((cam, i) => (
              <div key={cam.label} style={{ position: "absolute", left: cam.x, top: cam.y, zIndex: 5 }}>
                <motion.div animate={{ scale: [1, 1.8, 1], opacity: [0.6, 0, 0.6] }}
                  transition={{ duration: 2.5, repeat: Infinity, delay: i * 0.4 }}
                  style={{ position: "absolute", inset: -8, borderRadius: "50%",
                    border: `1px solid ${cam.color}`, pointerEvents: "none" }} />
                <motion.div whileHover={{ scale: 1.3 }}
                  style={{ width: 10, height: 10, borderRadius: "50%", background: cam.color,
                    boxShadow: `0 0 10px ${cam.color}`, cursor: "pointer", position: "relative", zIndex: 2 }} />
                <div style={{ position: "absolute", top: 14, left: "50%", transform: "translateX(-50%)",
                  fontSize: 8, fontFamily: "monospace", color: cam.color, whiteSpace: "nowrap",
                  background: "rgba(5,7,10,0.8)", padding: "2px 6px", borderRadius: 4 }}>
                  {cam.label}
                </div>
              </div>
            ))}

            {/* Zone polygon simulation */}
            <div style={{ position: "absolute", left: "22%", top: "28%", width: 120, height: 80,
              border: "1px solid rgba(239,68,68,0.5)", borderRadius: 8,
              background: "rgba(239,68,68,0.05)", zIndex: 3 }}>
              <div style={{ position: "absolute", top: -18, left: 4, fontSize: 8, fontFamily: "monospace",
                color: "#ef4444", letterSpacing: "0.1em" }}>ZONE RED</div>
            </div>
            <div style={{ position: "absolute", left: "55%", top: "45%", width: 100, height: 70,
              border: "1px solid rgba(34,197,94,0.4)", borderRadius: 8,
              background: "rgba(34,197,94,0.04)", zIndex: 3 }}>
              <div style={{ position: "absolute", top: -18, left: 4, fontSize: 8, fontFamily: "monospace",
                color: "#22c55e", letterSpacing: "0.1em" }}>ZONE GREEN</div>
            </div>

            {/* UAV path */}
            <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", zIndex: 4, pointerEvents: "none" }}>
              <motion.path d="M 200 280 Q 280 220 360 260 Q 440 300 500 240"
                stroke="rgba(0,242,255,0.4)" strokeWidth="1.5" fill="none" strokeDasharray="6 4"
                initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }}
                viewport={{ once: true }} transition={{ duration: 2.5, ease: "easeInOut" }} />
            </svg>

            {/* Legend */}
            <div style={{ position: "absolute", bottom: 20, left: 20, zIndex: 10,
              background: "rgba(5,7,10,0.9)", border: "1px solid rgba(0,242,255,0.12)",
              borderRadius: 8, padding: "10px 14px", fontFamily: "monospace" }}>
              {[["#00f2ff","Active Camera"],["#ef4444","Alert Camera"],["#f59e0b","Degraded"],["#22c55e","Zone GREEN"],["#ef4444","Zone RED"]].map(([c,l]) => (
                <div key={l} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 9, color: "#94a3b8", marginBottom: 4 }}>
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: c, flexShrink: 0 }} />
                  {l}
                </div>
              ))}
            </div>

            {/* TACTICAL label */}
            <div style={{ position: "absolute", top: 20, left: "50%", transform: "translateX(-50%)", zIndex: 10,
              fontSize: 10, fontFamily: "monospace", color: "rgba(0,242,255,0.4)", letterSpacing: "0.2em" }}>
              TACTICAL VIEW — DELHI NCR
            </div>
          </motion.div>
        </div>
      </Section>

      <Divider />

      {/* ══════════════════════════════════════════════════════════════════
          5. AI CAPABILITIES
      ══════════════════════════════════════════════════════════════════ */}
      <Section id="ai" style={{ padding: "96px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 60 }}>
            <Label><Brain size={10} /> AI / ML ENGINE</Label>
            <h2 style={{ fontSize: "clamp(24px,4vw,42px)", fontWeight: 900, marginBottom: 12 }}>
              Intelligence That Never Sleeps
            </h2>
            <p style={{ color: "#64748b", fontSize: 14, maxWidth: 500, margin: "0 auto" }}>
              Six AI systems running in parallel — detecting, recognising, tracking, and analysing 24/7.
            </p>
          </div>
          <motion.div variants={stagger(0.08)} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-40px" }}
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(300px,1fr))", gap: 16 }}>
            {AI_FEATURES.map((f, i) => (
              <motion.div key={f.title} variants={fadeUp}
                whileHover={{ y: -4, boxShadow: `0 12px 40px ${f.color}18` }}
                style={{ display: "flex", gap: 16, padding: "24px 20px", borderRadius: 14,
                  background: "rgba(13,17,23,0.85)", border: `1px solid ${f.color}22`,
                  transition: "all 0.25s" }}>
                <div style={{ width: 44, height: 44, borderRadius: 12, flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  background: `${f.color}12`, border: `1px solid ${f.color}33` }}>
                  <f.icon size={20} color={f.color} />
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, color: "#e2e8f0" }}>{f.title}</div>
                  <div style={{ fontSize: 12, color: "#64748b", lineHeight: 1.65 }}>{f.desc}</div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </Section>

      <Divider />

      {/* ══════════════════════════════════════════════════════════════════
          6. LIVE ALERTS TIMELINE
      ══════════════════════════════════════════════════════════════════ */}
      <Section id="timeline" style={{ padding: "96px 24px", background: "rgba(0,0,0,0.35)" }}>
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 60 }}>
            <Label><Clock size={10} /> LIVE INCIDENT TIMELINE</Label>
            <h2 style={{ fontSize: "clamp(24px,4vw,42px)", fontWeight: 900, marginBottom: 12 }}>
              Real-Time Threat Activity
            </h2>
            <p style={{ color: "#64748b", fontSize: 14, maxWidth: 460, margin: "0 auto" }}>
              Latest incidents from the NSG VisionAI tactical grid — 13 May 2026, Delhi NCR.
            </p>
          </div>

          <div style={{ position: "relative" }}>
            {/* vertical line */}
            <motion.div initial={{ scaleY: 0 }} whileInView={{ scaleY: 1 }}
              viewport={{ once: true, margin: "-40px" }} transition={{ duration: 1.2, ease: "easeInOut" }}
              style={{ position: "absolute", left: 20, top: 0, bottom: 0, width: 1,
                background: "linear-gradient(to bottom,rgba(0,242,255,0.3),rgba(0,242,255,0.05))",
                transformOrigin: "top" }} />

            <motion.div variants={stagger(0.12)} initial="hidden" whileInView="show"
              viewport={{ once: true, margin: "-40px" }}
              style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {ALERTS_TIMELINE.map((a, i) => (
                <motion.div key={i} variants={fadeUp}
                  style={{ display: "flex", gap: 20, paddingLeft: 48, position: "relative" }}>
                  {/* dot */}
                  <motion.div animate={{ boxShadow: [`0 0 0px ${a.color}`, `0 0 12px ${a.color}`, `0 0 0px ${a.color}`] }}
                    transition={{ duration: 2.5, repeat: Infinity, delay: i * 0.5 }}
                    style={{ position: "absolute", left: 14, top: 18, width: 12, height: 12,
                      borderRadius: "50%", background: a.color, border: `2px solid ${a.color}66`, flexShrink: 0 }} />

                  <div style={{ flex: 1, padding: "16px 20px", borderRadius: 12,
                    background: "rgba(13,17,23,0.9)", border: `1px solid ${a.color}22` }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 8px", borderRadius: 4,
                          background: `${a.color}20`, border: `1px solid ${a.color}44`, color: a.color,
                          fontFamily: "monospace", letterSpacing: "0.08em" }}>{a.priority}</span>
                        <span style={{ fontSize: 12, fontWeight: 700, color: "#e2e8f0" }}>{a.type}</span>
                      </div>
                      <span style={{ fontSize: 10, fontFamily: "monospace", color: "#475569" }}>{a.time} IST</span>
                    </div>
                    <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>{a.loc}</div>
                    <div style={{ fontSize: 11, color: "#94a3b8", fontStyle: "italic" }}>{a.suspect}</div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </div>
      </Section>

      <Divider />

      {/* ══════════════════════════════════════════════════════════════════
          7. SECURITY INFRASTRUCTURE
      ══════════════════════════════════════════════════════════════════ */}
      <Section id="infra" style={{ padding: "96px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 60 }}>
            <Label><Server size={10} /> SECURITY INFRASTRUCTURE</Label>
            <h2 style={{ fontSize: "clamp(24px,4vw,42px)", fontWeight: 900, marginBottom: 12 }}>
              Defense-Grade Architecture
            </h2>
            <p style={{ color: "#64748b", fontSize: 14, maxWidth: 500, margin: "0 auto" }}>
              Built for national security — encrypted, air-gappable, and resilient under operational stress.
            </p>
          </div>

          <motion.div variants={stagger(0.07)} initial="hidden" whileInView="show"
            viewport={{ once: true, margin: "-40px" }}
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(280px,1fr))", gap: 14 }}>
            {INFRA.map((item, i) => (
              <motion.div key={item.title} variants={fadeUp}
                whileHover={{ borderColor: "rgba(0,242,255,0.3)", y: -3 }}
                style={{ display: "flex", gap: 14, padding: "20px 18px", borderRadius: 12,
                  background: "rgba(13,17,23,0.85)", border: "1px solid #1e293b",
                  transition: "all 0.2s" }}>
                <div style={{ width: 40, height: 40, borderRadius: 10, flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  background: "rgba(0,242,255,0.07)", border: "1px solid rgba(0,242,255,0.18)" }}>
                  <item.icon size={17} color="#00f2ff" />
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 13, color: "#e2e8f0", marginBottom: 6 }}>{item.title}</div>
                  <div style={{ fontSize: 11, color: "#64748b", lineHeight: 1.6 }}>{item.desc}</div>
                </div>
              </motion.div>
            ))}
          </motion.div>

          {/* Architecture flow */}
          <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }} transition={{ duration: 0.8, delay: 0.3 }}
            style={{ marginTop: 48, padding: "28px 32px", borderRadius: 16,
              background: "rgba(0,242,255,0.03)", border: "1px solid rgba(0,242,255,0.1)" }}>
            <div style={{ fontSize: 10, fontFamily: "monospace", color: "rgba(0,242,255,0.5)",
              letterSpacing: "0.15em", marginBottom: 20, textAlign: "center" }}>DATA FLOW ARCHITECTURE</div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center",
              gap: 8, flexWrap: "wrap" }}>
              {["IP CAMERA","→","RTSP INGESTER","→","REDIS STREAMS","→","YOLO WORKER","→","ALERT ENGINE","→","OPERATOR"].map((node, i) => (
                <div key={i} style={{
                  padding: node === "→" ? "0 4px" : "8px 14px",
                  borderRadius: node === "→" ? 0 : 8,
                  background: node === "→" ? "transparent" : "rgba(0,242,255,0.06)",
                  border: node === "→" ? "none" : "1px solid rgba(0,242,255,0.15)",
                  fontSize: 10, fontFamily: "monospace",
                  color: node === "→" ? "rgba(0,242,255,0.3)" : "rgba(0,242,255,0.7)",
                  fontWeight: node === "→" ? 400 : 700,
                }}>
                  {node}
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </Section>

      <Divider />

      {/* ══════════════════════════════════════════════════════════════════
          8. FINAL CTA
      ══════════════════════════════════════════════════════════════════ */}
      <Section id="cta" style={{ padding: "120px 24px", textAlign: "center",
        background: "radial-gradient(ellipse 70% 60% at 50% 100%,rgba(0,80,200,0.12) 0%,transparent 70%)" }}>
        <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }}
          viewport={{ once: true }} transition={{ duration: 0.6 }}>
          <motion.div animate={{ opacity: [0.6, 1, 0.6] }} transition={{ duration: 3, repeat: Infinity }}
            style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "5px 16px",
              borderRadius: 999, fontSize: 10, fontFamily: "monospace", letterSpacing: "0.12em",
              marginBottom: 24, background: "rgba(0,242,255,0.08)", border: "1px solid rgba(0,242,255,0.2)", color: "#67e8f9" }}>
            <Activity size={10} color="#22c55e" /> SYSTEM OPERATIONAL — ALPHA-01
          </motion.div>

          <h2 style={{ fontSize: "clamp(32px,6vw,64px)", fontWeight: 900, marginBottom: 18,
            background: "linear-gradient(135deg,#fff 0%,#00f2ff 60%,#0080ff 100%)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Ready to Secure the Nation?
          </h2>
          <p style={{ color: "#64748b", fontSize: 15, maxWidth: 440, margin: "0 auto 48px", lineHeight: 1.7 }}>
            Authenticate with your NSG service credentials to access the tactical intelligence platform.
          </p>

          <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
            <motion.button onClick={onEnter}
              whileHover={{ scale: 1.05, boxShadow: "0 0 70px rgba(0,242,255,0.7)" }}
              whileTap={{ scale: 0.97 }}
              style={{ display: "flex", alignItems: "center", gap: 14, padding: "20px 48px",
                borderRadius: 14, fontWeight: 900, fontSize: 15, letterSpacing: "0.1em",
                cursor: "pointer", border: "none",
                background: "linear-gradient(135deg,#00f2ff,#0080ff)", color: "#05070a",
                boxShadow: "0 0 44px rgba(0,242,255,0.5)" }}>
              <Shield size={20} /> ENTER PLATFORM <ChevronRight size={20} />
            </motion.button>

            <motion.a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer"
              whileHover={{ borderColor: "rgba(0,242,255,0.5)", color: "#e2e8f0", y: -2 }}
              style={{ display: "flex", alignItems: "center", gap: 10, padding: "20px 36px",
                borderRadius: 14, fontWeight: 700, fontSize: 14, letterSpacing: "0.08em",
                textDecoration: "none", background: "rgba(15,25,50,0.7)",
                border: "1px solid rgba(0,242,255,0.2)", color: "#94a3b8", transition: "all 0.2s" }}>
              <FileText size={16} /> VIEW API DOCS
            </motion.a>
          </div>

          <p style={{ marginTop: 28, fontSize: 10, fontFamily: "monospace", color: "#1e293b" }}>
            Unauthorised access is a criminal offence under IT Act 2000 &amp; Official Secrets Act 1923
          </p>
        </motion.div>
      </Section>

      {/* ── FOOTER ── */}
      <footer style={{ padding: "24px 40px", borderTop: "1px solid rgba(0,242,255,0.06)",
        display: "flex", flexWrap: "wrap", alignItems: "center",
        justifyContent: "space-between", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Shield size={13} color="rgba(0,242,255,0.35)" />
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


