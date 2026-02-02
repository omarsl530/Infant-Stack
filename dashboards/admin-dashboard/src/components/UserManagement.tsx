import { useState, useEffect } from "react";
import {
  PlusIcon,
  MagnifyingGlassIcon,
  PencilSquareIcon,
  TrashIcon,
  KeyIcon,
} from "@heroicons/react/24/outline";
import { User, Role } from "../types";
import {
  fetchUsers,
  fetchRoles,
  createUser,
  updateUser,
  deleteUser,
  resetUserPassword,
  updateUserPassword,
  assignRole,
} from "../api";
import UserFormModal from "./UserFormModal";
import ConfirmModal from "./ConfirmModal";

export default function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [deletingUser, setDeletingUser] = useState<User | null>(null);
  const [resettingUser, setResettingUser] = useState<User | null>(null);
  const [passwordResetUser, setPasswordResetUser] = useState<User | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [usersData, rolesData] = await Promise.all([
        fetchUsers(),
        fetchRoles(),
      ]);
      setUsers(usersData.users || []); // Assuming response wrapper
      setRoles(rolesData);
    } catch (error) {
      console.error("Failed to load data:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Filter users
  const filteredUsers = users.filter((user) => {
    const matchesSearch = searchQuery
      ? user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.first_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.last_name.toLowerCase().includes(searchQuery.toLowerCase())
      : true;

    // Role filter is string based now
    const matchesRole = roleFilter ? user.role === roleFilter : true;
    const matchesStatus = statusFilter
      ? statusFilter === "active"
        ? user.is_active
        : !user.is_active
      : true;

    return matchesSearch && matchesRole && matchesStatus;
  });

  const handleCreateUser = async (
    data: Partial<User> & { password?: string },
  ) => {
    try {
      const newUser = await createUser(data as any);
      setUsers([newUser, ...users]);
      setShowAddModal(false);
    } catch (error) {
      console.error("Failed to create user:", error);
      throw error;
    }
  };

  const handleUpdateUser = async (data: Partial<User>) => {
    if (!editingUser) return;

    try {
      // If role changed, call assignRole too
      let updatedUser = { ...editingUser };

      if (data.role && data.role !== editingUser.role) {
        await assignRole(editingUser.id, data.role);
        updatedUser.role = data.role;
      }

      // Update other fields
      if (Object.keys(data).some((k) => k !== "role")) {
        const result = await updateUser(editingUser.id, data);
        updatedUser = result;
      }

      setUsers(users.map((u) => (u.id === editingUser.id ? updatedUser : u)));
      setEditingUser(null);
    } catch (error) {
      console.error("Failed to update user:", error);
      throw error; // Let modal handle it
    }
  };

  const handleDeleteUser = async () => {
    if (!deletingUser) return;

    try {
      await deleteUser(deletingUser.id);
      // Hard delete: remove from list
      setUsers((prevUsers) =>
        prevUsers.filter((u) => u.id !== deletingUser.id),
      );
      setDeletingUser(null);
    } catch (error) {
      console.error("Failed to delete user:", error);
    }
  };

  const handleResetPassword = async () => {
    if (!resettingUser) return;

    try {
      await resetUserPassword(resettingUser.id);
      alert(`Password reset email sent to ${resettingUser.email}`);
      setResettingUser(null);
    } catch (error) {
      console.error("Failed to reset password:", error);
    }
  };

  // Handle direct password update (Admin override)
  const handlePasswordUpdate = async (password: string) => {
    if (!passwordResetUser) return;
    try {
        await updateUserPassword(passwordResetUser.id, password);
        alert(`Password updated for ${passwordResetUser.email}`);
        setPasswordResetUser(null);
    } catch (error) {
        console.error("Failed to update password:", error);
        alert("Failed to update password.");
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleString();
  };

  const getRoleBadgeColor = (roleName: string) => {
    // Simple hashing for color consistency or predefined map
    if (roleName === "admin") return "admin";
    if (roleName === "nurse") return "nurse";
    if (roleName === "security") return "security";
    if (roleName === "viewer") return "slate";
    return "slate"; // Default for custom roles for now
  };

  return (
    <div className="space-y-6">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            placeholder="Search users..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="form-input pl-10"
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="form-select"
          >
            <option value="">All Roles</option>
            {roles.map((role) => (
              <option key={role.id} value={role.name}>
                {role.name}
              </option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="form-select"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>

          <button className="btn-primary" onClick={() => setShowAddModal(true)}>
            <PlusIcon className="w-5 h-5 mr-2" />
            Add User
          </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="glass-card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400">Loading users...</div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Last Login</th>
                <th>Created</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((user) => (
                <tr key={user.id}>
                  <td>
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold
                      bg-gradient-to-br from-slate-500 to-slate-700`}
                      >
                        {user.first_name.charAt(0)}
                        {user.last_name.charAt(0)}
                      </div>
                      <span className="text-white font-medium">
                        {user.first_name} {user.last_name}
                      </span>
                    </div>
                  </td>
                  <td className="text-slate-300">{user.email}</td>
                  <td>
                    <span
                      className={`badge badge-${getRoleBadgeColor(user.role)}`}
                    >
                      {user.role}
                    </span>
                  </td>
                  <td>
                    <span
                      className={`badge ${user.is_active ? "badge-active" : "badge-inactive"}`}
                    >
                      {user.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="text-slate-400 text-sm">
                    {formatDate(user.last_login)}
                  </td>
                  <td className="text-slate-400 text-sm">
                    {formatDate(user.created_at)}
                  </td>
                  <td>
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setEditingUser(user)}
                        className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded"
                        title="Edit"
                      >
                        <PencilSquareIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeletingUser(user)}
                        disabled={["admin@infantstack.com", "nurse@infantstack.com"].includes(user.email)}
                        className={`p-1.5 rounded ${
                          ["admin@infantstack.com", "nurse@infantstack.com"].includes(user.email)
                            ? "text-slate-600 cursor-not-allowed"
                            : "text-slate-400 hover:text-red-400 hover:bg-slate-700"
                        }`}
                        title={
                          ["admin@infantstack.com", "nurse@infantstack.com"].includes(user.email)
                            ? "Protected User"
                            : "Delete"
                        }
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                      <button
                         onClick={() => setPasswordResetUser(user)}
                         className="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-slate-700 rounded ml-1"
                         title="Change Password"
                      >
                        <KeyIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {!isLoading && filteredUsers.length === 0 && (
          <div className="p-8 text-center text-slate-400">
            No users found matching your criteria.
          </div>
        )}
      </div>

      {/* Modals */}
      {showAddModal && (
        <UserFormModal
          roles={roles}
          onClose={() => setShowAddModal(false)}
          onSubmit={handleCreateUser}
        />
      )}

      {editingUser && (
        <UserFormModal
          user={editingUser}
          roles={roles}
          onClose={() => setEditingUser(null)}
          onSubmit={handleUpdateUser}
        />
      )}

      {deletingUser && (
        <ConfirmModal
          title="Delete User"
          message={`Are you sure you want to delete ${deletingUser.first_name} ${deletingUser.last_name}? This will deactivate their account.`}
          confirmLabel="Delete"
          confirmVariant="danger"
          onConfirm={handleDeleteUser}
          onCancel={() => setDeletingUser(null)}
        />
      )}

      {resettingUser && (
        <ConfirmModal
          title="Reset Password"
          message={`Are you sure you want to reset the password for ${resettingUser.email}? They will receive an email with instructions.`}
          confirmLabel="Reset Password"
          confirmVariant="primary"
          onConfirm={handleResetPassword}
          onCancel={() => setResettingUser(null)}
        />
      )}

      {/* Direct Password Update Modal */}
      {passwordResetUser && (
        <PasswordResetModal
          user={passwordResetUser}
          onConfirm={handlePasswordUpdate}
          onCancel={() => setPasswordResetUser(null)}
        />
      )}
    </div>
  );
}

function PasswordResetModal({
  user,
  onConfirm,
  onCancel,
}: {
  user: User;
  onConfirm: (password: string) => void;
  onCancel: () => void;
}) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault();
      if (password.length < 4) {
          setError("Password must be at least 4 characters");
          return;
      }
      onConfirm(password);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-slate-800 rounded-lg p-6 max-w-sm w-full border border-slate-700 shadow-xl">
        <h3 className="text-xl font-semibold text-white mb-2">Change Password</h3>
        <p className="text-slate-400 mb-6">
          Enter a new password for <span className="text-white font-medium">{user.email}</span>.
        </p>
        
        <form onSubmit={handleSubmit}>
            <input
              type="password"
              placeholder="New Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white mb-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              autoFocus
            />
            {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
            
            <div className="flex justify-end gap-3 mt-4">
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 text-slate-300 hover:text-white hover:bg-slate-700 rounded transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded transition-colors shadow-lg shadow-blue-900/20"
              >
                Update Password
              </button>
            </div>
        </form>
      </div>
    </div>
  );
}



function DeleteConfirmationModal({
  title,
  message,
  confirmLabel,
  confirmVariant,
  onConfirm,
  onCancel,
}: {
  title: string;
  message: string;
  confirmLabel: string;
  confirmVariant: "primary" | "danger";
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-slate-800 rounded-lg p-6 max-w-sm w-full border border-slate-700 shadow-xl">
        <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
        <p className="text-slate-400 mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-slate-300 hover:text-white hover:bg-slate-700 rounded transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-white rounded transition-colors shadow-lg ${
              confirmVariant === "danger"
                ? "bg-red-600 hover:bg-red-500 shadow-red-900/20"
                : "bg-blue-600 hover:bg-blue-500 shadow-blue-900/20"
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
