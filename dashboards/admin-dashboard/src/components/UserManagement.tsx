import { useState } from 'react';
import {
  PlusIcon,
  MagnifyingGlassIcon,
  PencilSquareIcon,
  TrashIcon,
  KeyIcon,
} from '@heroicons/react/24/outline';
import { User } from '../types';
import UserFormModal from './UserFormModal';
import ConfirmModal from './ConfirmModal';

// Mock data for initial development
const mockUsers: User[] = [
  {
    id: '1',
    email: 'admin@hospital.org',
    first_name: 'Admin',
    last_name: 'User',
    role: 'admin',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    last_login: '2026-02-01T12:00:00Z',
  },
  {
    id: '2',
    email: 'nurse.jane@hospital.org',
    first_name: 'Jane',
    last_name: 'Doe',
    role: 'nurse',
    is_active: true,
    created_at: '2026-01-15T00:00:00Z',
    last_login: '2026-02-01T10:30:00Z',
  },
  {
    id: '3',
    email: 'security.john@hospital.org',
    first_name: 'John',
    last_name: 'Smith',
    role: 'security',
    is_active: true,
    created_at: '2026-01-20T00:00:00Z',
    last_login: '2026-02-01T08:00:00Z',
  },
  {
    id: '4',
    email: 'viewer@hospital.org',
    first_name: 'View',
    last_name: 'Only',
    role: 'viewer',
    is_active: false,
    created_at: '2026-01-25T00:00:00Z',
    last_login: null,
  },
];

export default function UserManagement() {
  const [users, setUsers] = useState<User[]>(mockUsers);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  
  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [deletingUser, setDeletingUser] = useState<User | null>(null);
  const [resettingUser, setResettingUser] = useState<User | null>(null);

  // Filter users
  const filteredUsers = users.filter((user) => {
    const matchesSearch = searchQuery
      ? user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.first_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.last_name.toLowerCase().includes(searchQuery.toLowerCase())
      : true;
    
    const matchesRole = roleFilter ? user.role === roleFilter : true;
    const matchesStatus = statusFilter
      ? statusFilter === 'active' ? user.is_active : !user.is_active
      : true;
    
    return matchesSearch && matchesRole && matchesStatus;
  });

  // Load users from API (uncomment for production)
  // useEffect(() => {
  //   loadUsers();
  // }, []);
  
  // const loadUsers = async () => {
  //   setIsLoading(true);
  //   try {
  //     const response = await fetchUsers();
  //     setUsers(response.users);
  //   } catch (error) {
  //     console.error('Failed to load users:', error);
  //   } finally {
  //     setIsLoading(false);
  //   }
  // };

  const handleCreateUser = async (data: Partial<User> & { password?: string }) => {
    try {
      // const newUser = await createUser(data);
      // setUsers([newUser, ...users]);
      
      // Mock: add user locally
      const newUser: User = {
        email: data.email || '',
        first_name: data.first_name || '',
        last_name: data.last_name || '',
        role: data.role || 'viewer',
        is_active: data.is_active ?? true,
        id: Date.now().toString(),
        created_at: new Date().toISOString(),
        last_login: null,
      };
      setUsers([newUser, ...users]);
      setShowAddModal(false);
    } catch (error) {
      console.error('Failed to create user:', error);
    }
  };

  const handleUpdateUser = async (data: Partial<User>) => {
    if (!editingUser) return;
    
    try {
      // const updated = await updateUser(editingUser.id, data);
      // setUsers(users.map((u) => u.id === updated.id ? updated : u));
      
      // Mock: update locally
      setUsers(users.map((u) => u.id === editingUser.id ? { ...u, ...data } : u));
      setEditingUser(null);
    } catch (error) {
      console.error('Failed to update user:', error);
    }
  };

  const handleDeleteUser = async () => {
    if (!deletingUser) return;
    
    try {
      // await deleteUser(deletingUser.id);
      
      // Mock: remove locally
      setUsers(users.filter((u) => u.id !== deletingUser.id));
      setDeletingUser(null);
    } catch (error) {
      console.error('Failed to delete user:', error);
    }
  };

  const handleResetPassword = async () => {
    if (!resettingUser) return;
    
    try {
      // await resetUserPassword(resettingUser.id);
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
            <option value="admin">Admin</option>
            <option value="nurse">Nurse</option>
            <option value="security">Security</option>
            <option value="viewer">Viewer</option>
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
                      ${user.role === 'admin' ? 'bg-gradient-to-br from-purple-500 to-purple-700' :
                        user.role === 'nurse' ? 'bg-gradient-to-br from-blue-500 to-blue-700' :
                        user.role === 'security' ? 'bg-gradient-to-br from-orange-500 to-orange-700' :
                        'bg-gradient-to-br from-slate-500 to-slate-700'
                      }`}
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
                  <span className={`badge badge-${user.role}`}>{user.role}</span>
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
        
        {filteredUsers.length === 0 && (
          <div className="p-8 text-center text-slate-400">
            No users found matching your criteria.
          </div>
        )}
      </div>

      {/* Modals */}
      {showAddModal && (
        <UserFormModal
          onClose={() => setShowAddModal(false)}
          onSubmit={handleCreateUser}
        />
      )}
      
      {editingUser && (
        <UserFormModal
          user={editingUser}
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
