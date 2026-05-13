/**
 * NSG VisionAI — Landing / Home Page
 *
 * Cinematic pre-login landing page. Shows before authentication.
 * Features: animated grid, live stat counters, feature cards,
 * capability showcase, and a prominent "Enter Platform" CTA.
 */

import { useState, useEffect, useRef } from "react";
import {
  Shield, Eye, Brain, Map, Bell, Search, FileText,
  BarChart2, Camera, Cpu, Lock, ChevronRight, Activity,
  Zap, Globe, Users, AlertTriangle, Radio, Crosshair,
} from "lucide-react";

interface HomePageProps {
  onEnter: () => void;
}

// ── Animated counter hook ─────────────────────────────────────────────────

function useCounter(target: number, duration = 2000, start = false) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime: number | null = null;
    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.floor(eased * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration, start]);
  return value;
}

// ── Typing animation hook ─────────────────────────────────────────────────

function useTyping(text: string, speed = 60, start = false) {
  const [displayed, setDisplayed] = useState("");
  useEffect(() => {
    if (!start) return;
    setDisplayed("");
    let i = 0;
    const interval = setInterval(() => {
      setDisplayed(text.slice(0, i + 1));
      i++;
      if (i >= text.length) clearInterval(interval);
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed, start]);
  return displayed;
}

// ── Feature card data ─────────────────────────────────────────────────────

const FEATURES = [
  {
    icon: Eye,
    title: "Live Video Intelligence",
    desc: "MJPEG/HLS streaming from RTSP cameras, drones, and body cams with real-time AI overlay.",
    color: "text-cyan-400",
    border: "border-cyan-500/20",
    glow: "rgba(0,242,255,0.08)",
  },
  {
    icon: Brain,
    title: "AI/ML Detection Pipeline",
    desc: "YOLOv8n object detection at 25–40 FPS. RetinaFace + ArcFace biometric recognition.",
    color: "text-purple-400",
    border: "border-purple-500/20",
    glow: "rgba(168,85,247,0.08)",
  },
  {
    icon: Map,
    title: "Tactical Map",
    desc: "Real-time camera markers, security zone polygons, UAV tracking, and threat overlays.",
    color: "text-emerald-400",
    border: "border-emerald-500/20",
    glow: "rgba(52,211,153,0.08)",
  },
  {
    icon: Bell,
    title: "Alert Management",
    desc: "P1–P4 priority alerts with acknowledge, resolve, and false-positive workflows.",
    color: "text-red-400",
    border: "border-red-500/20",
    glow: "rgba(239,68,68,0.08)",
  },
  {
    icon: Search,
    title: "Forensic Search",
    desc: "Face similarity search, object class search, zone activity, and timeline reconstruction.",
    color: "text-yellow-400",
    border: "border-yellow-500/20",
    glow: "rgba(234,179,8,0.08)",
  },
  {
    icon: Users,
    title: "Biometric Watchlist",
    desc: "ArcFace 512-dim embeddings with pgvector similarity search across all camera feeds.",
    color: "text-orange-400",
    border: "border-orange-500/20",
    glow: "rgba(249,115,22,0.08)",
  },
  {
    icon: FileText,
    title: "Intelligence Reports",
    desc: "Auto-generated classified PDF reports: incident, person, zone activity, forensic timeline.",
    color: "text-blue-400",
    border: "border-blue-500/20",
    glow: "rgba(59,130,246,0.08)",
  },
  {
    icon: BarChart2,
    title: "Mission Analytics",
    desc: "Alert trends, threat distribution, detection accuracy, camera uptime, and heatmaps.",
    color: "text-pink-400",
    border: "border-pink-500/20",
    glow: "rgba(236,72,153,0.08)",
  },
];

const STATS = [
  { label: "Camera Feeds",       value: 500,  suffix: "+",  icon: Camera,       color: "text-cyan-400"    },
  { label: "AI Detections/Day",  value: 50000, suffix: "+", icon: Brain,        color: "text-purple-400"  },
  { label: "Detection Accuracy", value: 91,   suffix: "%",  icon: Crosshair,    color: "text-emerald-400" },
  { label: "Uptime",             value: 99,   suffix: ".9%",icon: Activity,     color: "text-yellow-400"  },
  { label: "Watchlist Entries",  value: 2400, suffix: "+",  icon: Users,        color: "text-orange-400"  },
  { label: "Zones Monitored",    value: 120,  suffix: "+",  icon: Globe,        color: "text-blue-400"    },
];

const CAPABILITIES = [
  { icon: Cpu,          label: "YOLOv8n Object Detection",    sub: "80+ classes · 25–40 FPS CPU" },
  { icon: Eye,          label: "RetinaFace Detection",        sub: "96.1% precision · real-time" },
  { icon: Users,        label: "ArcFace Recognition",         sub: "512-dim · 99.83% LFW accuracy" },
  { icon: Activity,     label: "ByteTrack Person Tracking",   sub: "Cross-camera Re-ID · MOTA 80.1%" },
  { icon: Zap,          label: "LSTM Anomaly Detection",      sub: "AUC-ROC 0.934 · real-time" },
  { icon: Lock,         label: "AES-256-GCM Encryption",      sub: "All streams encrypted at rest" },
  { icon: Radio,        label: "WebSocket Alert Gateway",     sub: "Sub-100ms push to all operators" },
  { icon: Shield,       label: "JWT RS256 Authentication",    sub: "8h access · 30d refresh · RBAC" },
];

// ── Stats item (own component so hooks are valid) ────────────────────────

function StatItem({
  label, value, suffix, icon: Icon, color, start,
}: {
  label: string; value: number; suffix: string;
  icon: React.ElementType; color: string; start: boolean;
}) {
  const count = useCounter(value, 2000, start);
  return (
    <div className="flex flex-col items-center text-center gap-1">
      <Icon size={20} className={`${color} mb-1`} />
      <div className={`text-2xl font-black font-mono ${color}`}>
        {count.toLocaleString()}{suffix}
      </div>
      <div className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">{label}</div>
    </div>
  );
}

export function HomePage({ onEnter }: HomePageProps) {
  const [visible, setVisible] = useState(false);
  const [statsVisible, setStatsVisible] = useState(false);
  const statsRef = useRef<HTMLDivElement>(null);
  const featuresRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 100);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setStatsVisible(true); },
      { threshold: 0.1 }
    );
    if (statsRef.current) observer.observe(statsRef.current);
    return () => observer.disconnect();
  }, []);

  const tagline = useTyping("Sarvatra Sarvottam Suraksha", 55, visible);

  return (
    <div
      className="min-h-screen text-white"
      style={{ background: "#05070a" }}
    >
      {/* ── Animated grid background ── */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0,242,255,0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,242,255,0.025) 1px, transparent 1px)
          `,
          backgroundSize: "48px 48px",
        }}
      />

      {/* ── Top radial glow ── */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse 80% 40% at 50% -10%, rgba(0,100,255,0.12) 0%, transparent 70%)",
        }}
      />

      {/* ── Navbar ── */}
      <nav
        className="sticky top-0 z-50 flex items-center justify-between px-8 py-4 border-b"
        style={{
          background: "rgba(5,7,10,0.85)",
          backdropFilter: "blur(12px)",
          borderColor: "rgba(0,242,255,0.08)",
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center"
            style={{ background: "rgba(0,242,255,0.1)", border: "1px solid rgba(0,242,255,0.3)" }}
          >
            <Shield size={18} className="text-cyan-400" />
          </div>
          <div>
            <span className="text-base font-bold text-white tracking-tight">
              NSG <span className="text-cyan-400">VisionAI</span>
            </span>
            <div className="text-[9px] font-mono text-slate-600 tracking-widest">TACTICAL INTELLIGENCE PLATFORM</div>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-1 text-[10px] font-mono text-slate-600 bg-slate-900/60 px-3 py-1.5 rounded-full border border-slate-800">
          <Activity size={9} className="text-emerald-400" />
          <span className="ml-1">SECURE NODE: ALPHA-01</span>
          <span className="mx-2 text-slate-700">|</span>
          <span className="text-emerald-400">ONLINE</span>
        </div>

        <button
          onClick={onEnter}
          className="flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-bold transition-all"
          style={{
            background: "linear-gradient(135deg, rgba(0,242,255,0.15), rgba(0,128,255,0.15))",
            border: "1px solid rgba(0,242,255,0.3)",
            color: "#00f2ff",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "linear-gradient(135deg, rgba(0,242,255,0.25), rgba(0,128,255,0.25))";
            e.currentTarget.style.boxShadow = "0 0 20px rgba(0,242,255,0.2)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "linear-gradient(135deg, rgba(0,242,255,0.15), rgba(0,128,255,0.15))";
            e.currentTarget.style.boxShadow = "none";
          }}
        >
          <Lock size={12} /> Sign In
        </button>
      </nav>

      {/* ── Hero section ── */}
      <section className="relative flex flex-col items-center justify-center text-center px-6 pt-24 pb-20">
        {/* Classification badge */}
        <div
          className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-[10px] font-bold font-mono tracking-widest mb-8 transition-all duration-700 ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}
          style={{
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            color: "#fca5a5",
          }}
        >
          <AlertTriangle size={10} />
          RESTRICTED — AUTHORISED PERSONNEL ONLY
          <AlertTriangle size={10} />
        </div>

        {/* Main headline */}
        <h1
          className={`text-5xl md:text-7xl font-black tracking-tight mb-4 transition-all duration-700 delay-100 ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`}
          style={{
            background: "linear-gradient(135deg, #ffffff 0%, #00f2ff 50%, #0080ff 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            lineHeight: 1.1,
          }}
        >
          NSG VisionAI
        </h1>

        {/* Tagline typing effect */}
        <div
          className={`text-lg md:text-xl font-mono text-cyan-400/80 mb-3 h-8 transition-all duration-700 delay-200 ${visible ? "opacity-100" : "opacity-0"}`}
        >
          "{tagline}"
          <span className="animate-pulse">_</span>
        </div>

        <p
          className={`text-slate-400 text-sm md:text-base max-w-2xl leading-relaxed mb-10 transition-all duration-700 delay-300 ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}
        >
          Defense-grade AI/ML surveillance platform for India's National Security Guard.
          Real-time video intelligence, biometric recognition, and tactical situational awareness
          — unified in a single secure dashboard.
        </p>

        {/* CTA buttons */}
        <div
          className={`flex flex-col sm:flex-row gap-4 transition-all duration-700 delay-400 ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}
        >
          <button
            onClick={onEnter}
            className="group flex items-center justify-center gap-3 px-8 py-4 rounded-xl font-bold text-sm tracking-widest transition-all"
            style={{
              background: "linear-gradient(135deg, #00f2ff, #0080ff)",
              color: "#05070a",
              boxShadow: "0 0 30px rgba(0,242,255,0.4), 0 4px 20px rgba(0,0,0,0.4)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = "0 0 50px rgba(0,242,255,0.6), 0 4px 20px rgba(0,0,0,0.4)";
              e.currentTarget.style.transform = "translateY(-2px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = "0 0 30px rgba(0,242,255,0.4), 0 4px 20px rgba(0,0,0,0.4)";
              e.currentTarget.style.transform = "translateY(0)";
            }}
          >
            <Shield size={16} />
            ENTER PLATFORM
            <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
          </button>

          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 px-8 py-4 rounded-xl font-bold text-sm tracking-widest transition-all"
            style={{
              background: "rgba(15,25,50,0.6)",
              border: "1px solid rgba(0,242,255,0.2)",
              color: "#94a3b8",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "rgba(0,242,255,0.4)";
              e.currentTarget.style.color = "#e2e8f0";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(0,242,255,0.2)";
              e.currentTarget.style.color = "#94a3b8";
            }}
          >
            <FileText size={16} />
            API DOCUMENTATION
          </a>
        </div>

        {/* Scroll indicator — clicks scroll to stats section */}
        <button
          onClick={() => statsRef.current?.scrollIntoView({ behavior: "smooth" })}
          className="mt-16 flex flex-col items-center gap-2 text-slate-600 hover:text-slate-400 transition-colors cursor-pointer"
        >
          <span className="text-[10px] font-mono tracking-widest">SCROLL TO EXPLORE</span>
          <div className="flex flex-col items-center gap-1 animate-bounce">
            <div className="w-px h-6 bg-gradient-to-b from-slate-600 to-transparent" />
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400/50" />
          </div>
        </button>
      </section>

      {/* ── Live stats bar ── */}
      <section
        ref={statsRef}
        id="stats"
        className="px-6 py-12 border-y"
        style={{ borderColor: "rgba(0,242,255,0.08)", background: "rgba(0,242,255,0.02)" }}
      >
        <div className="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
          {STATS.map(({ label, value, suffix, icon, color }) => (
            <StatItem
              key={label}
              label={label}
              value={value}
              suffix={suffix}
              icon={icon}
              color={color}
              start={statsVisible}
            />
          ))}
        </div>
      </section>

      {/* ── Features grid ── */}
      <section className="px-6 py-20 max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <div className="text-[10px] font-mono text-cyan-400/60 tracking-widest mb-3">PLATFORM CAPABILITIES</div>
          <h2 className="text-3xl md:text-4xl font-black text-white mb-4">
            Full-Spectrum Surveillance Intelligence
          </h2>
          <p className="text-slate-500 text-sm max-w-xl mx-auto">
            Every module purpose-built for national security operations — from real-time detection to forensic analysis.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {FEATURES.map(({ icon: Icon, title, desc, color, border, glow }) => (
            <div
              key={title}
              className={`group relative rounded-xl p-5 border transition-all duration-300 cursor-default ${border}`}
              style={{ background: `rgba(13,17,23,0.8)` }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLDivElement).style.background = glow;
                (e.currentTarget as HTMLDivElement).style.transform = "translateY(-3px)";
                (e.currentTarget as HTMLDivElement).style.boxShadow = `0 8px 30px ${glow}`;
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLDivElement).style.background = "rgba(13,17,23,0.8)";
                (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
                (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
              }}
            >
              <div
                className={`w-10 h-10 rounded-lg flex items-center justify-center mb-4 ${color}`}
                style={{ background: `${glow}`, border: `1px solid currentColor`, opacity: 0.9 }}
              >
                <Icon size={18} />
              </div>
              <h3 className="text-sm font-bold text-white mb-2">{title}</h3>
              <p className="text-[11px] text-slate-500 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Tech capabilities strip ── */}
      <section
        className="px-6 py-16 border-y"
        style={{ borderColor: "rgba(0,242,255,0.06)", background: "rgba(0,0,0,0.3)" }}
      >
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-10">
            <div className="text-[10px] font-mono text-cyan-400/60 tracking-widest mb-2">TECHNICAL SPECIFICATIONS</div>
            <h2 className="text-2xl font-black text-white">AI/ML Engine</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {CAPABILITIES.map(({ icon: Icon, label, sub }) => (
              <div
                key={label}
                className="flex items-start gap-3 p-4 rounded-lg border border-slate-800 bg-slate-900/40 hover:border-slate-700 transition-colors"
              >
                <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0">
                  <Icon size={14} className="text-cyan-400" />
                </div>
                <div>
                  <p className="text-xs font-bold text-slate-200">{label}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5 font-mono">{sub}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Role access section ── */}
      <section className="px-6 py-20 max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <div className="text-[10px] font-mono text-cyan-400/60 tracking-widest mb-3">ACCESS CONTROL</div>
          <h2 className="text-3xl font-black text-white mb-3">Role-Based Access</h2>
          <p className="text-slate-500 text-sm">Four clearance levels — each with precisely scoped permissions.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              role: "OPERATOR",
              color: "text-blue-400",
              border: "border-blue-500/20",
              bg: "rgba(59,130,246,0.05)",
              access: ["Dashboard", "Live Feeds", "Webcam AI", "Tactical Map", "Alerts"],
              badge: "L1",
            },
            {
              role: "ANALYST",
              color: "text-emerald-400",
              border: "border-emerald-500/20",
              bg: "rgba(52,211,153,0.05)",
              access: ["All Operator", "Forensics", "Watchlist", "Reports", "Analytics"],
              badge: "L2",
            },
            {
              role: "COMMANDER",
              color: "text-yellow-400",
              border: "border-yellow-500/20",
              bg: "rgba(234,179,8,0.05)",
              access: ["All Analyst", "Mission Control", "Priority Alerts", "Zone Management"],
              badge: "L3",
            },
            {
              role: "ADMIN",
              color: "text-red-400",
              border: "border-red-500/20",
              bg: "rgba(239,68,68,0.05)",
              access: ["Full Access", "ML Models", "Audit Logs", "User Management", "System Health"],
              badge: "L4",
            },
          ].map(({ role, color, border, bg, access, badge }) => (
            <div
              key={role}
              className={`rounded-xl p-5 border ${border}`}
              style={{ background: bg }}
            >
              <div className="flex items-center justify-between mb-4">
                <span className={`text-sm font-black ${color}`}>{role}</span>
                <span
                  className={`text-[9px] font-bold px-2 py-0.5 rounded-full border ${color} ${border}`}
                  style={{ background: bg }}
                >
                  {badge}
                </span>
              </div>
              <ul className="space-y-1.5">
                {access.map((item) => (
                  <li key={item} className="flex items-center gap-2 text-[11px] text-slate-400">
                    <div className={`w-1 h-1 rounded-full ${color.replace("text-", "bg-")}`} />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section
        className="px-6 py-24 text-center border-t"
        style={{ borderColor: "rgba(0,242,255,0.08)", background: "rgba(0,242,255,0.02)" }}
      >
        <div
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-[10px] font-bold font-mono tracking-widest mb-6"
          style={{
            background: "rgba(0,242,255,0.08)",
            border: "1px solid rgba(0,242,255,0.2)",
            color: "#67e8f9",
          }}
        >
          <Activity size={10} className="text-emerald-400" />
          SYSTEM OPERATIONAL — ALPHA-01
        </div>

        <h2
          className="text-4xl md:text-5xl font-black mb-4"
          style={{
            background: "linear-gradient(135deg, #ffffff, #00f2ff)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          Ready to Secure the Nation?
        </h2>
        <p className="text-slate-500 text-sm mb-10 max-w-md mx-auto">
          Authenticate with your NSG service credentials to access the tactical intelligence platform.
        </p>

        <button
          onClick={onEnter}
          className="group inline-flex items-center gap-3 px-10 py-5 rounded-xl font-black text-base tracking-widest transition-all"
          style={{
            background: "linear-gradient(135deg, #00f2ff, #0080ff)",
            color: "#05070a",
            boxShadow: "0 0 40px rgba(0,242,255,0.5), 0 8px 30px rgba(0,0,0,0.5)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = "0 0 60px rgba(0,242,255,0.7), 0 8px 30px rgba(0,0,0,0.5)";
            e.currentTarget.style.transform = "translateY(-3px) scale(1.02)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = "0 0 40px rgba(0,242,255,0.5), 0 8px 30px rgba(0,0,0,0.5)";
            e.currentTarget.style.transform = "translateY(0) scale(1)";
          }}
        >
          <Shield size={20} />
          ENTER PLATFORM
          <ChevronRight size={20} className="group-hover:translate-x-1 transition-transform" />
        </button>

        <p className="text-slate-700 text-[10px] font-mono mt-6">
          Unauthorised access is a criminal offence under IT Act 2000 & Official Secrets Act 1923
        </p>
      </section>

      {/* ── Footer ── */}
      <footer
        className="px-8 py-6 border-t flex flex-col md:flex-row items-center justify-between gap-3"
        style={{ borderColor: "rgba(0,242,255,0.06)" }}
      >
        <div className="flex items-center gap-2">
          <Shield size={14} className="text-cyan-400/50" />
          <span className="text-[10px] font-mono text-slate-600">
            NSG VisionAI v1.0.0 — Ministry of Home Affairs, India
          </span>
        </div>
        <div className="text-[10px] font-mono text-slate-700">
          © 2024–2026 National Security Guard · All Rights Reserved
        </div>
        <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-700">
          <Lock size={10} />
          AES-256-GCM · JWT RS256 · TLS 1.3
        </div>
      </footer>
    </div>
  );
}
