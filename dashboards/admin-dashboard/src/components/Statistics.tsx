import { DashboardStats } from '../types';

interface StatisticsProps {
  stats: DashboardStats | null;
}

export default function Statistics({ stats }: StatisticsProps) {
  return (
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
  );
}
