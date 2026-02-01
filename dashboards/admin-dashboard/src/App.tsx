import { useState, useEffect } from 'react';
import { useAuth } from 'react-oidc-context';
import ProtectedRoute from './components/ProtectedRoute';
import {
  UsersIcon,
  ShieldCheckIcon,
  ClipboardDocumentListIcon,
  Cog6ToothIcon,
  ChartBarIcon,
  ArrowRightOnRectangleIcon,
  MapIcon,
} from '@heroicons/react/24/outline';
import UserManagement from './components/UserManagement';
// PermissionMatrix removed
import RoleManager from './components/RoleManager';
import AuditLogViewer from './components/AuditLogViewer';
import ConfigEditor from './components/ConfigEditor';
import ZoneEditor from './components/ZoneEditor';
import { fetchDashboardStats } from './api';
import { DashboardStats } from './types';

type NavSection = 'users' | 'roles' | 'audit' | 'zones' | 'config' | 'stats';

const navItems: { id: NavSection; label: string; icon: React.ElementType }[] = [
  { id: 'users', label: 'Users', icon: UsersIcon },
  { id: 'roles', label: 'Roles', icon: ShieldCheckIcon },
  { id: 'audit', label: 'Audit Logs', icon: ClipboardDocumentListIcon },
  { id: 'zones', label: 'Zones', icon: MapIcon },
  { id: 'config', label: 'Configuration', icon: Cog6ToothIcon },
  { id: 'stats', label: 'Statistics', icon: ChartBarIcon },
];

function DashboardLayout() {
  const [activeSection, setActiveSection] = useState<NavSection>('users');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const auth = useAuth();
  const user = auth.user?.profile;

  const loadStats = async () => {
    try {
      const data = await fetchDashboardStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load dashboard stats:', error);
    }
  };

  useEffect(() => {
    loadStats();
    // Refresh stats every 30 seconds
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-surface-card border-r border-slate-700 flex flex-col">
        {/* Logo */}
        <div className="p-4 border-b border-slate-700">
          <h1 className="text-xl font-bold bg-gradient-to-r from-admin-400 to-admin-600 bg-clip-text text-transparent">
            Admin Dashboard
          </h1>
          <p className="text-xs text-slate-500 mt-1">Infant Security System</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-left transition-all
                ${activeSection === item.id
                  ? 'bg-admin-600/20 text-admin-400 border border-admin-500/30'
                  : 'text-slate-400 hover:bg-slate-700/50 hover:text-white'
                }`}
            >
              <item.icon className="w-5 h-5" />
              <span className="text-sm font-medium">{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-slate-700">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-admin-500 to-admin-700 flex items-center justify-center text-white text-sm font-bold uppercase">
              {user?.given_name?.[0]}{user?.family_name?.[0]}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.given_name} {user?.family_name}
              </p>
              <p className="text-xs text-slate-500 truncate" title={user?.email}>
                {user?.email}
              </p>
            </div>
          </div>
          <button 
            onClick={() => auth.signoutRedirect()}
            className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
          >
            <ArrowRightOnRectangleIcon className="w-3 h-3" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-surface-card border-b border-slate-700 flex items-center justify-between px-6">
          <div>
            <h2 className="text-lg font-semibold text-white capitalize">
              {navItems.find((item) => item.id === activeSection)?.label}
            </h2>
            <p className="text-xs text-slate-500">
              {new Date().toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>

          {/* Quick Stats */}
          <div className="flex items-center gap-6">
            <div className="text-right">
              <p className="text-xs text-slate-500">Total Users</p>
              <p className="text-lg font-semibold text-white">{stats?.users.total || '-'}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500">Active Sessions</p>
              <p className="text-lg font-semibold text-emerald-400">{stats?.users.active_sessions || '-'}</p>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeSection === 'users' && <UserManagement />}
          
          {activeSection === 'roles' && (
            <div className="p-2">
              <RoleManager />
            </div>
          )}
          
          {activeSection === 'audit' && (
            <div className="p-2">
              <AuditLogViewer />
            </div>
          )}
          
          {activeSection === 'zones' && (
             <div className="p-2">
                 <ZoneEditor />
             </div>
          )}
          
          {activeSection === 'config' && (
             <div className="p-2">
                 <ConfigEditor />
             </div>
          )}
          
          {activeSection === 'stats' && (
            <div className="grid grid-cols-3 gap-6">
              <div className="glass-card p-6">
                <p className="text-sm text-slate-400">Total Users</p>
                <p className="text-3xl font-bold text-white mt-2">{stats?.users.total || 0}</p>
                <p className="text-xs text-emerald-400 mt-1">
                  {stats?.users.new_this_month ? `+${stats.users.new_this_month} this month` : 'No new users'}
                </p>
              </div>
              <div className="glass-card p-6">
                <p className="text-sm text-slate-400">Active Tags</p>
                <p className="text-3xl font-bold text-white mt-2">{stats?.tags.total_active || 0}</p>
                <p className="text-xs text-slate-400 mt-1">
                  {stats ? `${stats.tags.infants} infants, ${stats.tags.mothers} mothers` : 'Loading...'}
                </p>
              </div>
              <div className="glass-card p-6">
                <p className="text-sm text-slate-400">Alerts Today</p>
                <p className="text-3xl font-bold text-white mt-2">{stats?.alerts.today || 0}</p>
                <p className="text-xs text-amber-400 mt-1">
                  {stats?.alerts.unacknowledged || 0} unacknowledged
                </p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ProtectedRoute allowedRoles={['admin', 'security', 'nurse', 'viewer']}>
      <DashboardLayout />
    </ProtectedRoute>
  );
}
