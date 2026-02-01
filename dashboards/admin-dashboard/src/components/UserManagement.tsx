import { useState, useEffect } from 'react';
import {
  PlusIcon,
  MagnifyingGlassIcon,
  PencilSquareIcon,
  TrashIcon,
  KeyIcon,
} from '@heroicons/react/24/outline';
import { User, Role } from '../types';
import { fetchUsers, fetchRoles, createUser, updateUser, deleteUser, resetUserPassword, assignRole } from '../api';
import UserFormModal from './UserFormModal';
import ConfirmModal from './ConfirmModal';

export default function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  
  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [deletingUser, setDeletingUser] = useState<User | null>(null);
  const [resettingUser, setResettingUser] = useState<User | null>(null);

  useEffect(() => {
    loadData();
  }, []);
  
  const loadData = async () => {
    setIsLoading(true);
    try {
      const [usersData, rolesData] = await Promise.all([
        fetchUsers(),
        fetchRoles()
      ]);
      setUsers(usersData.users || []); // Assuming response wrapper
      setRoles(rolesData);
    } catch (error) {
      console.error('Failed to load data:', error);
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
      ? statusFilter === 'active' ? user.is_active : !user.is_active
      : true;
    
    return matchesSearch && matchesRole && matchesStatus;
  });

  const handleCreateUser = async (data: Partial<User> & { password?: string }) => {
    try {
      const newUser = await createUser(data as any);
      setUsers([newUser, ...users]);
      setShowAddModal(false);
    } catch (error) {
      console.error('Failed to create user:', error);
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
      if (Object.keys(data).some(k => k !== 'role')) {
          const result = await updateUser(editingUser.id, data);
          updatedUser = result;
      }

      setUsers(users.map((u) => u.id === editingUser.id ? updatedUser : u));
      setEditingUser(null);
    } catch (error) {
      console.error('Failed to update user:', error);
      throw error; // Let modal handle it
    }
  };

  const handleDeleteUser = async () => {
    if (!deletingUser) return;
    
    try {
      await deleteUser(deletingUser.id);
      setUsers(users.filter((u) => u.id !== deletingUser.id));
      setDeletingUser(null);
    } catch (error) {
      console.error('Failed to delete user:', error);
    }
  };

  const handleResetPassword = async () => {
    if (!resettingUser) return;
    
    try {
      await resetUserPassword(resettingUser.id);
      alert(`Password reset email sent to ${resettingUser.email}`);
      setResettingUser(null);
    } catch (error) {
      console.error('Failed to reset password:', error);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleString();
  };

  const getRoleBadgeColor = (roleName: string) => {
      // Simple hashing for color consistency or predefined map
      if (roleName === 'admin') return 'admin';
      if (roleName === 'nurse') return 'nurse';
      if (roleName === 'security') return 'security';
      if (roleName === 'viewer') return 'slate';
      return 'slate'; // Default for custom roles for now
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
            {roles.map(role => (
                <option key={role.id} value={role.name}>{role.name}</option>
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
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold
                      bg-gradient-to-br from-slate-500 to-slate-700`}
                    >
                      {user.first_name.charAt(0)}{user.last_name.charAt(0)}
                    </div>
                    <span className="text-white font-medium">
                      {user.first_name} {user.last_name}
                    </span>
                  </div>
                </td>
                <td className="text-slate-300">{user.email}</td>
                <td>
                  <span className={`badge badge-${getRoleBadgeColor(user.role)}`}>{user.role}</span>
                </td>
                <td>
                  <span className={`badge ${user.is_active ? 'badge-active' : 'badge-inactive'}`}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="text-slate-400 text-sm">{formatDate(user.last_login)}</td>
                <td className="text-slate-400 text-sm">{formatDate(user.created_at)}</td>
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
                      onClick={() => setResettingUser(user)}
                      className="p-1.5 text-slate-400 hover:text-amber-400 hover:bg-slate-700 rounded"
                      title="Reset Password"
                    >
                      <KeyIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setDeletingUser(user)}
                      className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-700 rounded"
                      title="Delete"
                    >
                      <TrashIcon className="w-4 h-4" />
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
    </div>
  );
}
