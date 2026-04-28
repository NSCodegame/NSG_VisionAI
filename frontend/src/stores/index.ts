/**
 * Zustand Stores — Phase 23.5
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, Alert, VideoFeed, TrackedPerson } from "../types";

// ---------------------------------------------------------------------------
// Auth Store
// ---------------------------------------------------------------------------

interface AuthState {
  user: User | null;
  token: string | null;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setAuth: (user, token) => set({ user, token }),
      logout: () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        set({ user: null, token: null });
      },
    }),
    { name: "nsg-auth" }
  )
);

// ---------------------------------------------------------------------------
// Alert Store
// ---------------------------------------------------------------------------

interface AlertState {
  alerts: Alert[];
  unreadCount: number;
  addAlert: (alert: Alert) => void;
  acknowledgeAlert: (alertId: string) => void;
  setAlerts: (alerts: Alert[]) => void;
  clearAlerts: () => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  alerts: [],
  unreadCount: 0,

  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts].slice(0, 200), // Keep last 200
      unreadCount: state.unreadCount + 1,
    })),

  acknowledgeAlert: (alertId) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a.id === alertId ? { ...a, status: "ACKNOWLEDGED" as const } : a
      ),
      unreadCount: Math.max(0, state.unreadCount - 1),
    })),

  setAlerts: (alerts) =>
    set({
      alerts,
      unreadCount: alerts.filter((a) => a.status === "ACTIVE").length,
    }),

  clearAlerts: () => set({ alerts: [], unreadCount: 0 }),
}));

// ---------------------------------------------------------------------------
// Feed Store
// ---------------------------------------------------------------------------

interface FeedState {
  feeds: VideoFeed[];
  selectedFeedId: string | null;
  setFeeds: (feeds: VideoFeed[]) => void;
  selectFeed: (feedId: string | null) => void;
  updateFeedStatus: (feedId: string, status: VideoFeed["status"]) => void;
}

export const useFeedStore = create<FeedState>((set) => ({
  feeds: [],
  selectedFeedId: null,

  setFeeds: (feeds) => set({ feeds }),

  selectFeed: (feedId) => set({ selectedFeedId: feedId }),

  updateFeedStatus: (feedId, status) =>
    set((state) => ({
      feeds: state.feeds.map((f) => (f.id === feedId ? { ...f, status } : f)),
    })),
}));

// ---------------------------------------------------------------------------
// Tracked Person Store
// ---------------------------------------------------------------------------

interface TrackedPersonState {
  persons: TrackedPerson[];
  setPersons: (persons: TrackedPerson[]) => void;
  updatePerson: (person: TrackedPerson) => void;
}

export const useTrackedPersonStore = create<TrackedPersonState>((set) => ({
  persons: [],

  setPersons: (persons) => set({ persons }),

  updatePerson: (person) =>
    set((state) => ({
      persons: state.persons.some((p) => p.id === person.id)
        ? state.persons.map((p) => (p.id === person.id ? person : p))
        : [person, ...state.persons],
    })),
}));

// ---------------------------------------------------------------------------
// UI Store
// ---------------------------------------------------------------------------

type GridLayout = "1x1" | "2x2" | "3x2" | "4x3";

interface UIState {
  gridLayout: GridLayout;
  sidebarOpen: boolean;
  activeTab: string;
  setGridLayout: (layout: GridLayout) => void;
  toggleSidebar: () => void;
  setActiveTab: (tab: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  gridLayout: "2x2",
  sidebarOpen: true,
  activeTab: "dashboard",

  setGridLayout: (layout) => set({ gridLayout: layout }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setActiveTab: (tab) => set({ activeTab: tab }),
}));
