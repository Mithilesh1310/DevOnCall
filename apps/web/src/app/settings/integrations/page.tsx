'use client';

import React, { useEffect, useState } from 'react';
import { ShieldCheck, Database, Server, Cpu, Globe, MessageSquare, Rocket, AlertTriangle, RefreshCw, Lock, CheckCircle2, XCircle, AlertCircle, Play } from 'lucide-react';

interface IntegrationInfo {
  name: string;
  provider: string;
  status: string;
  health: string;
  required_environment: string[];
  details?: Record<string, any>;
  last_verified_at?: string;
}

interface SystemIntegrationsData {
  system_mode: string;
  total_integrations: number;
  summary: {
    REAL: number;
    NOT_CONFIGURED: number;
    BLOCKED: number;
    ERROR: number;
  };
  integrations: IntegrationInfo[];
  evaluated_at: string;
}

export default function IntegrationsDashboardPage() {
  const [systemData, setSystemData] = useState<SystemIntegrationsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [testingName, setTestingName] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchIntegrations = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/system/integrations`);
      if (res.ok) {
        const data = await res.json();
        setSystemData(data);
      }
    } catch (e) {
      console.error("Failed to fetch system integrations:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const handleTestIntegration = async (name: string) => {
    setTestingName(name);
    try {
      const res = await fetch(`${apiUrl}/api/v1/system/integrations/${name}/test`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchIntegrations();
      }
    } catch (e) {
      console.error(`Failed to test integration ${name}:`, e);
    } finally {
      setTestingName(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'REAL':
        return (
          <span className="px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded font-mono text-xs flex items-center space-x-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>REAL</span>
          </span>
        );
      case 'NOT_CONFIGURED':
        return (
          <span className="px-2.5 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded font-mono text-xs flex items-center space-x-1.5">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>NOT_CONFIGURED</span>
          </span>
        );
      case 'BLOCKED':
      case 'ERROR':
        return (
          <span className="px-2.5 py-1 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded font-mono text-xs flex items-center space-x-1.5">
            <XCircle className="w-3.5 h-3.5" />
            <span>{status}</span>
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded font-mono text-xs">
            {status}
          </span>
        );
    }
  };

  const getIconForName = (name: string) => {
    switch (name) {
      case 'GITHUB':
        return <Globe className="w-5 h-5 text-blue-400" />;
      case 'POSTGRESQL':
        return <Database className="w-5 h-5 text-emerald-400" />;
      case 'REDIS':
        return <Server className="w-5 h-5 text-purple-400" />;
      case 'DOCKER':
        return <Cpu className="w-5 h-5 text-sky-400" />;
      case 'PLAYWRIGHT':
        return <Globe className="w-5 h-5 text-amber-400" />;
      case 'SENTRY':
        return <AlertTriangle className="w-5 h-5 text-rose-400" />;
      case 'WHATSAPP':
        return <MessageSquare className="w-5 h-5 text-emerald-400" />;
      case 'STAGING_DEPLOYMENT':
        return <Rocket className="w-5 h-5 text-indigo-400" />;
      case 'OBSERVABILITY':
        return <AlertTriangle className="w-5 h-5 text-cyan-400" />;
      case 'PRODUCTION_DEPLOYMENT':
        return <Lock className="w-5 h-5 text-amber-500" />;
      default:
        return <ShieldCheck className="w-5 h-5 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1e2438] pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-3">
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
            <span>Real Infrastructure Integrations Status</span>
          </h1>
          <p className="text-sm text-slate-400 font-mono mt-1">
            DevOnCall V1 end-to-end infrastructure audit across all 10 core integrations.
          </p>
        </div>

        <div className="flex items-center space-x-3 font-mono text-xs">
          <span className="px-3 py-1 bg-[#121624] border border-[#1e2438] rounded-lg text-slate-300">
            System Mode: <strong className="text-emerald-400">{systemData?.system_mode || 'REAL'}</strong>
          </span>

          <button
            onClick={fetchIntegrations}
            className="px-3 py-1.5 bg-[#121624] border border-[#1e2438] hover:border-slate-600 rounded-lg text-slate-300 flex items-center space-x-2 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Audit Integrations</span>
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-xs">
        <div className="p-4 bg-[#121624] border border-emerald-500/20 rounded-xl space-y-1">
          <span className="text-slate-400">REAL Connected:</span>
          <div className="text-xl font-bold text-emerald-400">{systemData?.summary?.REAL || 0}</div>
        </div>
        <div className="p-4 bg-[#121624] border border-amber-500/20 rounded-xl space-y-1">
          <span className="text-slate-400">NOT_CONFIGURED:</span>
          <div className="text-xl font-bold text-amber-400">{systemData?.summary?.NOT_CONFIGURED || 0}</div>
        </div>
        <div className="p-4 bg-[#121624] border border-rose-500/20 rounded-xl space-y-1">
          <span className="text-slate-400">BLOCKED:</span>
          <div className="text-xl font-bold text-rose-400">{systemData?.summary?.BLOCKED || 0}</div>
        </div>
        <div className="p-4 bg-[#121624] border border-rose-500/20 rounded-xl space-y-1">
          <span className="text-slate-400">ERROR:</span>
          <div className="text-xl font-bold text-rose-400">{systemData?.summary?.ERROR || 0}</div>
        </div>
      </div>

      {/* Integrations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {systemData?.integrations.map((item) => (
          <div
            key={item.name}
            className="bg-[#121624] border border-[#1e2438] rounded-xl p-5 space-y-3 font-mono text-xs flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-[#1e2438] pb-3">
                <div className="flex items-center space-x-3">
                  {getIconForName(item.name)}
                  <div>
                    <h3 className="font-bold text-white text-sm">{item.name}</h3>
                    <span className="text-[11px] text-slate-400">{item.provider}</span>
                  </div>
                </div>
                {getStatusBadge(item.status)}
              </div>

              <p className="text-slate-300 text-xs bg-[#0b0e17] p-3 border border-[#1e2438] rounded-lg">
                {item.health}
              </p>

              <div className="space-y-1.5 text-[11px]">
                <span className="text-slate-500 block">Required Environment Variables:</span>
                <div className="flex flex-wrap gap-1.5">
                  {item.required_environment.map((env) => (
                    <span key={env} className="px-2 py-0.5 bg-[#0b0e17] border border-[#1e2438] text-slate-400 rounded">
                      {env}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-[#1e2438] flex items-center justify-between">
              <span className="text-[10px] text-slate-500">
                Verified: {item.last_verified_at ? new Date(item.last_verified_at).toLocaleTimeString() : 'N/A'}
              </span>
              <button
                onClick={() => handleTestIntegration(item.name)}
                disabled={testingName === item.name}
                className="px-3 py-1.5 bg-[#0b0e17] hover:bg-[#181f33] border border-[#1e2438] text-blue-400 rounded-lg flex items-center space-x-1.5 transition-colors"
              >
                <Play className={`w-3 h-3 ${testingName === item.name ? 'animate-spin' : ''}`} />
                <span>{testingName === item.name ? 'Testing...' : 'Test Connection'}</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
