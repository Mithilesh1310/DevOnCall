'use client';

import React, { useEffect, useState } from 'react';
import { StatusCard } from '@/components/StatusCard';
import { 
  AlertTriangle, 
  FolderGit2, 
  Search, 
  Bot, 
  CheckCircle2, 
  Clock, 
  Terminal,
  Activity,
  ArrowUpRight
} from 'lucide-react';

export default function DashboardPage() {
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await fetch(`${apiUrl}/api/v1/status`);
        if (res.ok) {
          const data = await res.json();
          setSystemStatus(data);
        }
      } catch (err) {
        console.error("Status fetch failed:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchStatus();
  }, [apiUrl]);

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Title section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1e2438] pb-6">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h1 className="text-2xl font-bold text-white tracking-tight">DevOnCall</h1>
            <span className="px-2.5 py-0.5 text-xs font-mono rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Phase 0
            </span>
          </div>
          <p className="text-sm text-slate-400 font-mono">
            AI Production Software Engineer — Foundation Layer
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="px-3 py-1.5 rounded-lg bg-[#121624] border border-[#1e2438] text-xs font-mono text-slate-300 flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Agent Engine: Standby</span>
          </div>
        </div>
      </div>

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatusCard
          title="ACTIVE INCIDENTS"
          value="0"
          subtitle="No open production incidents"
          icon={AlertTriangle}
          badge="Healthy"
          badgeColor="emerald"
        />
        <StatusCard
          title="CONNECTED PROJECTS"
          value="1"
          subtitle="Monorepo sample workspace"
          icon={FolderGit2}
          badge="Active"
          badgeColor="blue"
        />
        <StatusCard
          title="RECENT INVESTIGATIONS"
          value="0"
          subtitle="Pending incident reports"
          icon={Search}
          badge="Idle"
          badgeColor="amber"
        />
        <StatusCard
          title="AGENT STATUS"
          value={loading ? "..." : (systemStatus?.status === 'ok' ? "Ready" : "Standby")}
          subtitle="Docker & Redis pipeline connected"
          icon={Bot}
          badge={systemStatus?.status === 'ok' ? "Online" : "Initializing"}
          badgeColor={systemStatus?.status === 'ok' ? "emerald" : "amber"}
        />
      </div>

      {/* Main Grid: Incident Feed & System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Recent Investigations Placeholder */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-200 flex items-center space-x-2">
              <Activity className="w-4 h-4 text-blue-400" />
              <span>Recent Incident Investigations</span>
            </h2>
            <span className="text-xs font-mono text-slate-500">Live Telemetry Feed</span>
          </div>

          <div className="bg-[#121624] border border-[#1e2438] rounded-xl p-8 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-[#1a2032] text-slate-400 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6 text-emerald-400" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200">System Operating Normally</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              DevOnCall Phase 0 foundation is active. Trigger an incident report or connect Sentry webhooks in Phase 1 to begin automated root-cause investigations.
            </p>
          </div>
        </div>

        {/* Right Column: Infrastructure Readiness Box */}
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-slate-200 flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-purple-400" />
            <span>Infrastructure Status</span>
          </h2>

          <div className="bg-[#121624] border border-[#1e2438] rounded-xl p-5 space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e2438]">
              <span className="text-slate-400">API Service</span>
              <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                {systemStatus?.service || 'devoncall-api'}
              </span>
            </div>

            <div className="flex items-center justify-between pb-3 border-b border-[#1e2438]">
              <span className="text-slate-400">PostgreSQL</span>
              <span className={systemStatus?.database?.connected ? "text-emerald-400" : "text-amber-400"}>
                {systemStatus?.database?.connected ? "Connected" : "Standby / Docker"}
              </span>
            </div>

            <div className="flex items-center justify-between pb-3 border-b border-[#1e2438]">
              <span className="text-slate-400">Redis Cache</span>
              <span className={systemStatus?.redis?.connected ? "text-emerald-400" : "text-amber-400"}>
                {systemStatus?.redis?.connected ? "Connected" : "Standby / Docker"}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Docker Sandbox</span>
              <span className="text-blue-400">Phase 1 Prepared</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
