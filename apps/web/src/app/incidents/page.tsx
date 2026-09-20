'use client';

import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  ShieldAlert,
  Search,
  Zap,
  FileCode,
  Terminal,
  ArrowRight,
  GitBranch,
  Activity,
  Layers,
  Check,
  X,
  Info,
  Brain,
  Rocket,
  ShieldCheck,
} from 'lucide-react';

export default function IncidentsPage() {
  const [observations, setObservations] = useState<any[]>([]);
  const [selectedObs, setSelectedObs] = useState<any>(null);
  const [intelligenceReport, setIntelligenceReport] = useState<any>(null);

  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchObservations = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/observability/incidents?project_id=demo-project`);
      if (res.ok) {
        const data = await res.json();
        setObservations(data);
        if (data.length > 0 && !selectedObs) {
          handleSelectObservation(data[0]);
        }
      }
    } catch (e) {
      console.error('Failed to fetch observations:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectObservation = async (obs: any) => {
    setSelectedObs(obs);
    try {
      const res = await fetch(`${apiUrl}/api/v1/observability/incidents/${obs.id}`);
      if (res.ok) {
        const rep = await res.json();
        setIntelligenceReport(rep);
      }
    } catch (e) {
      console.error('Failed to fetch incident intelligence:', e);
    }
  };

  useEffect(() => {
    fetchObservations();
  }, []);

  const handleSimulateWebhook = async (scenario: string = 'NEW_CRITICAL') => {
    setIngesting(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/observability/webhooks/mock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario: scenario,
          service: 'apps/api',
          message: `Simulated ${scenario} Production Telemetry Signal`,
          commit_sha: 'a1b2c3d4e5f6',
          release: 'v1.4.2',
        }),
      });

      if (res.ok) {
        await fetchObservations();
      }
    } catch (e) {
      console.error('Failed to ingest webhook:', e);
    } finally {
      setIngesting(false);
    }
  };

  const handleInvestigate = async (obsId: string) => {
    setActionInProgress('INVESTIGATE');
    try {
      const res = await fetch(`${apiUrl}/api/v1/observability/incidents/${obsId}/investigate`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchObservations();
      }
    } catch (e) {
      console.error('Failed to initiate investigation:', e);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleAcknowledge = async (obsId: string) => {
    setActionInProgress('ACKNOWLEDGE');
    try {
      const res = await fetch(`${apiUrl}/api/v1/observability/incidents/${obsId}/acknowledge`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchObservations();
      }
    } catch (e) {
      console.error('Failed to acknowledge incident:', e);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleResolve = async (obsId: string) => {
    setActionInProgress('RESOLVE');
    try {
      const res = await fetch(`${apiUrl}/api/v1/observability/incidents/${obsId}/resolve`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchObservations();
      }
    } catch (e) {
      console.error('Failed to resolve incident:', e);
    } finally {
      setActionInProgress(null);
    }
  };

  const filteredObservations = observations.filter((o) => {
    if (selectedSeverity !== 'ALL' && o.severity !== selectedSeverity) return false;
    if (selectedStatus !== 'ALL' && o.status !== selectedStatus) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        o.message.toLowerCase().includes(q) ||
        o.service.toLowerCase().includes(q) ||
        o.fingerprint.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return (
          <span className="px-2 py-0.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded font-mono text-xs flex items-center space-x-1">
            <ShieldAlert className="w-3 h-3" />
            <span>CRITICAL</span>
          </span>
        );
      case 'ERROR':
        return (
          <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded font-mono text-xs flex items-center space-x-1">
            <AlertTriangle className="w-3 h-3" />
            <span>ERROR</span>
          </span>
        );
      case 'WARNING':
        return (
          <span className="px-2 py-0.5 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 rounded font-mono text-xs flex items-center space-x-1">
            <Info className="w-3 h-3" />
            <span>WARNING</span>
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded font-mono text-xs">
            {sev || 'INFO'}
          </span>
        );
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'OPEN':
        return (
          <span className="px-2 py-0.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded font-mono text-xs">
            OPEN
          </span>
        );
      case 'ACKNOWLEDGED':
        return (
          <span className="px-2 py-0.5 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 rounded font-mono text-xs">
            ACKNOWLEDGED
          </span>
        );
      case 'INVESTIGATING':
        return (
          <span className="px-2 py-0.5 bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded font-mono text-xs flex items-center space-x-1">
            <Activity className="w-3 h-3 animate-spin" />
            <span>INVESTIGATING</span>
          </span>
        );
      case 'RESOLVED':
        return (
          <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded font-mono text-xs flex items-center space-x-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>RESOLVED</span>
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 bg-slate-500/10 text-slate-400 border border-slate-500/20 rounded font-mono text-xs">
            {st}
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-[#1e2438] pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-3">
            <Activity className="w-7 h-7 text-rose-400" />
            <span>Production Incident Observability & Intelligence</span>
          </h1>
          <p className="text-sm text-slate-400 font-mono mt-1">
            Phase 11 production telemetry normalization, fingerprint deduplication, release correlation, and READ_ONLY safety boundary.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => handleSimulateWebhook('NEW_CRITICAL')}
            disabled={ingesting}
            className="px-3.5 py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 rounded-md text-xs font-mono flex items-center space-x-2 transition-all disabled:opacity-50"
          >
            <Zap className={`w-3.5 h-3.5 ${ingesting ? 'animate-spin' : ''}`} />
            <span>Ingest Telemetry Webhook</span>
          </button>
          <button
            onClick={fetchObservations}
            className="px-3 py-2 bg-[#121624] hover:bg-[#1a2035] text-slate-300 border border-[#1e2438] rounded-md text-xs font-mono transition-all"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Production Safety Boundary Alert */}
      <div className="bg-emerald-500/5 border border-emerald-500/20 p-4 rounded-lg flex items-center justify-between font-mono text-xs text-emerald-300">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>PRODUCTION READ_ONLY ENFORCEMENT ACTIVE — Direct production deployment, shell access, or DB mutations are strictly denied.</span>
        </div>
        <span className="bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 text-[11px]">
          BOUNDARY VERIFIED
        </span>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-[#121624] border border-[#1e2438] p-4 rounded-lg flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search observations by service, message, or fingerprint..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#0a0d14] border border-[#1e2438] text-slate-200 text-sm rounded-md pl-9 pr-4 py-2 focus:outline-none focus:border-rose-500 font-mono"
          />
        </div>

        <div className="flex items-center space-x-3 w-full md:w-auto font-mono text-xs">
          <div className="flex items-center space-x-1">
            <span className="text-slate-400">SEVERITY:</span>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="bg-[#0a0d14] border border-[#1e2438] text-slate-200 rounded-md px-3 py-2 focus:outline-none focus:border-rose-500"
            >
              <option value="ALL">ALL</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="ERROR">ERROR</option>
              <option value="WARNING">WARNING</option>
              <option value="INFO">INFO</option>
            </select>
          </div>

          <div className="flex items-center space-x-1">
            <span className="text-slate-400">STATUS:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-[#0a0d14] border border-[#1e2438] text-slate-200 rounded-md px-3 py-2 focus:outline-none focus:border-rose-500"
            >
              <option value="ALL">ALL</option>
              <option value="OPEN">OPEN</option>
              <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
              <option value="INVESTIGATING">INVESTIGATING</option>
              <option value="RESOLVED">RESOLVED</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Grid: Observations List & Incident Intelligence Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Observations List */}
        <div className="lg:col-span-1 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-300 font-mono flex items-center space-x-2">
              <Layers className="w-4 h-4 text-rose-400" />
              <span>PRODUCTION TELEMETRY ({filteredObservations.length})</span>
            </h2>
          </div>

          {loading ? (
            <div className="bg-[#121624] border border-[#1e2438] p-8 rounded-lg text-center text-slate-400 font-mono text-sm">
              Loading production observations...
            </div>
          ) : filteredObservations.length === 0 ? (
            <div className="bg-[#121624] border border-[#1e2438] p-8 rounded-lg text-center text-slate-400 font-mono text-sm">
              No matching production observations found. Click "Ingest Telemetry Webhook" to simulate telemetry.
            </div>
          ) : (
            <div className="space-y-3">
              {filteredObservations.map((o) => (
                <div
                  key={o.id}
                  onClick={() => handleSelectObservation(o)}
                  className={`bg-[#121624] border p-4 rounded-lg cursor-pointer transition-all hover:border-rose-500/50 ${
                    selectedObs?.id === o.id
                      ? 'border-rose-500 bg-[#161b2e]'
                      : 'border-[#1e2438]'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        {getSeverityBadge(o.severity)}
                        {getStatusBadge(o.status)}
                      </div>
                      <p className="text-sm font-bold text-white mt-1.5 line-clamp-1">{o.message}</p>
                    </div>
                  </div>

                  <div className="mt-3 pt-2 border-t border-[#1e2438] flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <span>SERVICE: <strong className="text-slate-200">{o.service}</strong></span>
                    <span className="bg-rose-500/10 text-rose-300 px-1.5 py-0.5 rounded">
                      {o.occurrence_count}x seen
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Incident Intelligence View & Report */}
        <div className="lg:col-span-2 space-y-6">
          {selectedObs ? (
            <div className="bg-[#121624] border border-[#1e2438] p-6 rounded-lg space-y-6">
              {/* Incident Header & Action Controls */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1e2438] pb-4">
                <div>
                  <div className="flex items-center space-x-3">
                    {getSeverityBadge(selectedObs.severity)}
                    {getStatusBadge(selectedObs.status)}
                    <span className="text-xs font-mono text-slate-400">ID: #{selectedObs.id.slice(0, 8)}</span>
                  </div>
                  <h2 className="text-lg font-bold text-white mt-1">{selectedObs.message}</h2>
                </div>

                <div className="flex items-center space-x-2 font-mono text-xs">
                  <button
                    onClick={() => handleInvestigate(selectedObs.id)}
                    disabled={actionInProgress !== null}
                    className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded font-bold transition-all flex items-center space-x-1"
                  >
                    <Zap className="w-3.5 h-3.5" />
                    <span>INVESTIGATE</span>
                  </button>

                  <button
                    onClick={() => handleAcknowledge(selectedObs.id)}
                    disabled={actionInProgress !== null}
                    className="px-3 py-1.5 bg-yellow-600/20 hover:bg-yellow-600/30 text-yellow-300 border border-yellow-500/30 rounded transition-all"
                  >
                    ACKNOWLEDGE
                  </button>

                  <button
                    onClick={() => handleResolve(selectedObs.id)}
                    disabled={actionInProgress !== null}
                    className="px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded transition-all"
                  >
                    RESOLVE
                  </button>
                </div>
              </div>

              {/* Verified Facts Section */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-emerald-400 font-mono flex items-center space-x-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>VERIFIED FACTS</span>
                </h3>
                <div className="bg-[#0a0d14] border border-[#1e2438] p-3 rounded text-xs font-mono text-slate-300 space-y-1">
                  {intelligenceReport?.verified_facts ? (
                    intelligenceReport.verified_facts.map((f: string, idx: number) => (
                      <div key={idx} className="flex items-center space-x-2">
                        <span className="text-emerald-400">•</span>
                        <span>{f}</span>
                      </div>
                    ))
                  ) : (
                    <div>• Environment: PRODUCTION (READ_ONLY)</div>
                  )}
                </div>
              </div>

              {/* Stack Trace Box */}
              {selectedObs.stack_trace && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-slate-400 font-mono flex items-center space-x-1.5">
                    <Terminal className="w-4 h-4 text-cyan-400" />
                    <span>STACK TRACE / LOCATION</span>
                  </h3>
                  <pre className="bg-[#0a0d14] border border-[#1e2438] p-3.5 rounded text-xs font-mono text-cyan-300 overflow-x-auto">
                    {selectedObs.stack_trace}
                  </pre>
                </div>
              )}

              {/* Correlations Section */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-blue-400 font-mono flex items-center space-x-1.5">
                  <GitBranch className="w-4 h-4" />
                  <span>RELEASE & PROJECT BRAIN CORRELATIONS</span>
                </h3>
                <div className="bg-[#0a0d14] border border-[#1e2438] p-3 rounded text-xs font-mono text-slate-300 space-y-1">
                  {intelligenceReport?.correlations ? (
                    intelligenceReport.correlations.map((c: string, idx: number) => (
                      <div key={idx} className="flex items-center space-x-2">
                        <span className="text-blue-400">•</span>
                        <span>{c}</span>
                      </div>
                    ))
                  ) : (
                    <div>• Matched monorepo apps/api service structure.</div>
                  )}
                </div>
              </div>

              {/* Hypotheses & Proposed Next Steps */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-purple-400 font-mono flex items-center space-x-1.5">
                    <Brain className="w-4 h-4" />
                    <span>ROOT CAUSE HYPOTHESES</span>
                  </h3>
                  <div className="bg-[#0a0d14] border border-[#1e2438] p-3 rounded text-xs font-mono text-slate-300 space-y-1">
                    {intelligenceReport?.hypotheses ? (
                      intelligenceReport.hypotheses.map((h: string, idx: number) => (
                        <div key={idx} className="flex items-start space-x-1.5">
                          <span className="text-purple-400 mt-0.5">•</span>
                          <span>{h}</span>
                        </div>
                      ))
                    ) : (
                      <div>• Potential unhandled exception in request handler.</div>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-indigo-400 font-mono flex items-center space-x-1.5">
                    <Rocket className="w-4 h-4" />
                    <span>PROPOSED NEXT STEPS</span>
                  </h3>
                  <div className="bg-[#0a0d14] border border-[#1e2438] p-3 rounded text-xs font-mono text-slate-300 space-y-1">
                    {intelligenceReport?.proposed_next_steps ? (
                      intelligenceReport.proposed_next_steps.slice(0, 4).map((s: string, idx: number) => (
                        <div key={idx} className="flex items-start space-x-1.5">
                          <span className="text-indigo-400 mt-0.5">•</span>
                          <span>{s}</span>
                        </div>
                      ))
                    ) : (
                      <div>• Initiate Phase 4 root-cause investigation handoff.</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-[#121624] border border-[#1e2438] p-12 rounded-lg text-center text-slate-500 font-mono text-sm">
              Select a production telemetry observation to view incident intelligence, stack trace, correlations, and investigation controls.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
