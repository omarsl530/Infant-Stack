import { useState, useEffect, useCallback } from "react";
import {
  BellAlertIcon,
  UserGroupIcon,
  ShieldCheckIcon,
  Cog6ToothIcon,
  XMarkIcon,
  UserIcon,
  HeartIcon,
  ArrowPathIcon,
  ArrowRightOnRectangleIcon,
  HomeIcon,
} from "@heroicons/react/24/outline";
import { useAuth } from "./AuthContext";
import * as api from "./api";

// =============================================================================
// Types
// =============================================================================

interface Infant {
  id: string;
  tagId: string;
  name: string;
  ward: string;
  room: string;
  motherName: string;
  motherTagId: string;
  status: "active" | "inactive" | "alert";
  lastSeen: string;
  dateOfBirth?: string;
  weight?: string;
}

interface Mother {
  id: string;
  tagId: string;
  name: string;
  room: string;
  contactNumber: string;
}

interface Alert {
  id: string;
  type: string;
  severity: "info" | "warning" | "critical";
  message: string;
  tagId: string;
  timestamp: string;
}

// =============================================================================
// Modal Component
// =============================================================================

function Modal({
  isOpen,
  onClose,
  title,
  children,
}: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative bg-slate-800 rounded-2xl border border-slate-700 shadow-2xl w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <h2 className="text-xl font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-700 transition-colors"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

// =============================================================================
// Form Components
// =============================================================================

function FormInput({
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  required = false,
}: {
  label: string;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-slate-300 mb-2">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
        required={required}
      />
    </div>
  );
}

function FormSelect({
  label,
  value,
  onChange,
  options,
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  required?: boolean;
}) {
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-slate-300 mb-2">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
        required={required}
      >
        <option value="">Select...</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// =============================================================================
// Status Badge Component
// =============================================================================

function StatusBadge({ status }: { status: Infant["status"] }) {
  const styles = {
    active: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    inactive: "bg-gray-500/20 text-gray-400 border-gray-500/30",
    alert: "bg-red-500/20 text-red-400 border-red-500/30 animate-pulse",
  };

  return (
    <span
      className={`px-3 py-1 rounded-full text-xs font-medium border ${styles[status]}`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

// =============================================================================
// Stat Card Component
// =============================================================================

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}: {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  return (
    <div className="glass-card p-6 transition-transform hover:scale-[1.02] cursor-pointer">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400 mb-1">{title}</p>
          <p className="text-3xl font-bold">{value}</p>
        </div>
        <div className={`p-3 rounded-xl ${color}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Infant Card Component
// =============================================================================

function InfantCard({
  infant,
  onViewDetails,
}: {
  infant: Infant;
  onViewDetails: () => void;
}) {
  return (
    <div
      className={`glass-card p-5 transition-all hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-500/10 ${
        infant.status === "alert" ? "border-red-500/50" : ""
      }`}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-lg">{infant.name}</h3>
          <p className="text-sm text-slate-400">Tag: {infant.tagId}</p>
        </div>
        <StatusBadge status={infant.status} />
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-400">Location</span>
          <span>
            {infant.ward} - Room {infant.room || "N/A"}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Mother</span>
          <span>{infant.motherName || "Unassigned"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Last Seen</span>
          <span className="text-emerald-400">{infant.lastSeen}</span>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-700/50">
        <button
          onClick={onViewDetails}
          className="w-full py-2 px-4 bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 rounded-lg text-sm font-medium transition-colors"
        >
          View Details
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// Alert Item Component
// =============================================================================

function AlertItem({
  alert,
  onDismiss,
}: {
  alert: Alert;
  onDismiss: () => void;
}) {
  const severityStyles = {
    info: "border-l-cyan-500 bg-cyan-500/10",
    warning: "border-l-amber-500 bg-amber-500/10",
    critical: "border-l-red-500 bg-red-500/10",
  };

  return (
    <div
      className={`p-4 border-l-4 ${severityStyles[alert.severity]} rounded-r-lg mb-3 group`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="font-medium">{alert.type}</p>
          <p className="text-sm text-slate-400 mt-1">{alert.message}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className="text-xs text-slate-500">{alert.timestamp}</span>
          <button
            onClick={onDismiss}
            className="text-xs text-slate-500 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Main App
// =============================================================================

export default function App() {
  const { user, logout, isAdmin } = useAuth();
  const [infants, setInfants] = useState<Infant[]>([]);
  const [mothers, setMothers] = useState<Mother[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [showAddMother, setShowAddMother] = useState(false);
  const [showAddInfant, setShowAddInfant] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [selectedInfant, setSelectedInfant] = useState<Infant | null>(null);

  // Form states
  const [motherForm, setMotherForm] = useState({
    name: "",
    room: "",
    contact: "",
  });
  const [infantForm, setInfantForm] = useState({
    name: "",
    ward: "",
    room: "",
    dob: "",
    weight: "",
    motherId: "",
  });

  // Generate next tag IDs
  const nextInfantTag = `INF-${String(infants.length + 1).padStart(3, "0")}`;
  const nextMotherTag = `MOM-${String(mothers.length + 1).padStart(3, "0")}`;

  // Fetch data from API
  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [infantsData, mothersData, alertsData] = await Promise.all([
        api.fetchInfants(),
        api.fetchMothers(),
        api.fetchAlerts(),
      ]);

      setInfants(
        infantsData.map((i) => ({
          id: i.id,
          tagId: i.tag_id,
          name: i.name,
          ward: i.ward,
          room: i.room || "",
          motherName: i.mother_name || "Unassigned",
          motherTagId: i.mother_tag_id || "",
          status: (i.tag_status === "active"
            ? "active"
            : i.tag_status === "alert"
              ? "alert"
              : "inactive") as Infant["status"],
          lastSeen: "Just now",
          dateOfBirth: i.date_of_birth || undefined,
        })),
      );

      setMothers(
        mothersData.map((m) => ({
          id: m.id,
          tagId: m.tag_id,
          name: m.name,
          room: m.room || "",
          contactNumber: m.contact_number || "",
        })),
      );

      setAlerts(
        alertsData.map((a) => ({
          id: a.id,
          type: a.alert_type,
          severity: a.severity as Alert["severity"],
          message: a.message,
          tagId: a.tag_id || "",
          timestamp: new Date(a.created_at).toLocaleTimeString(),
        })),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const activeCount = infants.filter((i) => i.status === "active").length;

  // Handlers
  const handleAddMother = async () => {
    if (!motherForm.name || !motherForm.room) {
      setError("Mother Name and Room Number are required");
      setTimeout(() => setError(null), 3000);
      return;
    }

    try {
      await api.createMother({
        tag_id: nextMotherTag,
        name: motherForm.name,
        room: motherForm.room,
        contact_number: motherForm.contact,
      });

      setMotherForm({ name: "", room: "", contact: "" });
      setShowAddMother(false);
      await loadData(); // Refresh
    } catch (err) {
      console.error("Failed to add mother:", err);
      setError(err instanceof Error ? err.message : "Failed to add mother");
      // Clear error after 5 seconds
      setTimeout(() => setError(null), 5000);
    }
  };

  // Manual pairing state
  const [pairingMotherId, setPairingMotherId] = useState("");

  const handleAddInfant = async () => {
    if (!infantForm.name || !infantForm.ward || !infantForm.room) {
      setError("Baby Name, Ward, and Room Number are required");
      setTimeout(() => setError(null), 3000);
      return;
    }

    try {
      const newInfant = await api.createInfant({
        tag_id: nextInfantTag,
        name: infantForm.name,
        ward: infantForm.ward,
        room: infantForm.room,
        date_of_birth: infantForm.dob || undefined,
        weight: infantForm.weight || undefined,
      });

      // If mother is selected, pair them immediately
      if (infantForm.motherId) {
        try {
          await api.pairInfantToMother(newInfant.id, infantForm.motherId);
        } catch (pairErr) {
          console.error("Infant created but pairing failed:", pairErr);
          setError("Infant created but pairing failed. Please pair manually.");
          setTimeout(() => setError(null), 5000);
        }
      }

      setInfantForm({
        name: "",
        ward: "",
        room: "",
        dob: "",
        weight: "",
        motherId: "",
      });
      setShowAddInfant(false);
      await loadData(); // Refresh
    } catch (err) {
      console.error("Failed to add infant:", err);
      setError(err instanceof Error ? err.message : "Failed to add baby");
      setTimeout(() => setError(null), 5000);
    }
  };

  const handleManualPairing = async () => {
    if (!selectedInfant || !pairingMotherId) return;
    try {
      await api.pairInfantToMother(selectedInfant.id, pairingMotherId);
      setPairingMotherId("");
      setSelectedInfant(null); // Close modal to refresh
      await loadData();
    } catch (err) {
      console.error("Pairing failed:", err);
      setError("Failed to pair infant to mother");
      setTimeout(() => setError(null), 3000);
    }
  };

  const handleDismissAlert = async (alertId: string) => {
    try {
      await api.dismissAlert(alertId);
      setAlerts(alerts.filter((a) => a.id !== alertId));
    } catch (err) {
      console.error("Failed to dismiss alert:", err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <ArrowPathIcon className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-800/80 backdrop-blur-lg border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <ShieldCheckIcon className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold gradient-text">
                  Infant-Stack
                </h1>
                <p className="text-xs text-slate-400">Nurse Dashboard</p>
              </div>
            </div>

            <div className="flex items-center gap-6">
              {error && (
                <span className="text-sm text-red-400 bg-red-500/20 px-3 py-1 rounded">
                  {error}
                </span>
              )}

              <button
                onClick={loadData}
                className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
                title="Refresh data"
              >
                <ArrowPathIcon className="w-5 h-5" />
              </button>

              <div className="text-right">
                <p className="text-sm font-medium">
                  {currentTime.toLocaleTimeString()}
                </p>
                <p className="text-xs text-slate-400">
                  {currentTime.toLocaleDateString()}
                </p>
              </div>

              <button
                onClick={() => setShowSettings(true)}
                className="relative p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
              >
                <BellAlertIcon className="w-6 h-6" />
                {alerts.length > 0 && (
                  <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs flex items-center justify-center">
                    {alerts.length}
                  </span>
                )}
              </button>

              <button
                onClick={() => (window.location.href = "http://localhost:3003")}
                className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
                title="Back to Hub"
              >
                <HomeIcon className="w-6 h-6" />
              </button>

              <button
                onClick={() => setShowSettings(true)}
                className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
              >
                <Cog6ToothIcon className="w-6 h-6" />
              </button>

              {/* User Info & Logout */}
              <div className="flex items-center gap-3 pl-4 border-l border-slate-700">
                <div className="text-right">
                  <p className="text-sm font-medium">
                    {user?.fullName || "User"}
                  </p>
                  <p className="text-xs text-slate-400">
                    {isAdmin() ? (
                      <span className="text-amber-400">Admin</span>
                    ) : (
                      <span className="text-blue-400">User</span>
                    )}
                  </p>
                </div>
                <button
                  onClick={() => logout()}
                  className="p-2 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                  title="Logout"
                >
                  <ArrowRightOnRectangleIcon className="w-6 h-6" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3 mb-8">
          <button
            onClick={() => setShowAddMother(true)}
            className="flex items-center gap-2 px-4 py-2 bg-pink-600 hover:bg-pink-700 rounded-lg text-sm font-medium transition-colors"
          >
            <HeartIcon className="w-4 h-4" />
            Add Mother
          </button>
          <button
            onClick={() => setShowAddInfant(true)}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-sm font-medium transition-colors"
          >
            <UserIcon className="w-4 h-4" />
            Add Baby
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Infants"
            value={infants.length}
            icon={UserGroupIcon}
            color="bg-blue-500/20 text-blue-400"
          />
          <StatCard
            title="Active Tags"
            value={activeCount}
            icon={ShieldCheckIcon}
            color="bg-emerald-500/20 text-emerald-400"
          />
          <StatCard
            title="Active Alerts"
            value={alerts.length}
            icon={BellAlertIcon}
            color="bg-red-500/20 text-red-400"
          />
          <StatCard
            title="Mothers Registered"
            value={mothers.length}
            icon={HeartIcon}
            color="bg-pink-500/20 text-pink-400"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Infants Grid */}
          <div className="lg:col-span-2">
            <h2 className="text-xl font-semibold mb-6">Active Infants</h2>
            {infants.length === 0 ? (
              <div className="glass-card p-8 text-center text-slate-400">
                No infants registered yet. Click "Add Baby" to get started.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {infants.map((infant) => (
                  <InfantCard
                    key={infant.id}
                    infant={infant}
                    onViewDetails={() => setSelectedInfant(infant)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Alerts Panel */}
          <div>
            <h2 className="text-xl font-semibold mb-6">Recent Alerts</h2>
            <div className="glass-card p-4">
              {alerts.length > 0 ? (
                alerts.map((alert) => (
                  <AlertItem
                    key={alert.id}
                    alert={alert}
                    onDismiss={() => handleDismissAlert(alert.id)}
                  />
                ))
              ) : (
                <p className="text-center text-slate-400 py-8">
                  No active alerts ✓
                </p>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Add Mother Modal */}
      <Modal
        isOpen={showAddMother}
        onClose={() => setShowAddMother(false)}
        title="Add New Mother"
      >
        <p className="text-sm text-slate-400 mb-4">
          Tag ID:{" "}
          <span className="text-blue-400 font-mono">{nextMotherTag}</span>
        </p>
        <FormInput
          label="Full Name"
          value={motherForm.name}
          onChange={(v) => setMotherForm({ ...motherForm, name: v })}
          placeholder="Enter mother's full name"
          required
        />
        <FormInput
          label="Room Number"
          value={motherForm.room}
          onChange={(v) => setMotherForm({ ...motherForm, room: v })}
          placeholder="e.g., 101"
          required
        />
        <FormInput
          label="Contact Number"
          type="tel"
          value={motherForm.contact}
          onChange={(v) => setMotherForm({ ...motherForm, contact: v })}
          placeholder="+966-555-0000"
        />
        <button
          onClick={handleAddMother}
          className="w-full py-3 bg-pink-600 hover:bg-pink-700 rounded-lg font-medium transition-colors mt-4"
        >
          Register Mother
        </button>
      </Modal>

      {/* Add Infant Modal */}
      <Modal
        isOpen={showAddInfant}
        onClose={() => setShowAddInfant(false)}
        title="Add New Baby"
      >
        <p className="text-sm text-slate-400 mb-4">
          Tag ID:{" "}
          <span className="text-blue-400 font-mono">{nextInfantTag}</span>
        </p>
        <FormInput
          label="Baby Name"
          value={infantForm.name}
          onChange={(v) => setInfantForm({ ...infantForm, name: v })}
          placeholder="e.g., Baby Smith"
          required
        />
        <FormSelect
          label="Ward"
          value={infantForm.ward}
          onChange={(v) => setInfantForm({ ...infantForm, ward: v })}
          options={[
            { value: "Maternity A", label: "Maternity A" },
            { value: "Maternity B", label: "Maternity B" },
            { value: "NICU", label: "NICU" },
          ]}
          required
        />
        <FormInput
          label="Room Number"
          value={infantForm.room}
          onChange={(v) => setInfantForm({ ...infantForm, room: v })}
          placeholder="e.g., 101"
          required
        />
        <FormInput
          label="Date of Birth"
          type="date"
          value={infantForm.dob}
          onChange={(v) => setInfantForm({ ...infantForm, dob: v })}
        />
        <FormInput
          label="Weight"
          value={infantForm.weight}
          onChange={(v) => setInfantForm({ ...infantForm, weight: v })}
          placeholder="e.g., 3.2 kg"
        />
        <FormSelect
          label="Assign Mother"
          value={infantForm.motherId}
          onChange={(v) => setInfantForm({ ...infantForm, motherId: v })}
          options={mothers.map((m) => ({
            value: m.id,
            label: `${m.name} (${m.tagId})`,
          }))}
        />
        <p className="text-xs text-slate-500 -mt-2 mb-4">
          Leave empty to assign later
        </p>
        <button
          onClick={handleAddInfant}
          className="w-full py-3 bg-cyan-600 hover:bg-cyan-700 rounded-lg font-medium transition-colors mt-4"
        >
          Register Baby
        </button>
      </Modal>

      {/* View Details Modal */}
      <Modal
        isOpen={selectedInfant !== null}
        onClose={() => {
          setSelectedInfant(null);
          setPairingMotherId("");
        }}
        title="Infant Details"
      >
        {selectedInfant && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">{selectedInfant.name}</h3>
              <StatusBadge
                status={selectedInfant.motherTagId ? "active" : "inactive"}
              />
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4 space-y-3">
              <div className="flex justify-between">
                <span className="text-slate-400">Tag ID</span>
                <span className="font-mono text-blue-400">
                  {selectedInfant.tagId}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Ward</span>
                <span>{selectedInfant.ward}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Room</span>
                <span>{selectedInfant.room}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Mother</span>
                <span
                  className={
                    selectedInfant.motherName !== "Unassigned"
                      ? "text-pink-400 font-medium"
                      : "text-slate-500"
                  }
                >
                  {selectedInfant.motherName}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Mother Tag</span>
                <span className="font-mono text-pink-400">
                  {selectedInfant.motherTagId || "Not assigned"}
                </span>
              </div>
              {selectedInfant.dateOfBirth && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Date of Birth</span>
                  <span>
                    {new Date(selectedInfant.dateOfBirth).toLocaleDateString()}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-slate-400">Last Seen</span>
                <span className="text-emerald-400">
                  {selectedInfant.lastSeen}
                </span>
              </div>
            </div>

            {/* Manual Pairing UI - only show if not paired */}
            {!selectedInfant.motherTagId && (
              <div className="mt-4 pt-4 border-t border-slate-700">
                <h4 className="font-medium mb-3 text-sm text-slate-300">
                  Pair with Mother
                </h4>
                <div className="gap-2">
                  <FormSelect
                    label="Select Mother"
                    value={pairingMotherId}
                    onChange={setPairingMotherId}
                    options={[
                      { value: "", label: "Select a mother..." },
                      ...mothers.map((m) => ({
                        value: m.id,
                        label: `${m.name} (${m.tagId})`,
                      })),
                    ]}
                  />
                  <button
                    onClick={handleManualPairing}
                    disabled={!pairingMotherId}
                    className="w-full mt-2 py-2 bg-pink-600/20 hover:bg-pink-600/40 text-pink-400 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Link Mother
                  </button>
                </div>
              </div>
            )}

            {/* Action Buttons - Admin Only */}
            {isAdmin() && (
              <div className="mt-4 pt-4 border-t border-slate-700 flex gap-2">
                <button
                  onClick={async () => {
                    if (
                      confirm(
                        "Are you sure you want to delete this baby? This cannot be undone.",
                      )
                    ) {
                      try {
                        await api.deleteInfant(selectedInfant.id);
                        setSelectedInfant(null);
                        await loadData();
                      } catch (err) {
                        setError("Failed to delete infant");
                        setTimeout(() => setError(null), 3000);
                      }
                    }
                  }}
                  className="flex-1 py-2 bg-red-600/20 hover:bg-red-600/40 text-red-400 rounded-lg text-sm font-medium transition-colors"
                >
                  Delete Baby
                </button>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Settings Modal */}
      <Modal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        title="Settings"
      >
        <div className="space-y-4">
          <div className="bg-slate-900/50 rounded-lg p-4">
            <h3 className="font-medium mb-2">System Status</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">API Gateway</span>
                <span className="text-emerald-400">● Connected</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Database</span>
                <span className="text-emerald-400">● Healthy</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">MQTT Broker</span>
                <span className="text-emerald-400">● Running</span>
              </div>
            </div>
          </div>

          <div className="bg-slate-900/50 rounded-lg p-4">
            <h3 className="font-medium mb-2">Quick Stats</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Total Infants</span>
                <span>{infants.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Total Mothers</span>
                <span>{mothers.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Active Pairings</span>
                <span>{infants.filter((i) => i.motherTagId).length}</span>
              </div>
            </div>
          </div>

          {/* Registered Mothers List */}
          <div className="bg-slate-900/50 rounded-lg p-4">
            <h3 className="font-medium mb-3">Registered Mothers</h3>
            {mothers.length === 0 ? (
              <p className="text-sm text-slate-400">
                No mothers registered yet.
              </p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {mothers.map((mother) => (
                  <div
                    key={mother.id}
                    className="flex items-center justify-between bg-slate-800/50 rounded-lg p-2"
                  >
                    <div>
                      <p className="text-sm font-medium">{mother.name}</p>
                      <p className="text-xs text-slate-400 font-mono">
                        {mother.tagId}
                      </p>
                    </div>
                    {isAdmin() && (
                      <button
                        onClick={async () => {
                          if (
                            confirm(
                              `Delete ${mother.name}? This will also remove any pairings.`,
                            )
                          ) {
                            try {
                              await api.deleteMother(mother.id);
                              await loadData();
                            } catch (err) {
                              setError("Failed to delete mother");
                              setTimeout(() => setError(null), 3000);
                            }
                          }
                        }}
                        className="p-1.5 text-red-400 hover:bg-red-600/20 rounded transition-colors"
                        title="Delete mother"
                      >
                        <XMarkIcon className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Modal>
    </div>
  );
}
