import { useState, useEffect, useCallback } from "react";
import {
  ShieldCheckIcon,
  BellAlertIcon,
  MapIcon,
  RectangleGroupIcon,
  VideoCameraIcon,
  Cog6ToothIcon,
  SignalIcon,
  Bars3Icon,
  XMarkIcon,
  ChartBarIcon,
  HomeIcon,
  ArrowRightOnRectangleIcon,
} from "@heroicons/react/24/outline";

import { useAuth } from "react-oidc-context";

import {
  FloorplanMap,
  AlertPanel,
  GateGrid,
  EventFeed,
  TimelineScrubber,
  CameraGrid,
  CameraStreamModal,
  StatCard,
  OperationsDashboard,
} from "./components";

import {
  usePositionTracker,
  useAlertTracker,
  useGateEvents,
} from "./hooks/useRealtimeData";
import {
  fetchGates,
  fetchCameras,
  fetchZones,
  fetchFloorplans,
  acknowledgeAlert,
  dismissAlert,
  escalateAlert,
  exportPositions,
} from "./api";

import type {
  RTLSPosition,
  Gate,
  Camera,
  Zone,
  Floorplan,
  PlaybackState,
} from "./types";

// =============================================================================
// Stat Card Component
// =============================================================================

// StatCard moved to components/StatCard.tsx

// =============================================================================
// Main App Component
// =============================================================================

type ActiveView = "map" | "gates" | "cameras" | "events" | "operations";

