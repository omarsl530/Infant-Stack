import { useState, useEffect } from "react";
import {
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";
import { Role, RoleCreate, RoleUpdate } from "../types";
import { fetchRoles, createRole, updateRole, deleteRole } from "../api";
import RoleFormModal from "./RoleFormModal";
import ConfirmModal from "./ConfirmModal";

export default function RoleManager() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [deletingRole, setDeletingRole] = useState<Role | null>(null);

  useEffect(() => {
    loadRoles();
  }, []);

  const loadRoles = async () => {
    setIsLoading(true);
    try {
      const data = await fetchRoles();
      setRoles(data);
    } catch (err) {
      console.error("Failed to load roles:", err);
      setError("Failed to load roles");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateRole = async (data: RoleCreate | RoleUpdate) => {
    try {
      // Data from form matches RoleCreate interface (permissions is map)
      const newRole = await createRole(data as RoleCreate);
      setRoles([...roles, newRole]);
      setShowAddModal(false);
    } catch (err) {
      console.error("Failed to create role:", err);
      throw err; // Re-throw for modal to handle
    }
  };

  const handleUpdateRole = async (data: RoleCreate | RoleUpdate) => {
    if (!editingRole) return;
    try {
      const updated = await updateRole(editingRole.id, data as RoleUpdate);
      setRoles(roles.map((r) => (r.id === updated.id ? updated : r)));
      setEditingRole(null);
    } catch (err) {
      console.error("Failed to update role:", err);
      throw err;
    }
  };

  const handleDeleteRole = async () => {
    if (!deletingRole) return;
    try {
      await deleteRole(deletingRole.id);
      setRoles(roles.filter((r) => r.id !== deletingRole.id));
      setDeletingRole(null);
    } catch (err: any) {
      console.error("Failed to delete role:", err);
      alert(err.message || "Failed to delete role");
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString();
  };

  const getPermissionCount = (role: Role) => {
    // flatten permissions
    let count = 0;
    Object.values(role.permissions).forEach((actions) => {
      count += actions.length;
    });
    return count;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800 dark:text-white">
            Role Management
          </h2>
          <p className="text-slate-500 mt-1">
            Define roles and assign permissions.
          </p>
        </div>

        <button className="btn-primary" onClick={() => setShowAddModal(true)}>
          <PlusIcon className="w-5 h-5 mr-2" />
          Create Role
        </button>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-300 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Roles Table */}
      <div className="glass-card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400">Loading roles...</div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Role Name</th>
                <th>Description</th>
                <th>Users</th>
                <th>Permissions</th>
                <th>Type</th>
                <th>Created</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((role) => (
                <tr key={role.id}>
                  <td>
                    <div className="font-medium text-white">{role.name}</div>
                  </td>
                  <td
                    className="text-slate-300 text-sm max-w-xs truncate"
                    title={role.description || ""}
                  >
                    {role.description || "-"}
                  </td>
                  <td>
                    <div className="flex items-center gap-1 text-slate-300">
                      <div className="bg-slate-700 px-2 py-0.5 rounded-full text-xs">
                        {role.user_count || 0}
                      </div>
                    </div>
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <ShieldCheckIcon className="w-4 h-4 text-emerald-400" />
                      <span className="text-sm text-slate-300">
                        {getPermissionCount(role)} access rules
                      </span>
                    </div>
                  </td>
                  <td>
                    {role.is_system ? (
                      <span className="badge badge-admin">System</span>
                    ) : (
                      <span className="badge badge-viewer">Custom</span>
                    )}
                  </td>
                  <td className="text-slate-400 text-sm">
                    {formatDate(role.created_at)}
                  </td>
                  <td>
                    <div className="flex items-center justify-end gap-2">
                      {/* Cannot delete system roles, maybe allow view permissions logic */}
                      <button
                        onClick={() => setEditingRole(role)}
                        className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded"
                        title="Edit Role"
                      >
                        <PencilSquareIcon className="w-4 h-4" />
                      </button>
                      {!role.is_system && (
                        <button
                          onClick={() => setDeletingRole(role)}
                          className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-700 rounded"
                          title="Delete Role"
                        >
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modals */}
      {showAddModal && (
        <RoleFormModal
          onClose={() => setShowAddModal(false)}
          onSubmit={handleCreateRole}
        />
      )}

      {editingRole && (
        <RoleFormModal
          role={editingRole}
          onClose={() => setEditingRole(null)}
          onSubmit={handleUpdateRole}
        />
      )}

      {deletingRole && (
        <ConfirmModal
          title="Delete Role"
          message={`Are you sure you want to delete the role "${deletingRole.name}"? This action cannot be undone.`}
          confirmLabel="Delete"
          confirmVariant="danger"
          onConfirm={handleDeleteRole}
          onCancel={() => setDeletingRole(null)}
        />
      )}
    </div>
  );
}
