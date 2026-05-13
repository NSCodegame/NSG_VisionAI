/**
 * NSG VisionAI — Main Application
 *
 * Tab-based routing with auth guard.
 * Routes: login | dashboard | feeds | map | alerts | forensics | watchlist | reports | analytics | admin
 */

import { useState, useEffect } from "react";
import { Shield, Activity, Users, Map, Settings, Bell, Monitor, LayoutGrid, FileText, BarChart2, Lock, Search, Camera } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// Pages
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { HomePage } from "./pages/HomePage";
import { DashboardPage } from "./pages/DashboardPage";
import { AlertsPage } from "./pages/AlertsPage";
import { ForensicsPage } from "./pages/ForensicsPage";
import { ReportsPage } from "./pages/ReportsPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { AdminPage } from "./pages/AdminPage";
import { FeedsPage } from "./pages/FeedsPage";
import { WebcamPage } from "./pages/WebcamPage";
import { IPCameraPage } from "./pages/IPCameraPage";

// Components (existing)
import { WatchlistManager } from "./components/WatchlistManager";
import { TacticalMap } from "./components/TacticalMap";

// Stores
import { useAuthStore, useAlertStore, useUIStore } from "./stores";
import type { Role } from "./types";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ---------------------------------------------------------------------------
// Navigation items
// ---------------------------------------------------------------------------

interface NavItem {
  id: string;
  label: string;
  icon: React.ElementType;
  minRole?: Role;
}

const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "DASHBOARD", icon: Monitor },
  { id: "feeds", label: "FEEDS", icon: LayoutGrid },
  { id: "ip-camera", label: "IP CAMERAS", icon: Camera },
  { id: "webcam", label: "WEBCAM AI", icon: Activity },
  { id: "map", label: "TACTICAL MAP", icon: Map },
  { id: "alerts", label: "ALERTS", icon: Bell },
  { id: "forensics", label: "FORENSICS", icon: Search, minRole: 'ANALYST' },
  { id: "watchlist", label: "WATCHLIST", icon: Users, minRole: 'ANALYST' },
  { id: "reports", label: "REPORTS", icon: FileText, minRole: 'ANALYST' },
  { id: "analytics", label: "ANALYTICS", icon: BarChart2, minRole: 'ANALYST' },
  { id: "admin", label: "ADMIN", icon: Settings, minRole: 'ADMIN' },
];

const ROLE_HIERARCHY: Record<Role, number> = {
  OPERATOR: 1,
  ANALYST: 2,
  COMMANDER: 3,
  SUPER_ADMIN: 4,
  ADMIN: 4, // Mapping both for safety
} as any;

function hasAccess(userRole: Role, minRole?: Role): boolean {
  if (!minRole) return true;
  return ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[minRole];
}

// ---------------------------------------------------------------------------
// Sidebar item
// ---------------------------------------------------------------------------

