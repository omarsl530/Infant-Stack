import { 
  LockClosedIcon, 
  LockOpenIcon, 
  ExclamationTriangleIcon,
  VideoCameraIcon 
} from '@heroicons/react/24/outline';
import type { Gate, GateState } from '../types';

interface GateStatusTileProps {
  gate: Gate;
  onClick?: () => void;
  onCameraClick?: () => void;
}

const stateConfig: Record<GateState, {
  bg: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  pulse?: boolean;
}> = {
  OPEN: {
    bg: 'bg-emerald-500/20 border-emerald-500/50',
    icon: LockOpenIcon,
    label: 'Open',
  },
  CLOSED: {
    bg: 'bg-slate-600/20 border-slate-500/50',
    icon: LockClosedIcon,
    label: 'Closed',
  },
  FORCED_OPEN: {
    bg: 'bg-red-500/20 border-red-500/50',
    icon: ExclamationTriangleIcon,
    label: 'FORCED',
    pulse: true,
  },
  HELD_OPEN: {
    bg: 'bg-amber-500/20 border-amber-500/50',
    icon: LockOpenIcon,
    label: 'Held Open',
  },
  UNKNOWN: {
    bg: 'bg-gray-500/20 border-gray-500/50',
    icon: LockClosedIcon,
    label: 'Unknown',
  },
};

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  }
  return `${seconds}s`;
}

export function GateStatusTile({ gate, onClick, onCameraClick }: GateStatusTileProps) {
  const config = stateConfig[gate.state] || stateConfig.UNKNOWN;
  const Icon = config.icon;
  const isAlert = gate.state === 'FORCED_OPEN' || gate.state === 'HELD_OPEN';

  const timeSinceChange = Date.now() - new Date(gate.lastStateChange).getTime();

  return (
    <div
      className={`relative p-4 rounded-xl border ${config.bg} cursor-pointer transition-all hover:scale-[1.02] hover:shadow-lg ${
        config.pulse ? 'animate-pulse' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Icon className={`w-5 h-5 ${
              gate.state === 'FORCED_OPEN' ? 'text-red-400' :
              gate.state === 'HELD_OPEN' ? 'text-amber-400' :
              gate.state === 'OPEN' ? 'text-emerald-400' : 'text-slate-400'
            }`} />
            <span className={`text-xs font-bold uppercase tracking-wider ${
              gate.state === 'FORCED_OPEN' ? 'text-red-400' :
              gate.state === 'HELD_OPEN' ? 'text-amber-400' :
              gate.state === 'OPEN' ? 'text-emerald-400' : 'text-slate-400'
            }`}>
              {config.label}
            </span>
          </div>
          
          <h4 className="font-semibold text-sm truncate">{gate.name}</h4>
          <p className="text-xs text-slate-400 mt-1">
            Floor {gate.floor} • {gate.zone}
          </p>
          
          {isAlert && (
            <p className="text-xs text-amber-400 mt-2">
              Duration: {formatDuration(timeSinceChange)}
            </p>
          )}
        </div>

        {gate.cameraId && onCameraClick && (
          <button
            onClick={(e) => { e.stopPropagation(); onCameraClick(); }}
            className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-600/50 transition-colors"
            title="View Camera"
          >
            <VideoCameraIcon className="w-4 h-4 text-slate-300" />
          </button>
        )}
      </div>

      {/* Status indicator dot */}
      <div className={`absolute top-2 right-2 w-2 h-2 rounded-full ${
        gate.state === 'FORCED_OPEN' ? 'bg-red-500 animate-ping' :
        gate.state === 'HELD_OPEN' ? 'bg-amber-500' :
        gate.state === 'OPEN' ? 'bg-emerald-500' : 'bg-slate-500'
      }`} />
    </div>
  );
}

interface GateGridProps {
  gates: Gate[];
  onGateClick?: (gate: Gate) => void;
  onCameraClick?: (gate: Gate) => void;
}

export function GateGrid({ gates, onGateClick, onCameraClick }: GateGridProps) {
  const alertGates = gates.filter((g) => g.state === 'FORCED_OPEN' || g.state === 'HELD_OPEN');
  const normalGates = gates.filter((g) => g.state !== 'FORCED_OPEN' && g.state !== 'HELD_OPEN');

  return (
    <div className="space-y-4">
      {/* Alert gates first */}
      {alertGates.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-red-400 mb-2 flex items-center gap-2">
            <ExclamationTriangleIcon className="w-4 h-4" />
            Attention Required ({alertGates.length})
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {alertGates.map((gate) => (
              <GateStatusTile
                key={gate.id}
                gate={gate}
                onClick={() => onGateClick?.(gate)}
                onCameraClick={gate.cameraId ? () => onCameraClick?.(gate) : undefined}
              />
            ))}
          </div>
        </div>
      )}

      {/* Normal gates */}
      <div>
        <h4 className="text-sm font-medium text-slate-400 mb-2">
          All Gates ({normalGates.length})
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {normalGates.map((gate) => (
            <GateStatusTile
              key={gate.id}
              gate={gate}
              onClick={() => onGateClick?.(gate)}
              onCameraClick={gate.cameraId ? () => onCameraClick?.(gate) : undefined}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default GateGrid;
