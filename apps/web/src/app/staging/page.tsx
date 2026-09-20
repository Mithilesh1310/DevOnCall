'use client';

import React, { useEffect, useState } from 'react';
import { Rocket, ShieldAlert, CheckCircle2, XCircle, AlertCircle, RefreshCw, Server, Play, ExternalLink, Activity } from 'lucide-react';

export default function StagingPage() {
  const [deployments, setDeployments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDeployment, setSelectedDeployment] = useState<any>(null);

  // Form state
  const [projectId, setProjectId] = useState('demo-project');
  const [branch, setBranch] = useState('devoncall/agent/fix-142');
  const [commitSha, setCommitSha] = useState('a1b2c3d4e5f6');
  const [scenario, setScenario] = useState('PASS');
  const [requireBrowser, setRequireBrowser] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchDeployments = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/staging/deployments`);
      if (res.ok) {
        const data = await res.json();
        setDeployments(data);
        if (data.length > 0 && !selectedDeployment) {
          setSelectedDeployment(data[0]);
        }
      }
    } catch (e) {
      console.error("Failed to fetch staging deployments:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployments();
  }, []);

  const handleCreateDeployment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commitSha || !branch) return;

    setSubmitting(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/staging/deployments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          workspace_id: `ws-${projectId}`,
          branch: branch,
          commit_sha: commitSha,
          environment: 'STAGING',
          use_mock: true,
          mock_scenario: scenario,
          require_browser: requireBrowser,
        }),
      });

      if (res.ok) {
        const created = await res.json();
        setSelectedDeployment(created);
        fetchDeployments();
      }
    } catch (e) {
      console.error("Failed to create staging deployment:", e);
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASSED':
        return <span className="px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded font-mono text-xs flex items-center space-x-1.5"><CheckCircle2 className="w-3.5 h-3.5" /><span>PASSED</span></span>;
      case 'FAILED':
        return <span className="px-2.5 py-1 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded font-mono text-xs flex items-center space-x-1.5"><XCircle className="w-3.5 h-3.5" /><span>FAILED</span></span>;
      case 'BLOCKED':
        return <span className="px-2.5 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded font-mono text-xs flex items-center space-x-1.5"><AlertCircle className="w-3.5 h-3.5" /><span>BLOCKED</span></span>;
      default:
        return <span className="px-2.5 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded font-mono text-xs flex items-center space-x-1.5"><Activity className="w-3.5 h-3.5 animate-spin" /><span>{status}</span></span>;
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-[#1e2438] pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-3">
            <Rocket className="w-6 h-6 text-blue-400" />
            <span>Staging Deployments & Verification Gate</span>
          </h1>
          <p className="text-sm text-slate-400 font-mono mt-1">
            Phase 9 isolated staging deployments, health checking, smoke probes, and Playwright verification.
          </p>
        </div>

        <button 
          onClick={fetchDeployments}
          className="px-3 py-1.5 bg-[#121624] border border-[#1e2438] hover:border-slate-600 rounded-lg text-slate-300 text-xs font-mono flex items-center space-x-2 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Staging</span>
        </button>
      </div>

      {/* Production Boundary Banner */}
      <div className="p-4 bg-emerald-950/20 border border-emerald-500/30 rounded-xl flex items-center justify-between text-xs font-mono">
        <div className="flex items-center space-x-3">
          <ShieldAlert className="w-5 h-5 text-emerald-400" />
          <div>
            <span className="font-bold text-white uppercase">Production Security Policy:</span>
            <span className="text-slate-300 ml-2">STAGING_DEPLOY Allowed | PRODUCTION = DENIED (Hard Enforcement)</span>
          </div>
        </div>
        <span className="px-2.5 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded">
          Isolated Staging Network
        </span>
      </div>

      {/* Deploy to Staging Form */}
      <div className="bg-[#121624] border border-[#1e2438] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider font-mono flex items-center space-x-2">
          <Play className="w-4 h-4 text-blue-400" />
          <span>Trigger Staging Deployment</span>
        </h2>

        <form onSubmit={handleCreateDeployment} className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          <input
            type="text"
            placeholder="Branch (e.g. devoncall/agent/fix-142)"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            className="sm:col-span-2 bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2"
          />
          <input
            type="text"
            placeholder="Commit SHA (e.g. a1b2c3d4e5f6)"
            value={commitSha}
            onChange={(e) => setCommitSha(e.target.value)}
            className="bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2"
          />
          <select
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2"
          >
            <option value="PASS">Scenario: PASS (Clean)</option>
            <option value="BUILD_FAIL">Scenario: BUILD_FAIL</option>
            <option value="DEPLOY_FAIL">Scenario: DEPLOY_FAIL</option>
            <option value="HEALTH_FAIL">Scenario: HEALTH_FAIL</option>
            <option value="SMOKE_FAIL">Scenario: SMOKE_FAIL</option>
            <option value="BROWSER_FAIL">Scenario: BROWSER_FAIL</option>
          </select>
          <button
            type="submit"
            disabled={submitting}
            className="bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs rounded-lg px-4 py-2 flex items-center justify-center space-x-2 transition-colors"
          >
            <Rocket className="w-3.5 h-3.5" />
            <span>{submitting ? 'Deploying...' : 'Deploy Staging'}</span>
          </button>
        </form>
      </div>

      {/* Deployments Table */}
      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider font-mono">
          Recent Staging Deployments
        </h2>

        <div className="bg-[#121624] border border-[#1e2438] rounded-xl overflow-hidden">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#0b0e17] text-slate-400 border-b border-[#1e2438]">
              <tr>
                <th className="py-3 px-4">Deployment ID</th>
                <th className="py-3 px-4">Branch</th>
                <th className="py-3 px-4">Commit SHA</th>
                <th className="py-3 px-4">Provider</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">URL</th>
                <th className="py-3 px-4">Duration</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2438] text-slate-300">
              {deployments.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500">
                    No staging deployments created yet. Trigger one above.
                  </td>
                </tr>
              ) : (
                deployments.map((d) => (
                  <tr
                    key={d.id}
                    onClick={() => setSelectedDeployment(d)}
                    className={`cursor-pointer transition-colors ${
                      selectedDeployment?.id === d.id ? 'bg-[#1a2238]' : 'hover:bg-[#151a29]'
                    }`}
                  >
                    <td className="py-3 px-4 font-bold text-white">{d.id}</td>
                    <td className="py-3 px-4 text-slate-300">{d.branch}</td>
                    <td className="py-3 px-4 text-blue-400 font-bold">{d.commit_sha?.slice(0, 8)}</td>
                    <td className="py-3 px-4 text-slate-400">{d.provider}</td>
                    <td className="py-3 px-4">{getStatusBadge(d.status)}</td>
                    <td className="py-3 px-4 text-slate-400">
                      {d.deployment_url ? (
                        <span className="text-emerald-400 flex items-center space-x-1">
                          <span>{d.deployment_url}</span>
                        </span>
                      ) : (
                        'N/A'
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-400">{d.duration_ms}ms</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Deployment Check Results */}
      {selectedDeployment && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider font-mono flex items-center space-x-2">
            <Server className="w-4 h-4 text-emerald-400" />
            <span>Verification Gate Results for {selectedDeployment.id}</span>
          </h2>

          <div className="bg-[#121624] border border-[#1e2438] rounded-xl p-5 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 font-mono text-xs">
              {selectedDeployment.checks.map((check: any) => (
                <div
                  key={check.id}
                  className="p-3 bg-[#0b0e17] border border-[#1e2438] rounded-lg space-y-2"
                >
                  <div className="flex items-center justify-between border-b border-[#1e2438] pb-1.5">
                    <span className="font-bold text-white">{check.check_type}</span>
                    <span
                      className={`px-2 py-0.5 text-[10px] rounded ${
                        check.status === 'PASS'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}
                    >
                      {check.status}
                    </span>
                  </div>
                  <p className="text-slate-300 text-[11px]">{check.summary}</p>
                  <span className="text-[10px] text-slate-500 block">Duration: {check.duration_ms}ms</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