function SidebarItem({ item, active, onClick }: { item: NavItem; active: boolean; onClick: () => void }) {
  const Icon = item.icon;
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-150 group relative text-left",
        active
          ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
          : "text-slate-500 hover:text-slate-200 hover:bg-slate-800/50"
      )}
    >
      <Icon size={16} className={cn(active ? "" : "group-hover:scale-110 transition-transform")} />
      <span className="text-xs font-bold tracking-wider truncate">{item.label}</span>
      {active && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-cyan-400 rounded-r-full" />
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Top navigation bar
// ---------------------------------------------------------------------------

function TopBar({ onTabChange }: { activeTab: string; onTabChange: (tab: string) => void }) {
  const { user } = useAuthStore();
  const { unreadCount } = useAlertStore();
  const { logout } = useAuthStore();

  const criticalCount = useAlertStore((s) =>
    s.alerts.filter((a) => a.priority === "P1_CRITICAL" && a.status === "ACTIVE").length
  );

  return (
    <header className="h-14 flex items-center justify-between px-4 border-b border-blue-500/10 bg-[#0d1117]/80 backdrop-blur-sm z-20 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Shield size={22} className="text-cyan-400" />
          <span className="text-base font-bold tracking-tight text-white">
            NSG <span className="text-cyan-400">VisionAI</span>
          </span>
        </div>
        <div className="hidden sm:flex items-center gap-1.5 text-[10px] font-mono text-slate-600 bg-slate-900/50 px-2.5 py-1 rounded-full border border-slate-800">
          <Activity size={10} className="text-emerald-400" />
          SECURE NODE: ALPHA-01
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* Alert badge */}
        <button
          onClick={() => onTabChange("alerts")}
          className="relative p-2 text-slate-500 hover:text-slate-200 transition-colors"
        >
          <Bell size={18} />
          {unreadCount > 0 && (
            <span className={cn(
              "absolute -top-0.5 -right-0.5 min-w-[16px] h-4 rounded-full text-[9px] font-bold flex items-center justify-center px-1",
              criticalCount > 0 ? "bg-red-500 text-white animate-pulse" : "bg-slate-600 text-slate-200"
            )}>
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </button>

        {/* User info */}
        {user && (
          <div className="flex items-center gap-2 pl-3 border-l border-slate-800">
            <div className="text-right hidden sm:block">
              <p className="text-xs font-bold text-slate-200">{user.full_name}</p>
              <p className="text-[10px] text-slate-500 font-mono">{user.role} · {user.unit}</p>
            </div>
            <button
              onClick={logout}
              title="Logout"
              className="p-1.5 text-slate-600 hover:text-red-400 transition-colors"
            >
              <Lock size={14} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

// ---------------------------------------------------------------------------
// Main App
// ---------------------------------------------------------------------------

export default function App() {
  const { user, token } = useAuthStore();
  const { activeTab, setActiveTab } = useUIStore();
  const [isAuthenticated, setIsAuthenticated] = useState(!!token);
  const [showRegister, setShowRegister] = useState(false);
  const [showHome, setShowHome] = useState(!token); // show landing page if not logged in

  useEffect(() => {
    setIsAuthenticated(!!token);
    if (token) setShowHome(false);
  }, [token]);

  // Landing page — shown before login
  if (!isAuthenticated && showHome) {
    return <HomePage onEnter={() => setShowHome(false)} />;
  }

  if (!isAuthenticated) {
    if (showRegister) {
      return <RegisterPage onNavigateToLogin={() => setShowRegister(false)} />;
    }
    return (
      <LoginPage
        onLoginSuccess={() => setIsAuthenticated(true)}
        onNavigateToRegister={() => setShowRegister(true)}
      />
    );
  }

  const userRole = (user?.role as Role) ?? ('OPERATOR' as Role);
  const visibleNav = NAV_ITEMS.filter((item) => hasAccess(userRole, item.minRole));

  const renderPage = () => {
    switch (activeTab) {
      case "dashboard":
        return <DashboardPage />;
      case "alerts":
        return <AlertsPage />;
      case "map":
        return (
          <div className="h-full p-4">
            <TacticalMap
              dronePos={[28.5355, 77.391]}
              history={[[28.53, 77.38], [28.532, 77.385], [28.5355, 77.391]]}
              center={[28.5355, 77.391]}
              zoom={14}
            />
          </div>
        );
      case "analytics":
        return <AnalyticsPage />;
      case "watchlist":
        return (
          <div className="h-full overflow-y-auto p-4">
            <WatchlistManager />
          </div>
        );
      case "forensics":
        return <ForensicsPage />;
      case "reports":
        return <ReportsPage />;
      case "analytics":
        return <AnalyticsPage />;
      case "feeds":
        return <FeedsPage />;
      case "ip-camera":
        return <IPCameraPage />;
      case "webcam":
        return <WebcamPage />;
      case "admin":
        return <AdminPage />;
      default:
        return <DashboardPage />;
    }
  };

  return (
    <div className="h-screen w-full flex flex-col overflow-hidden bg-[#05070a] text-white">
      <TopBar activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-52 shrink-0 border-r border-blue-500/10 bg-[#0d1117]/60 flex flex-col py-3 px-2 gap-1">
          {visibleNav.map((item) => (
            <SidebarItem
              key={item.id}
              item={item}
              active={activeTab === item.id}
              onClick={() => setActiveTab(item.id)}
            />
          ))}
        </aside>

        {/* Page content */}
        <main className="flex-1 overflow-hidden bg-[#05070a]">
          {renderPage()}
        </main>
      </div>
    </div>
  );
}
