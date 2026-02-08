import { XMarkIcon, CheckIcon, ArrowUpIcon } from "@heroicons/react/24/outline";
import type { Alert, AlertSeverity } from "../types";

interface AlertPanelProps {
  alerts: Alert[];
  maxVisible?: number;
  onAcknowledge?: (alertId: string) => void;
  onDismiss?: (alertId: string) => void;
  onEscalate?: (alertId: string) => void;
  onAlertClick?: (alert: Alert) => void;
}

const severityConfig: Record<
  AlertSeverity,
  {
    bg: string;
    border: string;
    icon: string;
    label: string;
  }
> = {
  critical: {
    bg: "alert-critical",
    border: "border-l-red-500",
    icon: "🚨",
    label: "CRITICAL",
  },
  warning: {
    bg: "alert-warning",
    border: "border-l-amber-500",
    icon: "⚠️",
    label: "WARNING",
  },
  info: {
    bg: "alert-info",
    border: "border-l-cyan-500",
    icon: "ℹ️",
    label: "INFO",
  },
};

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function AlertItem({
  alert,
  onAcknowledge,
  onDismiss,
  onEscalate,
  onClick,
}: {
  alert: Alert;
  onAcknowledge?: () => void;
  onDismiss?: () => void;
  onEscalate?: () => void;
  onClick?: () => void;
}) {
  // Normalize severity to lowercase and provide fallback
  const severityStr = (alert.severity || "info").toLowerCase() as AlertSeverity;
  const config = severityConfig[severityStr] || severityConfig.info;

  return (
    <div
      className={`${config.bg} p-4 rounded-r-lg mb-3 group cursor-pointer hover:bg-opacity-80 transition-all`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm">{config.icon}</span>
            <span
              className={`text-xs font-bold uppercase tracking-wider ${
                severityStr === "critical"
                  ? "text-red-400"
                  : severityStr === "warning"
                    ? "text-amber-400"
                    : "text-cyan-400"
              }`}
            >
              {config.label}
            </span>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs text-slate-400">
              {formatTimestamp(alert.timestamp || new Date().toISOString())}
            </span>
          </div>

          <p className="font-medium text-sm truncate">
            {(alert.type || "UNKNOWN_ALERT").replace(/_/g, " ")}
          </p>
          <p className="text-sm text-slate-400 mt-1 line-clamp-2">
            {alert.message}
          </p>

          {alert.acknowledged && (
            <div className="flex items-center gap-1 mt-2 text-xs text-emerald-400">
              <CheckIcon className="w-3 h-3" />
              <span>Acknowledged</span>
              {alert.acknowledgedAt && (
                <span className="text-slate-500">
                  at {formatTimestamp(alert.acknowledgedAt)}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {!alert.acknowledged && onAcknowledge && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAcknowledge();
              }}
              className="p-1.5 rounded bg-emerald-500/20 hover:bg-emerald-500/40 text-emerald-400 transition-colors"
              title="Acknowledge"
            >
              <CheckIcon className="w-4 h-4" />
            </button>
          )}

          {severityStr === "critical" &&
            !alert.escalatedAt &&
            onEscalate && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onEscalate();
                }}
                className="p-1.5 rounded bg-amber-500/20 hover:bg-amber-500/40 text-amber-400 transition-colors"
                title="Escalate"
              >
                <ArrowUpIcon className="w-4 h-4" />
              </button>
            )}

          {onDismiss && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDismiss();
              }}
              className="p-1.5 rounded bg-slate-500/20 hover:bg-slate-500/40 text-slate-400 transition-colors"
              title="Dismiss"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function AlertPanel({
  alerts,
  maxVisible = 10,
  onAcknowledge,
  onDismiss,
  onEscalate,
  onAlertClick,
}: AlertPanelProps) {
  const visibleAlerts = alerts.slice(0, maxVisible);
  const hiddenCount = alerts.length - maxVisible;

  const criticalCount = alerts.filter(
    (a) => (a.severity || "").toLowerCase() === "critical" && !a.acknowledged,
  ).length;
  const warningCount = alerts.filter(
    (a) => (a.severity || "").toLowerCase() === "warning" && !a.acknowledged,
  ).length;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-lg">Active Alerts</h3>
        <div className="flex items-center gap-2">
          {criticalCount > 0 && (
            <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded-full text-xs font-medium">
              {criticalCount} Critical
            </span>
          )}
          {warningCount > 0 && (
            <span className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded-full text-xs font-medium">
              {warningCount} Warning
            </span>
          )}
        </div>
      </div>

      {/* Alert List */}
      <div className="flex-1 overflow-y-auto pr-2 -mr-2">
        {alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mb-4">
              <CheckIcon className="w-8 h-8 text-emerald-400" />
            </div>
            <p className="text-slate-400 font-medium">All Clear</p>
            <p className="text-sm text-slate-500 mt-1">No active alerts</p>
          </div>
        ) : (
          <>
            {visibleAlerts.map((alert) => (
              <AlertItem
                key={alert.id}
                alert={alert}
                onAcknowledge={
                  onAcknowledge ? () => onAcknowledge(alert.alertId) : undefined
                }
                onDismiss={
                  onDismiss ? () => onDismiss(alert.alertId) : undefined
                }
                onEscalate={
                  onEscalate ? () => onEscalate(alert.alertId) : undefined
                }
                onClick={onAlertClick ? () => onAlertClick(alert) : undefined}
              />
            ))}

            {hiddenCount > 0 && (
              <button className="w-full py-3 text-center text-sm text-slate-400 hover:text-white transition-colors">
                View {hiddenCount} more alerts
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default AlertPanel;
