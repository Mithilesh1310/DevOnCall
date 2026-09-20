import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatusCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: LucideIcon;
  badge?: string;
  badgeColor?: 'emerald' | 'amber' | 'blue' | 'rose';
}

export function StatusCard({ title, value, subtitle, icon: Icon, badge, badgeColor = 'blue' }: StatusCardProps) {
  const badgeClasses = {
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    rose: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
  };

  return (
    <div className="p-5 bg-[#121624] border border-[#1e2438] rounded-xl relative overflow-hidden group hover:border-slate-700 transition-all">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-slate-400 font-mono tracking-wide">{title}</span>
        <div className="p-2 bg-[#1a2032] rounded-lg text-slate-300">
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <div className="flex items-baseline justify-between">
        <div className="text-2xl font-bold text-white tracking-tight font-mono">{value}</div>
        {badge && (
          <span className={`px-2 py-0.5 text-[11px] font-mono rounded-md border ${badgeClasses[badgeColor]}`}>
            {badge}
          </span>
        )}
      </div>
      <p className="text-xs text-slate-500 mt-2">{subtitle}</p>
    </div>
  );
}
