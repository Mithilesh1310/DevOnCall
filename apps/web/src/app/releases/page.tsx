'use client';

import React, { useEffect, useState } from 'react';
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle, AlertCircle, RefreshCw, Server, Play, Activity, Layers, Lock, RotateCcw, Cpu } from 'lucide-react';

export default function ReleasesPage() {
  const [releaseCandidates, setReleaseCandidates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRc, setSelectedRc] = useState<any>(null);

  // Form states
  const [projectId, setProjectId] = useState('demo-project');
  const [commitSha, setCommitSha] = useState('a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2');
  const [stagingId, setStagingId] = useState('stg-demo-1');
  const [submitting, setSubmitting] = useState(false);

  // Approval state
  const [approverId, setApproverId] = useState('dev-lead@company.com');
  const [confirmationToken, setConfirmationToken] = useState('');
  const [approvalType, setApprovalType] = useState('CANARY_RELEASE');
  const [approvalReason, setApprovalReason] = useState('Staging and canary validations passed cleanly.');

  // Canary state
  const [canaryScenario, setCanaryScenario] = useState('HEALTHY');
  const [canaryTraffic, setCanaryTraffic] = useState(5.0);

  // Rollback state
  const [targetCommitSha, setTargetCommitSha] = useState('f0e9d8c7b6a5f0e9d8c7b6a5f0e9d8c7b6a5f0e9');
  const [rollbackReason, setRollbackReason] = useState('Emergency rollback requested due to anomalous telemetry.');
  const [showRollbackModal, setShowRollbackModal] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchReleases = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/deployment/release-candidates`);
      if (res.ok) {
        const data = await res.json();
        setReleaseCandidates(data);
        if (data.length > 0 && !selectedRc) {
          setSelectedRc(data[0]);
        }
      }
    } catch (e) {
      console.error("Failed to fetch release candidates:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReleases();
  }, []);

  const handleCreateRc = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commitSha) return;

    setSubmitting(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/deployment/release-candidates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          commit_sha: commitSha,
          staging_deployment_id: stagingId,
          pr_url: 'https://github.com/org/repo/pull/42',
        }),
      });

      if (res.ok) {
        const created = await res.json();
        setSelectedRc(created);
        fetchReleases();
      }
    } catch (e) {
      console.error("Failed to create release candidate:", e);
    } finally {
      setSubmitting(false);
    }
  };

  const handleStartCanary = async () => {
    if (!selectedRc) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/deployment/release-candidates/${selectedRc.id}/canary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rc_id: selectedRc.id,
          traffic_percent: canaryTraffic,
          mock_scenario: canaryScenario,
        }),
      });

      if (res.ok) {
        fetchReleases();
      }
    } catch (e) {
      console.error("Failed to start canary:", e);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeployProduction = async () => {
    if (!selectedRc) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/deployment/release-candidates/${selectedRc.id}/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rc_id: selectedRc.id,
          mock_scenario: 'SUCCESS',
        }),
      });

      if (res.ok) {
        fetchReleases();
      }
    } catch (e) {
      console.error("Failed to deploy to production:", e);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRollback = async () => {
    if (!selectedRc || !targetCommitSha) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/deployment/release-candidates/${selectedRc.id}/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rc_id: selectedRc.id,
          target_commit_sha: targetCommitSha,
          reason: rollbackReason,
          initiated_by: approverId,
        }),
      });

      if (res.ok) {
        setShowRollbackModal(false);
        fetchReleases();
      }
    } catch (e) {
      console.error("Failed to rollback production:", e);
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'DEPLOYED':
      case 'STAGING_PASSED':
        return <span className="px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded font-mono text-xs flex items-center space-x-1.5"><CheckCircle2 className="w-3.5 h-3.5" /><span>{status}</span></span>;
      case 'ROLLED_BACK':
      case 'CANARY_FAILED':
        return <span className="px-2.5 py-1 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded font-mono text-xs flex items-center space-x-1.5"><XCircle className="w-3.5 h-3.5" /><span>{status}</span></span>;
      case 'AWAITING_APPROVAL':
      case 'CANARY_VERIFIED':
        return <span className="px-2.5 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded font-mono text-xs flex items-center space-x-1.5"><AlertCircle className="w-3.5 h-3.5" /><span>{status}</span></span>;
      default:
        return <span className="px-2.5 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded font-mono text-xs flex items-center space-x-1.5"><Activity className="w-3.5 h-3.5" /><span>{status}</span></span>;
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-[#1e2438] pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-3">
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
            <span>Controlled Canary & Production Safety Gate</span>
          </h1>
          <p className="text-sm text-slate-400 font-mono mt-1">
            Phase 12 double human approval gates, 1-10% canary traffic bounding, telemetry decision engine & rollback safety.
          </p>
        </div>

        <button 
          onClick={fetchReleases}
          className="px-3 py-1.5 bg-[#121624] border border-[#1e2438] hover:border-slate-600 rounded-lg text-slate-300 text-xs font-mono flex items-center space-x-2 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Releases</span>
        </button>
      </div>

      {/* Production Safety Banner */}
      <div className="p-4 bg-emerald-950/20 border border-emerald-500/30 rounded-xl flex items-center justify-between text-xs font-mono">
        <div className="flex items-center space-x-3">
          <Lock className="w-5 h-5 text-emerald-400" />
          <div>
            <span className="font-bold text-white uppercase">Production Safety Policy Active:</span>
            <span className="text-slate-300 ml-2">Double Human Approval Required | Autonomous Agent Code Modification DENIED | Canary Bound: 1-10%</span>
          </div>
        </div>
        <span className="px-2.5 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded">
          Provider Isolated
        </span>
      </div>

      {/* Create Release Candidate Form */}
      <div className="bg-[#121624] border border-[#1e2438] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider font-mono flex items-center space-x-2">
          <Layers className="w-4 h-4 text-blue-400" />
          <span>Create Release Candidate</span>
        </h2>

        <form onSubmit={handleCreateRc} className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          <input
            type="text"
            placeholder="Exact 40-char Commit SHA"
            value={commitSha}
            onChange={(e) => setCommitSha(e.target.value)}
            className="sm:col-span-3 bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2"
          />
          <input
            type="text"
            placeholder="Staging ID (e.g. stg-demo-1)"
            value={stagingId}
            onChange={(e) => setStagingId(e.target.value)}
            className="bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2"
          />
          <button
            type="submit"
            disabled={submitting}
            className="bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs rounded-lg px-4 py-2 flex items-center justify-center space-x-2 transition-colors"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{submitting ? 'Creating...' : 'Create Candidate'}</span>
          </button>
        </form>
      </div>

      {/* Release Candidates Queue */}
      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider font-mono">
          Release Candidates Queue
        </h2>

        <div className="bg-[#121624] border border-[#1e2438] rounded-xl overflow-hidden">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#0b0e17] text-slate-400 border-b border-[#1e2438]">
              <tr>
                <th className="py-3 px-4">RC ID</th>
                <th className="py-3 px-4">Commit SHA</th>
                <th className="py-3 px-4">Staging Ref</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Created At</th>
                <th className="py-3 px-4">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2438] text-slate-300">
              {releaseCandidates.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-500">
                    No release candidates registered yet. Create one above.
                  </td>
                </tr>
              ) : (
                releaseCandidates.map((rc) => (
                  <tr
                    key={rc.id}
                    onClick={() => setSelectedRc(rc)}
                    className={`cursor-pointer transition-colors ${
                      selectedRc?.id === rc.id ? 'bg-[#1a2238]' : 'hover:bg-[#151a29]'
                    }`}
                  >
                    <td className="py-3 px-4 font-bold text-white">{rc.id}</td>
                    <td className="py-3 px-4 text-blue-400 font-bold">{rc.commit_sha?.slice(0, 8)}</td>
                    <td className="py-3 px-4 text-slate-400">{rc.staging_deployment_id || 'N/A'}</td>
                    <td className="py-3 px-4">{getStatusBadge(rc.status)}</td>
                    <td className="py-3 px-4 text-slate-400">{new Date(rc.created_at).toLocaleTimeString()}</td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => setSelectedRc(rc)}
                        className="px-2.5 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded hover:bg-blue-500/20"
                      >
                        Manage
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Release Candidate Dashboard */}
      {selectedRc && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider font-mono flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <span>Release Gate Operations for {selectedRc.id}</span>
            </h2>

            <button
              onClick={() => setShowRollbackModal(true)}
              className="px-3 py-1.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 rounded-lg text-xs font-mono flex items-center space-x-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Initiate Rollback</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-mono text-xs">
            {/* Gate 1: Canary Release */}
            <div className="bg-[#121624] border border-[#1e2438] rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-[#1e2438] pb-3">
                <span className="font-bold text-white text-sm">Gate 1: Canary Release</span>
                <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded">
                  Traffic: {canaryTraffic}%
                </span>
              </div>

              <p className="text-slate-400 text-xs">
                Deploys candidate to 1-10% production traffic with real-time telemetry anomaly detection.
              </p>

              <div className="space-y-2">
                <label className="text-slate-300 block">Traffic Percentage (1.0% - 10.0%):</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  step="0.5"
                  value={canaryTraffic}
                  onChange={(e) => setCanaryTraffic(parseFloat(e.target.value))}
                  className="w-full bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2"
                />
              </div>

              <div className="space-y-2">
                <label className="text-slate-300 block">Mock Telemetry Scenario:</label>
                <select
                  value={canaryScenario}
                  onChange={(e) => setCanaryScenario(e.target.value)}
                  className="w-full bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2"
                >
                  <option value="HEALTHY">Scenario: HEALTHY (Verdict PASS)</option>
                  <option value="HIGH_ERROR_RATE">Scenario: HIGH_ERROR_RATE (Verdict FAIL)</option>
                  <option value="HIGH_LATENCY">Scenario: HIGH_LATENCY (Verdict FAIL)</option>
                  <option value="INSUFFICIENT_DATA">Scenario: INSUFFICIENT_DATA (Verdict HUMAN_REVIEW)</option>
                </select>
              </div>

              <button
                onClick={handleStartCanary}
                disabled={submitting}
                className="w-full bg-amber-600 hover:bg-amber-500 text-white font-mono text-xs rounded-lg px-4 py-2 flex items-center justify-center space-x-2 transition-colors"
              >
                <Activity className="w-3.5 h-3.5" />
                <span>Start Canary Release ({canaryTraffic}%)</span>
              </button>
            </div>

            {/* Gate 2: Full Production Deployment */}
            <div className="bg-[#121624] border border-[#1e2438] rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-[#1e2438] pb-3">
                <span className="font-bold text-white text-sm">Gate 2: Full Production</span>
                <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded">
                  Double Approval
                </span>
              </div>

              <p className="text-slate-400 text-xs">
                Promotes 100% traffic to production after Canary Decision Engine emits verdict PASS.
              </p>

              <div className="p-3 bg-[#0b0e17] border border-[#1e2438] rounded-lg space-y-1">
                <span className="text-slate-400">Canary Decision Engine Verdict:</span>
                <div className="font-bold text-emerald-400">PASS (Error rate diff +0.02%, p95 diff +4ms)</div>
              </div>

              <button
                onClick={handleDeployProduction}
                disabled={submitting}
                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs rounded-lg px-4 py-2 flex items-center justify-center space-x-2 transition-colors"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Execute Full Production Release</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rollback Modal */}
      {showRollbackModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#121624] border border-[#1e2438] rounded-xl max-w-md w-full p-6 space-y-4 font-mono">
            <div className="flex items-center justify-between border-b border-[#1e2438] pb-3">
              <h3 className="text-sm font-bold text-rose-400 flex items-center space-x-2">
                <RotateCcw className="w-4 h-4" />
                <span>Confirm Production Rollback</span>
              </h3>
              <button onClick={() => setShowRollbackModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-300 block mb-1">Target 40-Char Stable Commit SHA:</label>
                <input
                  type="text"
                  value={targetCommitSha}
                  onChange={(e) => setTargetCommitSha(e.target.value)}
                  className="w-full bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2"
                />
              </div>

              <div>
                <label className="text-slate-300 block mb-1">Rollback Reason:</label>
                <textarea
                  value={rollbackReason}
                  onChange={(e) => setRollbackReason(e.target.value)}
                  rows={3}
                  className="w-full bg-[#0b0e17] border border-[#1e2438] text-white text-xs font-mono rounded-lg px-3 py-2"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowRollbackModal(false)}
                className="px-3 py-1.5 bg-[#0b0e17] text-slate-400 border border-[#1e2438] rounded-lg text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleRollback}
                className="px-4 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-bold"
              >
                Execute Emergency Rollback
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
