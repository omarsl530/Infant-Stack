export interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  trend?: { value: number; isUp: boolean };
}

export function StatCard({ title, value, icon: Icon, color, trend }: StatCardProps) {
  return (
    <div className="glass-card p-5 transition-transform hover:scale-[1.02]">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400 mb-1">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
          {trend && (
            <p className={`text-xs mt-1 ${trend.isUp ? 'text-emerald-400' : 'text-red-400'}`}>
              {trend.isUp ? '↑' : '↓'} {trend.value}% from yesterday
            </p>
          )}
        </div>
        <div className={`p-3 rounded-xl ${color}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}

export default StatCard;
