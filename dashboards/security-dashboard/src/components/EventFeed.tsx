import type { GateEvent } from '../types';
import { 
  ArrowRightOnRectangleIcon,
  ArrowLeftOnRectangleIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';

interface EventFeedProps {
  events: GateEvent[];
  maxEvents?: number;
  onEventClick?: (event: GateEvent) => void;
}

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function getEventIcon(event: GateEvent) {
  if (event.eventType === 'forced' || event.state === 'FORCED_OPEN') {
    return <ExclamationTriangleIcon className="w-4 h-4 text-red-400" />;
  }
  if (event.eventType === 'heldOpen' || event.state === 'HELD_OPEN') {
    return <ClockIcon className="w-4 h-4 text-amber-400" />;
  }
  if (event.eventType === 'badgeScan') {
    if (event.result === 'DENIED') {
      return <XCircleIcon className="w-4 h-4 text-red-400" />;
    }
    if (event.direction === 'IN') {
      return <ArrowRightOnRectangleIcon className="w-4 h-4 text-emerald-400" />;
    }
    return <ArrowLeftOnRectangleIcon className="w-4 h-4 text-cyan-400" />;
  }
  if (event.eventType === 'gateState') {
    return event.state === 'OPEN' 
      ? <CheckCircleIcon className="w-4 h-4 text-emerald-400" />
      : <CheckCircleIcon className="w-4 h-4 text-slate-400" />;
  }
  return <CheckCircleIcon className="w-4 h-4 text-slate-400" />;
}

function getEventDescription(event: GateEvent): string {
  if (event.eventType === 'badgeScan') {
    const action = event.result === 'GRANTED' ? 'granted' : 'denied';
    const direction = event.direction === 'IN' ? 'entry' : 'exit';
    return `Access ${action} (${direction})`;
  }
  if (event.eventType === 'forced') {
    return 'Door forced open';
  }
  if (event.eventType === 'heldOpen') {
    return `Door held open for ${Math.floor((event.durationMs || 0) / 1000)}s`;
  }
  if (event.eventType === 'gateState') {
    return `Gate ${event.state?.toLowerCase()}`;
  }
  return event.eventType;
}

function EventRow({ event, onClick }: { event: GateEvent; onClick?: () => void }) {
  const isAlert = event.eventType === 'forced' || 
                  event.state === 'FORCED_OPEN' || 
                  event.result === 'DENIED';

  return (
    <tr 
      className={`border-b border-slate-700/50 hover:bg-slate-800/30 transition-colors cursor-pointer ${
        isAlert ? 'bg-red-500/5' : ''
      }`}
      onClick={onClick}
    >
      <td className="px-4 py-3 text-sm text-slate-400 whitespace-nowrap">
        {formatTime(event.timestamp)}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          {getEventIcon(event)}
          <span className="text-sm">{getEventDescription(event)}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-sm">{event.gateName}</td>
      <td className="px-4 py-3 text-sm text-slate-400">
        {event.userName || event.badgeId || '-'}
      </td>
      <td className="px-4 py-3">
        {event.result && (
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
            event.result === 'GRANTED' ? 'bg-emerald-500/20 text-emerald-400' :
            event.result === 'DENIED' ? 'bg-red-500/20 text-red-400' :
            'bg-slate-500/20 text-slate-400'
          }`}>
            {event.result}
          </span>
        )}
      </td>
    </tr>
  );
}

export function EventFeed({ events, maxEvents = 50, onEventClick }: EventFeedProps) {
  const displayEvents = events.slice(0, maxEvents);

  return (
    <div className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Event</th>
              <th>Location</th>
              <th>User/Badge</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {displayEvents.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                  No recent events
                </td>
              </tr>
            ) : (
              displayEvents.map((event) => (
                <EventRow
                  key={event.id}
                  event={event}
                  onClick={onEventClick ? () => onEventClick(event) : undefined}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default EventFeed;
