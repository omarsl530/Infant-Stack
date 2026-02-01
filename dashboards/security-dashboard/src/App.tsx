import { useState, useEffect, useCallback } from 'react';
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
} from '@heroicons/react/24/outline';

import {
  FloorplanMap,
  AlertPanel,
  GateGrid,
  EventFeed,
  TimelineScrubber,
  CameraGrid,
  CameraStreamModal,
} from './components';

// Real-time hooks imported but not yet connected to backend
// import { usePositionTracker, useAlertTracker, useGateEvents } from './hooks/useRealtimeData';
// import * as api from './api';
import type {
  RTLSPosition,
  Gate,
  Alert,
  Camera,
  Zone,
  Floorplan,
  GateEvent,
  PlaybackState,
} from './types';

// =============================================================================
// Mock Data for Development
// =============================================================================

const MOCK_FLOORPLAN: Floorplan = {
  id: 'f1',
  floor: 'F1',
  name: 'Ground Floor',
  imageUrl: '/assets/floor1-placeholder.svg',
  width: 1200,
  height: 800,
  scale: 10,
  originX: 0,
  originY: 0,
};

const MOCK_GATES: Gate[] = [
  { id: '1', gateId: 'GATE-A1', name: 'Main Entrance', floor: 'F1', zone: 'Lobby', state: 'CLOSED', lastStateChange: new Date().toISOString(), cameraId: 'cam-1' },
  { id: '2', gateId: 'GATE-A2', name: 'Emergency Exit', floor: 'F1', zone: 'East Wing', state: 'OPEN', lastStateChange: new Date().toISOString() },
  { id: '3', gateId: 'GATE-B1', name: 'Nursery Entry', floor: 'F1', zone: 'Maternity', state: 'CLOSED', lastStateChange: new Date().toISOString(), cameraId: 'cam-2' },
  { id: '4', gateId: 'GATE-B2', name: 'Staff Only', floor: 'F1', zone: 'Restricted', state: 'FORCED_OPEN', lastStateChange: new Date(Date.now() - 45000).toISOString(), cameraId: 'cam-3' },
];

const MOCK_CAMERAS: Camera[] = [
  { id: 'cam-1', cameraId: 'CAM-001', name: 'Main Entrance', gateId: 'GATE-A1', floor: 'F1', zone: 'Lobby', streamUrl: '', thumbnailUrl: '', status: 'online' },
  { id: 'cam-2', cameraId: 'CAM-002', name: 'Nursery Entry', gateId: 'GATE-B1', floor: 'F1', zone: 'Maternity', streamUrl: '', thumbnailUrl: '', status: 'online' },
  { id: 'cam-3', cameraId: 'CAM-003', name: 'Staff Corridor', gateId: 'GATE-B2', floor: 'F1', zone: 'Restricted', streamUrl: '', thumbnailUrl: '', status: 'offline' },
  { id: 'cam-4', cameraId: 'CAM-004', name: 'East Hallway', floor: 'F1', zone: 'East Wing', streamUrl: '', thumbnailUrl: '', status: 'online' },
];

const MOCK_ZONES: Zone[] = [
  { id: 'z1', name: 'Maternity Ward', floor: 'F1', type: 'authorized', polygon: [{ x: 100, y: 100 }, { x: 300, y: 100 }, { x: 300, y: 250 }, { x: 100, y: 250 }], color: '#22c55e' },
  { id: 'z2', name: 'Restricted Area', floor: 'F1', type: 'restricted', polygon: [{ x: 400, y: 100 }, { x: 550, y: 100 }, { x: 550, y: 200 }, { x: 400, y: 200 }], color: '#ef4444' },
  { id: 'z3', name: 'Exit Zone', floor: 'F1', type: 'exit', polygon: [{ x: 50, y: 300 }, { x: 150, y: 300 }, { x: 150, y: 400 }, { x: 50, y: 400 }], color: '#f59e0b' },
];

const MOCK_ALERTS: Alert[] = [
  {
    id: '1', alertId: 'ALT-001', type: 'DOOR_FORCED_OPEN', severity: 'critical',
    timestamp: new Date().toISOString(), entityType: 'gate', entityId: 'GATE-B2',
    message: 'Staff Only door forced open at Restricted Area',
    acknowledged: false,
  },
  {
    id: '2', alertId: 'ALT-002', type: 'TAG_LOW_BATTERY', severity: 'warning',
    timestamp: new Date(Date.now() - 300000).toISOString(), entityType: 'tag', entityId: 'INF-007',
    message: 'Infant tag INF-007 battery at 15%',
    acknowledged: false,
  },
  {
    id: '3', alertId: 'ALT-003', type: 'GEOFENCE_BREACH', severity: 'critical',
    timestamp: new Date(Date.now() - 120000).toISOString(), entityType: 'tag', entityId: 'INF-003',
    message: 'Tag INF-003 entered restricted zone without authorization',
    acknowledged: true, acknowledgedAt: new Date(Date.now() - 60000).toISOString(),
  },
];

