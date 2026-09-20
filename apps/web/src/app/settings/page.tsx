'use client';

import React, { useEffect, useState } from 'react';
import { Settings, Database, Server, MessageSquare, Shield, RefreshCw, UserPlus, Play, CheckCircle2, AlertCircle } from 'lucide-react';

export default function SettingsPage() {
  const [statusData, setStatusData] = useState<any>(null);
  const [whatsappStatus, setWhatsappStatus] = useState<any>(null);
  const [developers, setDevelopers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Registration state
  const [devName, setDevName] = useState('');
  const [devPhone, setDevPhone] = useState('');
  const [devRole, setDevRole] = useState('DEVELOPER');

  // Simulator state
  const [simPhone, setSimPhone] = useState('+14155552671');
  const [simCommand, setSimCommand] = useState('HELP');
  const [simResponse, setSimResponse] = useState<any>(null);
  const [simulating, setSimulating] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [sysRes, waStatusRes, waDevsRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/status`),
        fetch(`${apiUrl}/api/v1/whatsapp/status`),
        fetch(`${apiUrl}/api/v1/whatsapp/developers`),
      ]);

      if (sysRes.ok) setStatusData(await sysRes.json());
      if (waStatusRes.ok) setWhatsappStatus(await waStatusRes.json());
      if (waDevsRes.ok) setDevelopers(await waDevsRes.json());
    } catch (e) {
      console.error("Settings data fetch failed:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  const handleRegisterDeveloper = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!devName || !devPhone) return;

    try {
      const res = await fetch(`${apiUrl}/api/v1/whatsapp/developers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: devName,
          phone_number: devPhone,
          role: devRole,
          enabled: true,
        }),
      });
      if (res.ok) {
        setDevName('');
        setDevPhone('');
        fetchAllData();
      }
    } catch (e) {
      console.error("Developer registration failed:", e);
    }
  };

  const handleRunSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!simCommand) return;

    setSimulating(true);
    setSimResponse(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/whatsapp/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sender_phone: simPhone,
          raw_text: simCommand,
          use_mock: true,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSimResponse(data);
      }
    } catch (e) {
      console.error("Command simulation failed:", e);
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      <div className="flex items-center justify-between border-b border-[#1e2438] pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-3">
            <Settings className="w-6 h-6 text-slate-400" />
            <span>Settings & On-Call WhatsApp Interface</span>
          </h1>
          <p className="text-sm text-slate-400 font-mono mt-1">
            Configure system infrastructure, WhatsApp Cloud API webhooks, and authorized developers.
          </p>
        </div>

        <div className="flex items-center space-x-3 font-mono text-xs">
          <a
            href="/settings/integrations"
            className="px-3 py-1.5 bg-blue-600/10 text-blue-400 border border-blue-500/20 hover:bg-blue-600/20 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <Shield className="w-3.5 h-3.5" />
            <span>Audit Integrations</span>
          </a>
          <button 
            onClick={fetchAllData}
            className="px-3 py-1.5 bg-[#121624] border border-[#1e2438] hover:border-slate-600 rounded-lg text-slate-300 flex items-center space-x-2 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Status</span>
          </button>
        </div>
      </div>

      {/* Core Infrastructure & WhatsApp Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* PostgreSQL Card */}
        <div className="p-5 bg-[#121624] border border-[#1e2438] rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Database className="w-5 h-5 text-blue-400" />
              <span className="font-bold text-white text-sm">PostgreSQL</span>
            </div>
            <span className={`px-2 py-0.5 text-xs font-mono rounded ${
              statusData?.database?.connected 
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
            }`}>
              {statusData?.database?.connected ? 'Online' : 'Standby'}
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono">
            {statusData?.database?.details || 'Connecting to database...'}
          </p>
        </div>

        {/* Redis Cache */}
        <div className="p-5 bg-[#121624] border border-[#1e2438] rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Server className="w-5 h-5 text-purple-400" />
              <span className="font-bold text-white text-sm">Redis Cache</span>
            </div>
            <span className={`px-2 py-0.5 text-xs font-mono rounded ${
              statusData?.redis?.connected 
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
            }`}>
              {statusData?.redis?.connected ? 'Online' : 'Standby'}
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono">
            {statusData?.redis?.details || 'Connecting to redis...'}
          </p>
        </div>

        {/* WhatsApp Provider */}
        <div className="p-5 bg-[#121624] border border-[#1e2438] rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <MessageSquare className="w-5 h-5 text-emerald-400" />
              <span className="font-bold text-white text-sm">WhatsApp Runtime</span>
            </div>
            <span className="px-2 py-0.5 text-xs font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {whatsappStatus?.provider_type || 'MOCK_SIMULATION'}
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono">
            Webhook: <span className="text-slate-200">{whatsappStatus?.webhook_url || '/api/v1/webhooks/whatsapp'}</span>
          </p>
        </div>
      </div>

      {/* PHASE 8: WhatsApp Authorized Developers Management */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider font-mono flex items-center space-x-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            <span>Authorized On-Call Developers</span>
          </h2>
          <span className="text-xs font-mono text-slate-400">
            {developers.length} Developer(s) Registered
          </span>
        </div>

        <div className="bg-[#121624] border border-[#1e2438] rounded-xl overflow-hidden p-5 space-y-6">
          {/* Register Developer Form */}
          <form onSubmit={handleRegisterDeveloper} className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <input
              type="text"
              placeholder="Developer Name (e.g. Alice)"
              value={devName}
              onChange={(e) => setDevName(e.target.value)}
              className="bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
            />
            <input
              type="text"
              placeholder="Phone e.g. +14155552671"
              value={devPhone}
              onChange={(e) => setDevPhone(e.target.value)}
              className="bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
            />
            <select
              value={devRole}
              onChange={(e) => setDevRole(e.target.value)}
              className="bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
            >
              <option value="VIEWER">VIEWER (Read-only)</option>
              <option value="DEVELOPER">DEVELOPER (Investigate & Fix)</option>
              <option value="APPROVER">APPROVER (Approve PRs)</option>
              <option value="ADMIN">ADMIN (Full Access)</option>
            </select>
            <button
              type="submit"
              className="bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs rounded-lg px-4 py-2 flex items-center justify-center space-x-2 transition-colors"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>Authorize Developer</span>
            </button>
          </form>

          {/* Developers List Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#0b0e17] text-slate-400 border-b border-[#1e2438]">
                <tr>
                  <th className="py-2.5 px-3">Name</th>
                  <th className="py-2.5 px-3">Phone Number</th>
                  <th className="py-2.5 px-3">Identity Hash</th>
                  <th className="py-2.5 px-3">Role</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e2438] text-slate-300">
                {developers.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-4 text-center text-slate-500">
                      No authorized developers registered yet. Add one above.
                    </td>
                  </tr>
                ) : (
                  developers.map((dev) => (
                    <tr key={dev.id} className="hover:bg-[#181f33]">
                      <td className="py-2.5 px-3 font-semibold text-white">{dev.name}</td>
                      <td className="py-2.5 px-3">{dev.phone_number}</td>
                      <td className="py-2.5 px-3 text-slate-500 text-[10px] truncate max-w-[150px]">{dev.identity_hash}</td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded">
                          {dev.role}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        {dev.enabled ? (
                          <span className="text-emerald-400 flex items-center space-x-1">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Active</span>
                          </span>
                        ) : (
                          <span className="text-rose-400 flex items-center space-x-1">
                            <AlertCircle className="w-3 h-3" />
                            <span>Disabled</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* PHASE 8: Interactive WhatsApp Command Simulator */}
      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider font-mono flex items-center space-x-2">
          <MessageSquare className="w-4 h-4 text-blue-400" />
          <span>WhatsApp Command Simulator & Tester</span>
        </h2>

        <div className="bg-[#121624] border border-[#1e2438] rounded-xl p-5 space-y-4">
          <form onSubmit={handleRunSimulation} className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <input
              type="text"
              placeholder="Sender Phone"
              value={simPhone}
              onChange={(e) => setSimPhone(e.target.value)}
              className="bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2"
            />
            <input
              type="text"
              placeholder="Command (e.g. HELP, INCIDENTS, FIX 142)"
              value={simCommand}
              onChange={(e) => setSimCommand(e.target.value)}
              className="sm:col-span-2 bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2"
            />
            <button
              type="submit"
              disabled={simulating}
              className="bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs rounded-lg px-4 py-2 flex items-center justify-center space-x-2"
            >
              <Play className="w-3.5 h-3.5" />
              <span>{simulating ? 'Sending...' : 'Send Command'}</span>
            </button>
          </form>

          {/* Quick Command Chips */}
          <div className="flex flex-wrap gap-2 text-[11px] font-mono">
            <span className="text-slate-500 self-center">Quick commands:</span>
            {['HELP', 'INCIDENTS', 'INCIDENT 1', 'INVESTIGATE 1', 'FIX 1', 'WHOAMI'].map((cmd) => (
              <button
                key={cmd}
                type="button"
                onClick={() => setSimCommand(cmd)}
                className="px-2.5 py-1 bg-[#0b0e17] hover:bg-[#181f33] border border-[#1e2438] text-slate-300 rounded"
              >
                {cmd}
              </button>
            ))}
          </div>

          {/* Response Box */}
          {simResponse && (
            <div className="mt-4 p-4 bg-[#0b0e17] border border-[#1e2438] rounded-xl space-y-2 font-mono text-xs">
              <div className="flex items-center justify-between text-slate-400 text-[11px] border-b border-[#1e2438] pb-2">
                <span>
                  Authorized: <strong className={simResponse.is_authorized ? "text-emerald-400" : "text-rose-400"}>
                    {simResponse.is_authorized ? "YES" : "NO"}
                  </strong> | Command: <span className="text-blue-400">{simResponse.command_type}</span>
                </span>
                {simResponse.confirmation_token && (
                  <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded font-bold">
                    Token: {simResponse.confirmation_token}
                  </span>
                )}
              </div>
              <pre className="text-slate-200 whitespace-pre-wrap font-mono text-xs leading-relaxed pt-2">
                {simResponse.response_text}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