export default function App() {
  // State
  const auth = useAuth();
  const [currentTime, setCurrentTime] = useState(new Date());
  const [activeView, setActiveView] = useState<ActiveView>("map");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showHeatmap, setShowHeatmap] = useState(false);

  // Data state
  const [floorplans, setFloorplans] = useState<Floorplan[]>([]);
  const [activeFloorplanId, setActiveFloorplanId] = useState<string | null>(
    null,
  );
  const [gates, setGates] = useState<Gate[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);

  // Real-time data from hooks
  const activeFloorplan =
    floorplans.find((f) => f.id === activeFloorplanId) || floorplans[0] || null;
  const { positions, isConnected: isRtlsConnected } = usePositionTracker(
    activeFloorplan?.floor || "F1",
  );
  const {
    alerts,
    setAlerts,
    isConnected: isAlertsConnected,
  } = useAlertTracker();
  const { events, isConnected: isEventsConnected } = useGateEvents();

  const isSystemOnline =
    isRtlsConnected && isAlertsConnected && isEventsConnected;

  // Modal states
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [selectedTag, setSelectedTag] = useState<RTLSPosition | null>(null);

  // Playback state
  const [playbackState, setPlaybackState] = useState<PlaybackState>({
    isPlaying: false,
    isLive: true,
    currentTime: new Date(),
    playbackSpeed: 1,
  });

  const [historyRange, setHistoryRange] = useState({
    start: new Date(Date.now() - 3600000),
    end: new Date(),
  });

  const handleExport = useCallback(async () => {
    try {
      await exportPositions(
        historyRange.start.toISOString(),
        historyRange.end.toISOString(),
      );
    } catch (err) {
      console.error("Export failed:", err);
    }
  }, [historyRange]);

  // Clock update
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch static data on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [gatesData, camerasData, zonesData, floorplansData] =
          await Promise.all([
            fetchGates(),
            fetchCameras(),
            fetchZones(),
            fetchFloorplans(),
          ]);

        setGates(gatesData);
        setCameras(camerasData);
        setZones(zonesData);
        setFloorplans(floorplansData);
        if (floorplansData.length > 0) {
          setActiveFloorplanId(floorplansData[0].id);
        }
      } catch (error) {
        console.error("Failed to fetch initial data:", error);
      }
    };

    fetchData();
  }, []);

  // Listen for global logout events
  useEffect(() => {
    return auth.events.addUserSignedOut(() => {
      auth.removeUser();
      window.location.href = "http://localhost:3003/login";
    });
  }, [auth]);

  // Handlers
  const handleAcknowledgeAlert = useCallback(
    async (alertId: string) => {
      try {
        await acknowledgeAlert(alertId);
        setAlerts((prev) =>
          prev.map((a) =>
            a.alertId === alertId
              ? {
                  ...a,
                  acknowledged: true,
                  acknowledgedAt: new Date().toISOString(),
                }
              : a,
          ),
        );
      } catch (err) {
        console.error("Failed to acknowledge alert:", err);
      }
    },
    [setAlerts],
  );

  const handleDismissAlert = useCallback(
    async (alertId: string) => {
      try {
        await dismissAlert(alertId);
        setAlerts((prev) => prev.filter((a) => a.alertId !== alertId));
      } catch (err) {
        console.error("Failed to dismiss alert:", err);
      }
    },
    [setAlerts],
  );

  const handleEscalateAlert = useCallback(
    async (alertId: string) => {
      try {
        await escalateAlert(alertId);
        setAlerts((prev) =>
          prev.map((a) =>
            a.alertId === alertId
              ? { ...a, escalatedAt: new Date().toISOString() }
              : a,
          ),
        );
      } catch (err) {
        console.error("Failed to escalate alert:", err);
      }
    },
    [setAlerts],
  );

  // Stats
  const activeAlerts = alerts.filter((a) => !a.acknowledged).length;
  const criticalAlerts = alerts.filter(
    (a) => (a.severity || "").toLowerCase() === "critical" && !a.acknowledged,
  ).length;
  const openGates = gates.filter(
    (g) => g.state === "OPEN" || g.state === "HELD_OPEN",
  ).length;
  const alertGates = gates.filter((g) => g.state === "FORCED_OPEN").length;

  const navItems = [
    { id: "map" as const, label: "Live Map", icon: MapIcon },
    { id: "gates" as const, label: "Gates", icon: RectangleGroupIcon },
    { id: "cameras" as const, label: "Cameras", icon: VideoCameraIcon },
    { id: "events" as const, label: "Events", icon: BellAlertIcon },
    { id: "operations" as const, label: "Operations", icon: ChartBarIcon },
  ];

  return (
    <div className="min-h-screen bg-slate-900 flex">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 bg-slate-800/95 border-r border-slate-700/50 transition-all duration-300 ${
          isSidebarCollapsed ? "w-20" : "w-64"
        } ${isMobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center gap-3 p-4 border-b border-slate-700/50">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-600 flex items-center justify-center flex-shrink-0">
              <ShieldCheckIcon className="w-6 h-6 text-white" />
            </div>
            {!isSidebarCollapsed && (
              <div>
                <h1 className="font-bold gradient-text-security">
                  Infant-Stack
                </h1>
                <p className="text-xs text-slate-400">Security Dashboard</p>
              </div>
            )}
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  setActiveView(item.id);
                  setIsMobileMenuOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                  activeView === item.id
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "text-slate-400 hover:bg-slate-700/50 hover:text-white"
                }`}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {!isSidebarCollapsed && (
                  <span className="font-medium">{item.label}</span>
                )}
              </button>
            ))}
          </nav>

          {/* Connection Status */}
          <div className="p-4 border-t border-slate-700/50">
            <div
              className={`flex items-center gap-2 ${isSidebarCollapsed ? "justify-center" : ""}`}
            >
              <SignalIcon
                className={`w-4 h-4 ${isSystemOnline ? "text-emerald-400" : "text-red-400"}`}
              />
              {!isSidebarCollapsed && (
                <span
                  className={`text-xs ${isSystemOnline ? "text-emerald-400" : "text-red-400"}`}
                >
                  {isSystemOnline ? "Connected • Live" : "Reconnecting..."}
                </span>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile menu overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 lg:hidden backdrop-blur-sm transition-opacity"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Main Content */}
      <main
        className={`flex-1 transition-all duration-300 ${isSidebarCollapsed ? "lg:ml-20" : "lg:ml-64"}`}
      >
        {/* Header */}
        <header className="sticky top-0 z-20 bg-slate-900/80 backdrop-blur-lg border-b border-slate-700/50">
          <div className="flex items-center justify-between px-6 py-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="p-2 rounded-lg hover:bg-slate-700/50 lg:hidden"
              >
                {isMobileMenuOpen ? (
                  <XMarkIcon className="w-6 h-6" />
                ) : (
                  <Bars3Icon className="w-6 h-6" />
                )}
              </button>
              <button
                onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                className="p-2 rounded-lg hover:bg-slate-700/50 hidden lg:block"
              >
                <Bars3Icon className="w-5 h-5" />
              </button>
              <h2 className="text-xl font-semibold">
                {navItems.find((n) => n.id === activeView)?.label ||
                  "Dashboard"}
              </h2>
            </div>

            <div className="flex items-center gap-4">
              {/* Live indicator */}
              <div
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${isSystemOnline ? "bg-red-600/20" : "bg-slate-700/50"}`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${isSystemOnline ? "bg-red-500 animate-pulse" : "bg-slate-400"}`}
                />
                <span
                  className={`text-xs font-medium ${isSystemOnline ? "text-red-400" : "text-slate-400"}`}
                >
                  {isSystemOnline ? "LIVE" : "OFFLINE"}
                </span>
              </div>

              {/* Time */}
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium">
                  {currentTime.toLocaleTimeString()}
                </p>
                <p className="text-xs text-slate-400">
                  {currentTime.toLocaleDateString()}
                </p>
              </div>

              {/* Settings */}
              <button
                onClick={() => (window.location.href = "http://localhost:3003")}
                className="p-2 rounded-lg hover:bg-slate-700/50"
                title="Back to Hub"
              >
                <HomeIcon className="w-5 h-5" />
              </button>
              <button className="p-2 rounded-lg hover:bg-slate-700/50">
                <Cog6ToothIcon className="w-5 h-5" />
              </button>
              <button
                onClick={() =>
                  auth.signoutRedirect({
                    post_logout_redirect_uri: "http://localhost:3003/login",
                  })
                }
                className="p-2 rounded-lg hover:bg-slate-700/50 text-red-400"
                title="Sign Out"
              >
                <ArrowRightOnRectangleIcon className="w-5 h-5" />
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-6">
          {/* Stats Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard
              title="Active Tags"
              value={positions.length}
              icon={MapIcon}
              color="bg-cyan-500/20 text-cyan-400"
            />
            <StatCard
              title="Active Alerts"
              value={activeAlerts}
              icon={BellAlertIcon}
              color={
                criticalAlerts > 0
                  ? "bg-red-500/20 text-red-400"
                  : "bg-amber-500/20 text-amber-400"
              }
            />
            <StatCard
              title="Gates Open"
              value={`${openGates}/${gates.length}`}
              icon={RectangleGroupIcon}
              color={
                alertGates > 0
                  ? "bg-red-500/20 text-red-400"
                  : "bg-emerald-500/20 text-emerald-400"
              }
            />
            <StatCard
              title="Cameras Online"
              value={`${cameras.filter((c) => c.status === "online").length}/${cameras.length}`}
              icon={VideoCameraIcon}
              color="bg-purple-500/20 text-purple-400"
            />
          </div>

          {/* Main Grid */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {/* Main View Area */}
            <div className="xl:col-span-2 space-y-6">
              {activeView === "map" && (
                <>
                  {/* Map Controls */}
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={showHeatmap}
                        onChange={(e) => setShowHeatmap(e.target.checked)}
                        className="w-4 h-4 rounded bg-slate-700 border-slate-600"
                      />
                      <span className="text-sm">Show Heatmap</span>
                    </label>

                    {/* Floor Selector */}
                    {floorplans.length > 1 && (
                      <select
                        value={activeFloorplanId || ""}
                        onChange={(e) => setActiveFloorplanId(e.target.value)}
                        className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1 text-sm outline-none focus:ring-2 focus:ring-emerald-500"
                      >
                        {floorplans.map((fp) => (
                          <option key={fp.id} value={fp.id}>
                            {fp.name}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>

                  {/* Floorplan Map */}
                  <div
                    className="glass-card overflow-hidden"
                    style={{ height: "500px" }}
                  >
                    <FloorplanMap
                      floorplan={activeFloorplan}
                      positions={positions}
                      gates={gates}
                      zones={zones}
                      alerts={alerts}
                      selectedTagId={selectedTag?.tagId}
                      showHeatmap={showHeatmap}
                      onTagClick={(pos) => setSelectedTag(pos)}
                      onGateClick={(gate) => console.log("Gate clicked:", gate)}
                      onZoneClick={(zone) => console.log("Zone clicked:", zone)}
                    />
                  </div>

                  {/* Timeline */}
                  <TimelineScrubber
                    isLive={playbackState.isLive}
                    isPlaying={playbackState.isPlaying}
                    currentTime={playbackState.currentTime}
                    startTime={historyRange.start}
                    endTime={historyRange.end}
                    playbackSpeed={playbackState.playbackSpeed}
                    onToggleLive={() =>
                      setPlaybackState((s) => ({ ...s, isLive: !s.isLive }))
                    }
                    onTogglePlay={() =>
                      setPlaybackState((s) => ({
                        ...s,
                        isPlaying: !s.isPlaying,
                      }))
                    }
                    onSeek={(time) =>
                      setPlaybackState((s) => ({ ...s, currentTime: time }))
                    }
                    onSpeedChange={(speed) =>
                      setPlaybackState((s) => ({ ...s, playbackSpeed: speed }))
                    }
                    onRangeChange={(start, end) =>
                      setHistoryRange({ start, end })
                    }
                    onExport={handleExport}
                  />
                </>
              )}

              {activeView === "gates" && (
                <div className="glass-card p-6">
                  <GateGrid
                    gates={gates}
                    onGateClick={(gate) => console.log("Gate clicked:", gate)}
                    onCameraClick={(gate) => {
                      const camera = cameras.find(
                        (c) => c.gateId === gate.gateId,
                      );
                      if (camera) setSelectedCamera(camera);
                    }}
                  />
                </div>
              )}

              {activeView === "cameras" && (
                <div className="glass-card p-6">
                  <CameraGrid
                    cameras={cameras}
                    columns={3}
                    refreshInterval={5000}
                    onCameraClick={setSelectedCamera}
                  />
                </div>
              )}

              {activeView === "events" && (
                <div className="glass-card p-6 overflow-hidden">
                  <h3 className="font-semibold mb-4">Recent Events</h3>
                  <EventFeed
                    events={events}
                    maxEvents={50}
                    onEventClick={(event) =>
                      console.log("Event clicked:", event)
                    }
                  />
                </div>
              )}

              {activeView === "operations" && (
                <OperationsDashboard
                  isRtlsConnected={isRtlsConnected}
                  isAlertsConnected={isAlertsConnected}
                  isEventsConnected={isEventsConnected}
                  positions={positions}
                  gates={gates}
                  cameras={cameras}
                  alerts={alerts}
                />
              )}
            </div>

            {/* Right Sidebar - Alerts */}
            <div className="xl:col-span-1">
              <div
                className="glass-card p-6 sticky top-24"
                style={{ maxHeight: "calc(100vh - 200px)" }}
              >
                <AlertPanel
                  alerts={alerts}
                  maxVisible={10}
                  onAcknowledge={handleAcknowledgeAlert}
                  onDismiss={handleDismissAlert}
                  onEscalate={handleEscalateAlert}
                  onAlertClick={(alert) => console.log("Alert clicked:", alert)}
                />
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Camera Stream Modal */}
      <CameraStreamModal
        camera={selectedCamera}
        onClose={() => setSelectedCamera(null)}
      />
    </div>
  );
}
