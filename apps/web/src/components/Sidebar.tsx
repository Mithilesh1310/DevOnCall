'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Terminal, 
  LayoutDashboard, 
  AlertTriangle, 
  FolderGit2, 
  Settings, 
  Rocket, 
  ShieldCheck 
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Incidents', href: '/incidents', icon: AlertTriangle },
  { name: 'Projects', href: '/projects', icon: FolderGit2 },
  { name: 'Staging', href: '/staging', icon: Rocket },
  { name: 'Releases', href: '/releases', icon: ShieldCheck },
  { name: 'Settings', href: '/settings', icon: Settings },
];


export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-[#1e2438] bg-[#0d101a] flex flex-col justify-between h-screen sticky top-0">
      <div>
        {/* Brand Header */}
        <div className="p-5 border-b border-[#1e2438] flex items-center space-x-3">
          <div className="p-2 bg-blue-600/20 border border-blue-500/30 rounded-lg text-blue-400">
            <Terminal className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-white tracking-wide">DevOnCall</h1>
            <p className="text-xs text-slate-400 font-mono">AI Production Engineer</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#151a29]'
                }`}
              >
                <Icon className={`w-4 h-4 mr-3 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-[#1e2438] bg-[#090b12]">
        <div className="flex items-center space-x-2 text-xs text-slate-400 mb-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Phase 0 Foundation</span>
        </div>
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
          <span>v0.1.0-local</span>
          <span className="flex items-center">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block mr-1.5 animate-pulse"></span>
            Ready
          </span>
        </div>
      </div>
    </aside>
  );
}