const MOCK_POSITIONS: RTLSPosition[] = [
  { tagId: 'INF-001', assetType: 'infant', x: 150, y: 180, z: 0, floor: 'F1', accuracy: 0.3, batteryPct: 85, gatewayId: 'GW-01', rssi: -55, timestamp: new Date().toISOString(), sequenceId: 1 },
  { tagId: 'INF-002', assetType: 'infant', x: 220, y: 200, z: 0, floor: 'F1', accuracy: 0.2, batteryPct: 92, gatewayId: 'GW-01', rssi: -48, timestamp: new Date().toISOString(), sequenceId: 2 },
  { tagId: 'INF-003', assetType: 'infant', x: 450, y: 150, z: 0, floor: 'F1', accuracy: 0.4, batteryPct: 78, gatewayId: 'GW-02', rssi: -62, timestamp: new Date().toISOString(), sequenceId: 3 },
  { tagId: 'MOM-001', assetType: 'mother', x: 160, y: 170, z: 0, floor: 'F1', accuracy: 0.3, batteryPct: 90, gatewayId: 'GW-01', rssi: -50, timestamp: new Date().toISOString(), sequenceId: 4 },
  { tagId: 'MOM-002', assetType: 'mother', x: 230, y: 210, z: 0, floor: 'F1', accuracy: 0.2, batteryPct: 88, gatewayId: 'GW-01', rssi: -52, timestamp: new Date().toISOString(), sequenceId: 5 },
];

const MOCK_EVENTS: GateEvent[] = [
  { id: 'e1', eventType: 'badgeScan', timestamp: new Date().toISOString(), gateId: 'GATE-A1', gateName: 'Main Entrance', badgeId: 'BADGE-001', userId: 'USR-001', userName: 'J. Smith', result: 'GRANTED', direction: 'IN' },
  { id: 'e2', eventType: 'forced', timestamp: new Date(Date.now() - 45000).toISOString(), gateId: 'GATE-B2', gateName: 'Staff Only', state: 'FORCED_OPEN', durationMs: 45000 },
  { id: 'e3', eventType: 'badgeScan', timestamp: new Date(Date.now() - 120000).toISOString(), gateId: 'GATE-B1', gateName: 'Nursery Entry', badgeId: 'BADGE-015', userId: 'USR-015', userName: 'A. Jones', result: 'DENIED', direction: 'IN' },
  { id: 'e4', eventType: 'gateState', timestamp: new Date(Date.now() - 180000).toISOString(), gateId: 'GATE-A2', gateName: 'Emergency Exit', state: 'OPEN', previousState: 'CLOSED' },
];

// =============================================================================
// Stat Card Component
// =============================================================================

