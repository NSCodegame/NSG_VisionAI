/**
 * TacticalMap — Full tactical surveillance map
 *
 * Features:
 * - Dark OpenStreetMap tiles (CartoDB Dark Matter — free, no API key)
 * - Camera feed markers with status colours
 * - Security zone polygons with threat-level colours
 * - Drone position + flight path
 * - Live alert count badges
 * - Click camera marker to see feed details
 */

import { useEffect, useState, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  Polygon,
  Circle,
  useMap,
  ZoomControl,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Camera, Shield, AlertTriangle, Navigation, Crosshair, Layers, RefreshCw } from "lucide-react";
import apiClient from "../services/api";

// ── Fix Leaflet default icon paths broken by Vite bundling ──────────────────
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

// @ts-ignore
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

// ── Custom SVG icons ─────────────────────────────────────────────────────────

function makeSvgIcon(svg: string, size = 28): L.DivIcon {
  return L.divIcon({
    html: svg,
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

const CAMERA_ICONS: Record<string, L.DivIcon> = {
  ACTIVE: makeSvgIcon(
    `<svg viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="14" cy="14" r="13" fill="#0d1117" stroke="#00f2ff" stroke-width="1.5"/>
      <rect x="6" y="10" width="10" height="8" rx="1.5" fill="#00f2ff"/>
      <polygon points="16,11 22,8 22,20 16,17" fill="#00f2ff"/>
      <circle cx="14" cy="14" r="2" fill="#0d1117"/>
    </svg>`, 28
  ),
  OFFLINE: makeSvgIcon(
    `<svg viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="14" cy="14" r="13" fill="#0d1117" stroke="#475569" stroke-width="1.5"/>
      <rect x="6" y="10" width="10" height="8" rx="1.5" fill="#475569"/>
      <polygon points="16,11 22,8 22,20 16,17" fill="#475569"/>
    </svg>`, 28
  ),
  ALERT: makeSvgIcon(
    `<svg viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="14" cy="14" r="13" fill="#0d1117" stroke="#ef4444" stroke-width="2"/>
      <rect x="6" y="10" width="10" height="8" rx="1.5" fill="#ef4444"/>
      <polygon points="16,11 22,8 22,20 16,17" fill="#ef4444"/>
      <circle cx="14" cy="14" r="2" fill="#0d1117"/>
    </svg>`, 28
  ),
  DEGRADED: makeSvgIcon(
    `<svg viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="14" cy="14" r="13" fill="#0d1117" stroke="#f59e0b" stroke-width="1.5"/>
      <rect x="6" y="10" width="10" height="8" rx="1.5" fill="#f59e0b"/>
      <polygon points="16,11 22,8 22,20 16,17" fill="#f59e0b"/>
    </svg>`, 28
  ),
};

const DRONE_ICON = makeSvgIcon(
  `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="16" cy="16" r="15" fill="#0d1117" stroke="#00f2ff" stroke-width="1.5"/>
    <circle cx="8"  cy="8"  r="3" fill="#00f2ff" opacity="0.7"/>
    <circle cx="24" cy="8"  r="3" fill="#00f2ff" opacity="0.7"/>
    <circle cx="8"  cy="24" r="3" fill="#00f2ff" opacity="0.7"/>
    <circle cx="24" cy="24" r="3" fill="#00f2ff" opacity="0.7"/>
    <rect x="14" y="10" width="4" height="12" rx="2" fill="#00f2ff"/>
    <rect x="10" y="14" width="12" height="4" rx="2" fill="#00f2ff"/>
    <circle cx="16" cy="16" r="3" fill="#0d1117" stroke="#00f2ff" stroke-width="1.5"/>
  </svg>`, 32
);

// ── Zone colours ─────────────────────────────────────────────────────────────

const ZONE_STYLES: Record<string, { color: string; fillColor: string; fillOpacity: number }> = {
  GREEN:    { color: "#22c55e", fillColor: "#22c55e", fillOpacity: 0.08 },
  AMBER:    { color: "#f59e0b", fillColor: "#f59e0b", fillOpacity: 0.10 },
  RED:      { color: "#ef4444", fillColor: "#ef4444", fillOpacity: 0.12 },
  CRITICAL: { color: "#dc2626", fillColor: "#dc2626", fillOpacity: 0.18 },
};

// ── Types ────────────────────────────────────────────────────────────────────

interface Feed {
  id: string;
  name: string;
  feed_type: string;
  status: string;
  latitude?: number;
  longitude?: number;
  location_name?: string;
  zone_id?: string;
}

interface Zone {
  id: string;
  name: string;
  zone_type: string;
  threat_level: string;
  polygon_coordinates: unknown;
}

interface TacticalMapProps {
  dronePos?: [number, number];
  history?: [number, number][];
  center?: [number, number];
  zoom?: number;
}

// ── Auto-center helper ───────────────────────────────────────────────────────

function FlyTo({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, zoom, { duration: 1.5 });
  }, [center, zoom, map]);
  return null;
}

// ── Main component ───────────────────────────────────────────────────────────

export const TacticalMap = ({
  dronePos = [28.5355, 77.391],
  history = [],
  center,
  zoom = 15,
}: TacticalMapProps) => {
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(false);
  const [mapCenter, setMapCenter] = useState<[number, number]>(center ?? dronePos);
  const [mapZoom, setMapZoom] = useState(zoom);
  const [flyTarget, setFlyTarget] = useState<{ center: [number, number]; zoom: number } | null>(null);
  const [tileLayer, setTileLayer] = useState<"dark" | "satellite" | "osm">("dark");

  // Load feeds and zones
  const loadData = async () => {
    setLoading(true);
    try {
      const [feedsRes, zonesRes] = await Promise.allSettled([
        apiClient.get("/feeds"),
        apiClient.get("/zones"),
      ]);

      if (feedsRes.status === "fulfilled") {
        const data = feedsRes.value.data;
        setFeeds(Array.isArray(data) ? data : data?.feeds ?? []);
      }
      if (zonesRes.status === "fulfilled") {
        const data = zonesRes.value.data;
        setZones(Array.isArray(data) ? data : data?.zones ?? []);
      }
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  // Feeds with valid GPS coordinates
  const mappedFeeds = feeds.filter(
    (f) => f.latitude != null && f.longitude != null &&
           Math.abs(f.latitude!) > 0.001 && Math.abs(f.longitude!) > 0.001
  );

  // Parse zone polygon coordinates
  const parsedZones = zones.map((z) => {
    let coords: [number, number][] = [];
    try {
      const raw = z.polygon_coordinates;
      if (Array.isArray(raw)) {
        // Could be [[lat,lng], ...] or [{lat,lng}, ...]
        coords = raw.map((p: unknown) => {
          if (Array.isArray(p)) return [p[0], p[1]] as [number, number];
          const obj = p as Record<string, number>;
          return [obj.lat ?? obj.y, obj.lng ?? obj.lon ?? obj.x] as [number, number];
        });
      }
    } catch { /* ignore */ }
    return { ...z, coords };
  }).filter((z) => z.coords.length >= 3);

  const TILE_URLS = {
    dark:      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    satellite: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    osm:       "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  };

  const TILE_ATTRS = {
    dark:      '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
    satellite: '&copy; <a href="https://www.esri.com/">Esri</a>',
    osm:       '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  };

  const activeFeedsCount = feeds.filter((f) => f.status === "ACTIVE").length;
  const alertFeedsCount  = feeds.filter((f) => f.status === "ALERT").length;
  const criticalZones    = zones.filter((z) => z.threat_level === "CRITICAL" || z.threat_level === "RED").length;

  return (
    <div className="h-full w-full relative rounded-xl overflow-hidden border border-blue-500/10">

      {/* ── HUD top-left ── */}
      <div className="absolute top-3 left-3 z-[1000] flex flex-col gap-2 pointer-events-none">
        <div className="bg-[#0d1117]/90 backdrop-blur border border-cyan-500/20 px-3 py-2 rounded-lg">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[10px] font-mono font-bold text-cyan-400 tracking-widest">NSG TACTICAL GRID</span>
          </div>
          <div className="grid grid-cols-3 gap-3 text-[10px] font-mono">
            <div>
              <p className="text-slate-500 uppercase">Cameras</p>
              <p className="text-cyan-400 font-bold">{feeds.length}</p>
            </div>
            <div>
              <p className="text-slate-500 uppercase">Active</p>
              <p className="text-emerald-400 font-bold">{activeFeedsCount}</p>
            </div>
            <div>
              <p className="text-slate-500 uppercase">Alerts</p>
              <p className={`font-bold ${alertFeedsCount > 0 ? "text-red-400" : "text-slate-400"}`}>
                {alertFeedsCount}
              </p>
            </div>
          </div>
        </div>

        {criticalZones > 0 && (
          <div className="bg-red-900/80 backdrop-blur border border-red-500/40 px-3 py-1.5 rounded-lg flex items-center gap-2 pointer-events-none">
            <AlertTriangle size={11} className="text-red-400" />
            <span className="text-[10px] font-mono text-red-300 font-bold">
              {criticalZones} CRITICAL ZONE{criticalZones > 1 ? "S" : ""}
            </span>
          </div>
        )}

        {dronePos && (
          <div className="bg-[#0d1117]/90 backdrop-blur border border-cyan-500/20 px-3 py-2 rounded-lg">
            <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider mb-0.5">UAV ALPHA-01</p>
            <p className="text-[10px] font-mono text-cyan-400 font-bold">
              {dronePos[0].toFixed(5)}, {dronePos[1].toFixed(5)}
            </p>
          </div>
        )}
      </div>

      {/* ── Controls top-right ── */}
      <div className="absolute top-3 right-3 z-[1000] flex flex-col gap-1.5">
        {/* Tile layer switcher */}
        <div className="bg-[#0d1117]/90 backdrop-blur border border-blue-500/20 rounded-lg overflow-hidden">
          {(["dark", "satellite", "osm"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTileLayer(t)}
              className={`block w-full px-3 py-1.5 text-[10px] font-mono font-bold uppercase tracking-wider transition-colors ${
                tileLayer === t
                  ? "bg-cyan-500/20 text-cyan-400"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {t === "dark" ? "TACTICAL" : t === "satellite" ? "SATELLITE" : "STREET"}
            </button>
          ))}
        </div>

        {/* Refresh */}
        <button
          onClick={loadData}
          disabled={loading}
          className="p-2 bg-[#0d1117]/90 backdrop-blur border border-blue-500/20 text-cyan-400 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
          title="Refresh feeds & zones"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>

        {/* Center on drone */}
        {dronePos && (
          <button
            onClick={() => setFlyTarget({ center: dronePos, zoom: 16 })}
            className="p-2 bg-[#0d1117]/90 backdrop-blur border border-blue-500/20 text-cyan-400 rounded-lg hover:bg-slate-800 transition-colors"
            title="Center on drone"
          >
            <Crosshair size={14} />
          </button>
        )}
      </div>

      {/* ── Legend bottom-left ── */}
      <div className="absolute bottom-8 left-3 z-[1000] bg-[#0d1117]/90 backdrop-blur border border-blue-500/20 px-3 py-2 rounded-lg pointer-events-none">
        <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider mb-1.5">LEGEND</p>
        <div className="space-y-1">
          {[
            { colour: "bg-cyan-400",   label: "Active Camera" },
            { colour: "bg-red-400",    label: "Alert Camera" },
            { colour: "bg-yellow-400", label: "Degraded" },
            { colour: "bg-slate-500",  label: "Offline" },
            { colour: "bg-emerald-400 opacity-60", label: "Zone GREEN" },
            { colour: "bg-yellow-400 opacity-60",  label: "Zone AMBER" },
            { colour: "bg-red-500 opacity-60",     label: "Zone RED/CRITICAL" },
          ].map(({ colour, label }) => (
            <div key={label} className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${colour}`} />
              <span className="text-[9px] font-mono text-slate-400">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Map ── */}
      <MapContainer
        center={mapCenter}
        zoom={mapZoom}
        scrollWheelZoom
        className="h-full w-full"
        zoomControl={false}
        style={{ background: "#0d1117" }}
      >
        <ZoomControl position="bottomright" />

        <TileLayer
          key={tileLayer}
          attribution={TILE_ATTRS[tileLayer]}
          url={TILE_URLS[tileLayer]}
          maxZoom={19}
        />

        {/* Fly animation */}
        {flyTarget && (
          <FlyTo center={flyTarget.center} zoom={flyTarget.zoom} />
        )}

        {/* Security zone polygons */}
        {parsedZones.map((zone) => {
          const style = ZONE_STYLES[zone.threat_level] ?? ZONE_STYLES.GREEN;
          return (
            <Polygon
              key={zone.id}
              positions={zone.coords}
              pathOptions={{
                color: style.color,
                fillColor: style.fillColor,
                fillOpacity: style.fillOpacity,
                weight: 2,
                dashArray: zone.threat_level === "CRITICAL" ? "8,4" : undefined,
              }}
            >
              <Popup>
                <div className="font-mono text-xs bg-[#0d1117] text-white p-2 rounded min-w-[160px]">
                  <p className="font-bold text-cyan-400 border-b border-slate-700 pb-1 mb-1">{zone.name}</p>
                  <p className="text-slate-400">Type: <span className="text-white">{zone.zone_type}</span></p>
                  <p className="text-slate-400">Threat: <span style={{ color: style.color }}>{zone.threat_level}</span></p>
                </div>
              </Popup>
            </Polygon>
          );
        })}

        {/* Camera feed markers */}
        {mappedFeeds.map((feed) => {
          const icon = CAMERA_ICONS[feed.status] ?? CAMERA_ICONS.OFFLINE;
          return (
            <Marker
              key={feed.id}
              position={[feed.latitude!, feed.longitude!]}
              icon={icon}
            >
              <Popup>
                <div className="font-mono text-xs bg-[#0d1117] text-white p-2 rounded min-w-[180px]">
                  <p className="font-bold text-cyan-400 border-b border-slate-700 pb-1 mb-1">{feed.name}</p>
                  <p className="text-slate-400">Type: <span className="text-white">{feed.feed_type}</span></p>
                  <p className="text-slate-400">Status: <span className={
                    feed.status === "ACTIVE" ? "text-emerald-400" :
                    feed.status === "ALERT"  ? "text-red-400" :
                    feed.status === "DEGRADED" ? "text-yellow-400" : "text-slate-500"
                  }>{feed.status}</span></p>
                  {feed.location_name && (
                    <p className="text-slate-400">Location: <span className="text-white">{feed.location_name}</span></p>
                  )}
                  <p className="text-slate-500 text-[9px] mt-1">
                    {feed.latitude!.toFixed(5)}, {feed.longitude!.toFixed(5)}
                  </p>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Drone marker + flight path */}
        {dronePos && (
          <>
            {history.length > 1 && (
              <Polyline
                positions={history}
                pathOptions={{ color: "#00f2ff", weight: 2, dashArray: "8,6", opacity: 0.6 }}
              />
            )}
            {/* Pulse ring around drone */}
            <Circle
              center={dronePos}
              radius={80}
              pathOptions={{ color: "#00f2ff", fillColor: "#00f2ff", fillOpacity: 0.05, weight: 1 }}
            />
            <Marker position={dronePos} icon={DRONE_ICON}>
              <Popup>
                <div className="font-mono text-xs bg-[#0d1117] text-white p-2 rounded min-w-[160px]">
                  <p className="font-bold text-cyan-400 border-b border-slate-700 pb-1 mb-1">UAV ALPHA-01</p>
                  <p className="text-slate-400">ALT: <span className="text-white">120m</span></p>
                  <p className="text-slate-400">SPEED: <span className="text-white">15 m/s</span></p>
                  <p className="text-slate-400">POS: <span className="text-cyan-400">
                    {dronePos[0].toFixed(5)}, {dronePos[1].toFixed(5)}
                  </span></p>
                </div>
              </Popup>
            </Marker>
          </>
        )}
      </MapContainer>
    </div>
  );
};
