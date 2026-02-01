import { 
  SignalIcon, 
  TagIcon, 
  MapIcon, 
  VideoCameraIcon,
  ShieldCheckIcon,
  BellAlertIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import type { RTLSPosition, Gate, Camera, Alert } from '../types';
import { StatCard } from './StatCard';

interface OperationsDashboardProps {
  isRtlsConnected: boolean;
  isAlertsConnected: boolean;
  isEventsConnected: boolean;
  positions: RTLSPosition[];
  gates: Gate[];
  cameras: Camera[];
  alerts: Alert[];
}

export function OperationsDashboard({
  isRtlsConnected,
  isAlertsConnected,
  isEventsConnected,
  positions,
  gates,
  cameras,
  alerts
}: OperationsDashboardProps) {
  // Aggregate data
  const tagBreakdown = {
    infant: positions.filter(p => p.assetType === 'infant').length,
    mother: positions.filter(p => p.assetType === 'mother').length,
    staff: positions.filter(p => p.assetType === 'staff').length,
  };

  const gateHealth = {
    online: gates.filter(g => g.status === 'online').length,
    offline: gates.filter(g => g.status === 'offline').length,
    forced: gates.filter(g => g.state === 'FORCED_OPEN').length,
  };

  const cameraHealth = {
    online: cameras.filter(c => c.status === 'online').length,
    offline: cameras.filter(c => c.status === 'offline').length,
  };

  const activeAlerts = alerts.filter(a => !a.acknowledged);
  const alertSeverity = {
    high: activeAlerts.filter(a => a.severity === 'high').length,
    medium: activeAlerts.filter(a => a.severity === 'medium').length,
    low: activeAlerts.filter(a => a.severity === 'low').length,
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-100 mb-4">Operations Overview</h2>

      {/* System Status Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <HealthMetric 
          label="RTLS Service" 
          isOnline={isRtlsConnected} 
          icon={TagIcon}
        />
        <HealthMetric 
          label="Alert Engine" 
          isOnline={isAlertsConnected} 
          icon={BellAlertIcon}
        />
        <HealthMetric 
          label="Gate Controller" 
          isOnline={isEventsConnected} 
          icon={ShieldCheckIcon}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Asset Distribution */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-medium text-slate-400 mb-6 flex items-center gap-2">
            <MapIcon className="w-4 h-4" />
            Active Asset Distribution
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard 
              title="Infants" 
              value={tagBreakdown.infant} 
              icon={TagIcon} 
              color="bg-cyan-500/10 text-cyan-400" 
            />
            <StatCard 
              title="Mothers" 
              value={tagBreakdown.mother} 
              icon={TagIcon} 
              color="bg-pink-500/10 text-pink-400" 
            />
            <StatCard 
              title="Staff" 
              value={tagBreakdown.staff} 
              icon={TagIcon} 
              color="bg-purple-500/10 text-purple-400" 
            />
          </div>
        </div>

        {/* Infrastructure Health */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-medium text-slate-400 mb-6 flex items-center gap-2">
            <SignalIcon className="w-4 h-4" />
            Infrastructure Status
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700/50">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs text-slate-400">Gates</span>
                <ShieldCheckIcon className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="flex justify-around items-end">
                <div className="text-center text-sm">
                  <div className="text-lg font-bold text-emerald-400">{gateHealth.online}</div>
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">Live</div>
                </div>
                <div className="text-center text-sm">
                  <div className="text-lg font-bold text-red-400">{gateHealth.offline}</div>
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">Offline</div>
                </div>
                <div className="text-center text-sm">
                  <div className="text-lg font-bold text-amber-500">{gateHealth.forced}</div>
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">Forced</div>
                </div>
              </div>
            </div>
            <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700/50">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs text-slate-400">Cameras</span>
                <VideoCameraIcon className="w-4 h-4 text-blue-400" />
              </div>
              <div className="flex justify-around items-end">
                <div className="text-center text-sm">
                  <div className="text-lg font-bold text-emerald-400">{cameraHealth.online}</div>
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">Live</div>
                </div>
                <div className="text-center text-sm">
                  <div className="text-lg font-bold text-red-400">{cameraHealth.offline}</div>
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">Offline</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Alert Summary */}
      <div className="glass-card p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-6 flex items-center gap-2">
          <ExclamationTriangleIcon className="w-4 h-4 text-amber-500" />
          Critical Alert Distribution
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <AlertSummaryTile severity="High" count={alertSeverity.high} color="text-red-400" bg="bg-red-400/10" />
          <AlertSummaryTile severity="Medium" count={alertSeverity.medium} color="text-amber-400" bg="bg-amber-400/10" />
          <AlertSummaryTile severity="Low" count={alertSeverity.low} color="text-emerald-400" bg="bg-emerald-400/10" />
        </div>
      </div>
    </div>
  );
}

function HealthMetric({ label, isOnline, icon: Icon }: { label: string; isOnline: boolean; icon: any }) {
  return (
    <div className="flex items-center justify-between p-4 bg-slate-800/40 border border-slate-700/50 rounded-2xl">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${isOnline ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
          <Icon className="w-5 h-5" />
        </div>
        <span className="text-sm font-medium text-slate-300">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-red-500'} animate-pulse`} />
        <span className="text-xs text-slate-500 uppercase tracking-tighter">{isOnline ? 'Connected' : 'Disconnected'}</span>
      </div>
    </div>
  );
}

function AlertSummaryTile({ severity, count, color, bg }: { severity: string; count: number; color: string; bg: string }) {
  return (
    <div className={`flex flex-col items-center justify-center p-6 ${bg} rounded-2xl border border-white/5`}>
      <div className={`text-3xl font-bold ${color}`}>{count}</div>
      <div className="text-xs text-slate-400 uppercase tracking-widest mt-1">{severity} Severity</div>
    </div>
  );
}