function StatCard({ title, value, icon: Icon, color, trend }: {
  title: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  trend?: { value: number; isUp: boolean };
}) {
  return (
    <div className="glass-card p-5 transition-transform hover:scale-[1.02]">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400 mb-1">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
          {trend && (
            <p className={`text-xs mt-1 ${trend.isUp ? 'text-emerald-400' : 'text-red-400'}`}>
              {trend.isUp ? '↑' : '↓'} {trend.value}% from yesterday
            </p>
          )}
        </div>
        <div className={`p-3 rounded-xl ${color}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Main App Component
// =============================================================================

type ActiveView = 'map' | 'gates' | 'cameras' | 'events';

export default function App() {
  // State
  const [currentTime, setCurrentTime] = useState(new Date());
  const [activeView, setActiveView] = useState<ActiveView>('map');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showHeatmap, setShowHeatmap] = useState(false);
  
  // Data state
  const [floorplan] = useState<Floorplan>(MOCK_FLOORPLAN);
  const [gates] = useState<Gate[]>(MOCK_GATES);
  const [cameras] = useState<Camera[]>(MOCK_CAMERAS);
  const [zones] = useState<Zone[]>(MOCK_ZONES);
  const [alerts, setAlerts] = useState<Alert[]>(MOCK_ALERTS);
  const [positions, setPositions] = useState<RTLSPosition[]>(MOCK_POSITIONS);
  const [events] = useState<GateEvent[]>(MOCK_EVENTS);
  
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

  // Real-time hooks (commented out for now, using mock data)
  // const { positions, isConnected } = usePositionTracker('F1');
  // const { alerts: realtimeAlerts } = useAlertTracker();
  // const { events: realtimeEvents } = useGateEvents();

  // Clock update
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Simulate position updates
  useEffect(() => {
    const interval = setInterval(() => {
      setPositions((prev) =>
        prev.map((pos) => ({
          ...pos,
          x: pos.x + (Math.random() - 0.5) * 5,
          y: pos.y + (Math.random() - 0.5) * 5,
          timestamp: new Date().toISOString(),
        }))
      );
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  // Handlers
  const handleAcknowledgeAlert = useCallback((alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.alertId === alertId
          ? { ...a, acknowledged: true, acknowledgedAt: new Date().toISOString() }
          : a
      )
    );
  }, []);

  const handleDismissAlert = useCallback((alertId: string) => {
    setAlerts((prev) => prev.filter((a) => a.alertId !== alertId));
  }, []);

  const handleEscalateAlert = useCallback((alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.alertId === alertId
          ? { ...a, escalatedAt: new Date().toISOString() }
          : a
      )
    );
  }, []);

  // Stats
  const activeAlerts = alerts.filter((a) => !a.acknowledged).length;
  const criticalAlerts = alerts.filter((a) => a.severity === 'critical' && !a.acknowledged).length;
  const openGates = gates.filter((g) => g.state === 'OPEN' || g.state === 'HELD_OPEN').length;
  const alertGates = gates.filter((g) => g.state === 'FORCED_OPEN').length;

  const navItems = [
    { id: 'map' as const, label: 'Live Map', icon: MapIcon },
    { id: 'gates' as const, label: 'Gates', icon: RectangleGroupIcon },
    { id: 'cameras' as const, label: 'Cameras', icon: VideoCameraIcon },
    { id: 'events' as const, label: 'Events', icon: BellAlertIcon },
  ];

  return (
    <div className="min-h-screen bg-slate-900 flex">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-30 bg-slate-800/95 border-r border-slate-700/50 transition-all duration-300 ${
        isSidebarCollapsed ? 'w-20' : 'w-64'
      } ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center gap-3 p-4 border-b border-slate-700/50">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-600 flex items-center justify-center flex-shrink-0">
              <ShieldCheckIcon className="w-6 h-6 text-white" />
            </div>
            {!isSidebarCollapsed && (
              <div>
                <h1 className="font-bold gradient-text-security">Infant-Stack</h1>
                <p className="text-xs text-slate-400">Security Dashboard</p>
              </div>
            )}
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => { setActiveView(item.id); setIsMobileMenuOpen(false); }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                  activeView === item.id
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-slate-400 hover:bg-slate-700/50 hover:text-white'
                }`}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {!isSidebarCollapsed && <span className="font-medium">{item.label}</span>}
              </button>
            ))}
          </nav>

          {/* Connection Status */}
          <div className="p-4 border-t border-slate-700/50">
            <div className={`flex items-center gap-2 ${isSidebarCollapsed ? 'justify-center' : ''}`}>
              <SignalIcon className="w-4 h-4 text-emerald-400" />
              {!isSidebarCollapsed && (
                <span className="text-xs text-emerald-400">Connected • Live</span>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile menu overlay */}
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Main Content */}
      <main className={`flex-1 transition-all duration-300 ${isSidebarCollapsed ? 'lg:ml-20' : 'lg:ml-64'}`}>
        {/* Header */}
        <header className="sticky top-0 z-20 bg-slate-900/80 backdrop-blur-lg border-b border-slate-700/50">
          <div className="flex items-center justify-between px-6 py-4">
            <div className="flex items-center gap-4">
              <button 
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="p-2 rounded-lg hover:bg-slate-700/50 lg:hidden"
              >
                {isMobileMenuOpen ? <XMarkIcon className="w-6 h-6" /> : <Bars3Icon className="w-6 h-6" />}
              </button>
              <button
                onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                className="p-2 rounded-lg hover:bg-slate-700/50 hidden lg:block"
              >
                <Bars3Icon className="w-5 h-5" />
              </button>
              <h2 className="text-xl font-semibold">
                {navItems.find((n) => n.id === activeView)?.label || 'Dashboard'}
              </h2>
            </div>

            <div className="flex items-center gap-4">
              {/* Live indicator */}
              <div className="flex items-center gap-2 px-3 py-1.5 bg-red-600/20 rounded-full">
                <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                <span className="text-xs font-medium text-red-400">LIVE</span>
              </div>

              {/* Time */}
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium">{currentTime.toLocaleTimeString()}</p>
                <p className="text-xs text-slate-400">{currentTime.toLocaleDateString()}</p>
              </div>

              {/* Settings */}
              <button className="p-2 rounded-lg hover:bg-slate-700/50">
                <Cog6ToothIcon className="w-5 h-5" />
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-6">
          {/* Stats Row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
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
              color={criticalAlerts > 0 ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'}
            />
            <StatCard
              title="Gates Open"
              value={`${openGates}/${gates.length}`}
              icon={RectangleGroupIcon}
              color={alertGates > 0 ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'}
            />
            <StatCard
              title="Cameras Online"
              value={`${cameras.filter((c) => c.status === 'online').length}/${cameras.length}`}
              icon={VideoCameraIcon}
              color="bg-purple-500/20 text-purple-400"
            />
          </div>

          {/* Main Grid */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {/* Main View Area */}
            <div className="xl:col-span-2 space-y-6">
              {activeView === 'map' && (
                <>
                  {/* Map Controls */}
                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={showHeatmap}
                        onChange={(e) => setShowHeatmap(e.target.checked)}
                        className="w-4 h-4 rounded bg-slate-700 border-slate-600"
                      />
                      <span className="text-sm">Show Heatmap</span>
                    </label>
                  </div>

                  {/* Floorplan Map */}
                  <div className="glass-card overflow-hidden" style={{ height: '500px' }}>
                    <FloorplanMap
                      floorplan={floorplan}
                      positions={positions}
                      gates={gates}
                      zones={zones}
                      selectedTagId={selectedTag?.tagId}
                      showHeatmap={showHeatmap}
                      onTagClick={(pos) => setSelectedTag(pos)}
                      onGateClick={(gate) => console.log('Gate clicked:', gate)}
                      onZoneClick={(zone) => console.log('Zone clicked:', zone)}
                    />
                  </div>

                  {/* Timeline */}
                  <TimelineScrubber
                    isLive={playbackState.isLive}
                    isPlaying={playbackState.isPlaying}
                    currentTime={playbackState.currentTime}
                    startTime={new Date(Date.now() - 3600000)}
                    endTime={new Date()}
                    playbackSpeed={playbackState.playbackSpeed}
                    onToggleLive={() => setPlaybackState((s) => ({ ...s, isLive: !s.isLive }))}
                    onTogglePlay={() => setPlaybackState((s) => ({ ...s, isPlaying: !s.isPlaying }))}
                    onSeek={(time) => setPlaybackState((s) => ({ ...s, currentTime: time }))}
                    onSpeedChange={(speed) => setPlaybackState((s) => ({ ...s, playbackSpeed: speed }))}
                  />
                </>
              )}

              {activeView === 'gates' && (
                <div className="glass-card p-6">
                  <GateGrid
                    gates={gates}
                    onGateClick={(gate) => console.log('Gate clicked:', gate)}
                    onCameraClick={(gate) => {
                      const camera = cameras.find((c) => c.gateId === gate.gateId);
                      if (camera) setSelectedCamera(camera);
                    }}
                  />
                </div>
              )}

              {activeView === 'cameras' && (
                <div className="glass-card p-6">
                  <CameraGrid
                    cameras={cameras}
                    columns={3}
                    refreshInterval={5000}
                    onCameraClick={setSelectedCamera}
                  />
                </div>
              )}

              {activeView === 'events' && (
                <div className="glass-card p-6 overflow-hidden">
                  <h3 className="font-semibold mb-4">Recent Events</h3>
                  <EventFeed
                    events={events}
                    maxEvents={50}
                    onEventClick={(event) => console.log('Event clicked:', event)}
                  />
                </div>
              )}
            </div>

            {/* Right Sidebar - Alerts */}
            <div className="xl:col-span-1">
              <div className="glass-card p-6 sticky top-24" style={{ maxHeight: 'calc(100vh - 200px)' }}>
                <AlertPanel
                  alerts={alerts}
                  maxVisible={10}
                  onAcknowledge={handleAcknowledgeAlert}
                  onDismiss={handleDismissAlert}
                  onEscalate={handleEscalateAlert}
                  onAlertClick={(alert) => console.log('Alert clicked:', alert)}
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
