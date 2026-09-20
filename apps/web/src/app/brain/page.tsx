'use client';

import React, { useEffect, useState } from 'react';
import {
  Brain,
  Database,
  Network,
  CheckCircle2,
  ShieldCheck,
  Layers,
  Search,
  RefreshCw,
  FileCode,
  Terminal,
  History,
  Sparkles,
  AlertTriangle,
  Info,
  GitBranch,
  Server,
  Activity,
} from 'lucide-react';

export default function BrainPage() {
  const [projectId, setProjectId] = useState('demo-project');
  const [summary, setSummary] = useState<any>(null);
  const [nodes, setNodes] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [selectedNode, setSelectedNode] = useState<any>(null);

  const [loading, setLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('ALL');

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchData = async () => {
    setLoading(true);
    try {
      // 1. Fetch Summary
      const summaryRes = await fetch(`${apiUrl}/api/v1/brain/summary?project_id=${projectId}`);
      if (summaryRes.ok) {
        const sumData = await summaryRes.json();
        setSummary(sumData);
      }

      // 2. Fetch Nodes (or Query)
      const nodesRes = await fetch(`${apiUrl}/api/v1/brain/query?project_id=${projectId}&query=${encodeURIComponent(searchQuery)}`);
      if (nodesRes.ok) {
        const nodesData = await nodesRes.json();
        setNodes(nodesData.nodes || []);
      }

      // 3. Fetch Event Ledger
      const eventsRes = await fetch(`${apiUrl}/api/v1/brain/history?project_id=${projectId}&limit=10`);
      if (eventsRes.ok) {
        const eventsData = await eventsRes.json();
        setEvents(eventsData || []);
      }
    } catch (e) {
      console.error('Failed to fetch Brain data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData();
  };

  const handleRebuild = async () => {
    setRebuilding(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/brain/projects/${projectId}/rebuild`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchData();
      }
    } catch (e) {
      console.error('Failed to rebuild Brain:', e);
    } finally {
      setRebuilding(false);
    }
  };

  const filteredNodes = nodes.filter((n) => {
    if (selectedType === 'ALL') return true;
    return n.node_type === selectedType;
  });

  const getConfidenceBadge = (confidence: string) => {
    switch (confidence) {
      case 'VERIFIED':
        return (
          <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded font-mono text-xs flex items-center space-x-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>VERIFIED</span>
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded font-mono text-xs flex items-center space-x-1">
            <ShieldCheck className="w-3 h-3" />
            <span>HIGH</span>
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded font-mono text-xs flex items-center space-x-1">
            <Info className="w-3 h-3" />
            <span>MEDIUM</span>
          </span>
        );
      case 'LOW':
        return (
          <span className="px-2 py-0.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded font-mono text-xs flex items-center space-x-1">
            <AlertTriangle className="w-3 h-3" />
            <span>LOW</span>
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 bg-slate-500/10 text-slate-400 border border-slate-500/20 rounded font-mono text-xs">
            {confidence || 'UNKNOWN'}
          </span>
        );
    }
  };

  const getNodeTypeBadge = (nodeType: string) => {
    const colors: Record<string, string> = {
      SERVICE: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
      FILE: 'bg-slate-500/10 text-slate-300 border-slate-500/20',
      DATABASE: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
      INCIDENT: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
      DEPLOYMENT: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
      DECISION: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    };

    const cls = colors[nodeType] || 'bg-blue-500/10 text-blue-400 border-blue-500/20';

    return (
      <span className={`px-2 py-0.5 rounded font-mono text-xs border ${cls}`}>
        {nodeType}
      </span>
    );
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-[#1e2438] pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-3">
            <Brain className="w-7 h-7 text-purple-400" />
            <span>Project Brain — Living Engineering Memory</span>
          </h1>
          <p className="text-sm text-slate-400 font-mono mt-1">
            Persistent knowledge layer tracking monorepo architecture, services, incidents, fixes, and provenance.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleRebuild}
            disabled={rebuilding}
            className="px-3.5 py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 rounded-md text-xs font-mono flex items-center space-x-2 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${rebuilding ? 'animate-spin' : ''}`} />
            <span>{rebuilding ? 'Scanning Repo...' : 'Rebuild Brain'}</span>
          </button>
          <button
            onClick={fetchData}
            className="px-3 py-2 bg-[#121624] hover:bg-[#1a2035] text-slate-300 border border-[#1e2438] rounded-md text-xs font-mono transition-all"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <div className="bg-[#121624] border border-[#1e2438] p-4 rounded-lg">
          <div className="text-xs text-slate-400 font-mono flex items-center justify-between">
            <span>TOTAL NODES</span>
            <Layers className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1 font-mono">
            {summary?.total_nodes ?? 0}
          </div>
        </div>

        <div className="bg-[#121624] border border-[#1e2438] p-4 rounded-lg">
          <div className="text-xs text-slate-400 font-mono flex items-center justify-between">
            <span>RELATIONSHIPS</span>
            <Network className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1 font-mono">
            {summary?.total_edges ?? 0}
          </div>
        </div>

        <div className="bg-[#121624] border border-[#1e2438] p-4 rounded-lg">
          <div className="text-xs text-slate-400 font-mono flex items-center justify-between">
            <span>VERIFIED FACTS</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">
            {summary?.verified_facts_count ?? 0}
          </div>
        </div>

        <div className="bg-[#121624] border border-[#1e2438] p-4 rounded-lg">
          <div className="text-xs text-slate-400 font-mono flex items-center justify-between">
            <span>SERVICES</span>
            <Server className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1 font-mono">
            {summary?.services_count ?? 0}
          </div>
        </div>

        <div className="bg-[#121624] border border-[#1e2438] p-4 rounded-lg">
          <div className="text-xs text-slate-400 font-mono flex items-center justify-between">
            <span>INCIDENTS</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1 font-mono">
            {summary?.incidents_count ?? 0}
          </div>
        </div>

        <div className="bg-[#121624] border border-[#1e2438] p-4 rounded-lg">
          <div className="text-xs text-slate-400 font-mono flex items-center justify-between">
            <span>DEPLOYMENTS</span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1 font-mono">
            {summary?.deployments_count ?? 0}
          </div>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-[#121624] border border-[#1e2438] p-4 rounded-lg flex flex-col md:flex-row gap-4 items-center justify-between">
        <form onSubmit={handleSearch} className="flex-1 flex items-center space-x-2 w-full">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search architecture nodes, services, schemas, incidents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0a0d14] border border-[#1e2438] text-slate-200 text-sm rounded-md pl-9 pr-4 py-2 focus:outline-none focus:border-purple-500 font-mono"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-md text-xs font-mono transition-all"
          >
            Query Brain
          </button>
        </form>

        <div className="flex items-center space-x-2 w-full md:w-auto">
          <span className="text-xs text-slate-400 font-mono">TYPE:</span>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="bg-[#0a0d14] border border-[#1e2438] text-slate-200 text-xs rounded-md px-3 py-2 font-mono focus:outline-none focus:border-purple-500"
          >
            <option value="ALL">ALL TYPES</option>
            <option value="SERVICE">SERVICE</option>
            <option value="FILE">FILE</option>
            <option value="DATABASE">DATABASE</option>
            <option value="INCIDENT">INCIDENT</option>
            <option value="DEPLOYMENT">DEPLOYMENT</option>
            <option value="DECISION">DECISION</option>
          </select>
        </div>
      </div>

      {/* Main Grid: Knowledge Nodes & Node Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Knowledge Nodes List */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-300 font-mono flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              <span>KNOWLEDGE NODES ({filteredNodes.length})</span>
            </h2>
          </div>

          {loading ? (
            <div className="bg-[#121624] border border-[#1e2438] p-8 rounded-lg text-center text-slate-400 font-mono text-sm">
              Loading Project Brain memory...
            </div>
          ) : filteredNodes.length === 0 ? (
            <div className="bg-[#121624] border border-[#1e2438] p-8 rounded-lg text-center text-slate-400 font-mono text-sm">
              No matching knowledge nodes found. Try searching or click "Rebuild Brain".
            </div>
          ) : (
            <div className="space-y-3">
              {filteredNodes.map((n) => (
                <div
                  key={n.id || n.key}
                  onClick={() => setSelectedNode(n)}
                  className={`bg-[#121624] border p-4 rounded-lg cursor-pointer transition-all hover:border-purple-500/50 ${
                    selectedNode?.key === n.key
                      ? 'border-purple-500 bg-[#161b2e]'
                      : 'border-[#1e2438]'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        {getNodeTypeBadge(n.node_type)}
                        <span className="text-sm font-bold text-white">{n.title}</span>
                      </div>
                      <p className="text-xs text-slate-400 font-mono mt-1">
                        KEY: {n.key}
                      </p>
                    </div>
                    {getConfidenceBadge(n.confidence)}
                  </div>

                  <p className="text-xs text-slate-300 mt-2 line-clamp-2">
                    {n.content}
                  </p>

                  <div className="mt-3 pt-2 border-t border-[#1e2438] flex items-center justify-between text-[11px] text-slate-500 font-mono">
                    <span className="flex items-center space-x-1">
                      <span>SOURCE:</span>
                      <span className="text-slate-400">{n.source_type}</span>
                      {n.source_reference && (
                        <span className="text-purple-400 ml-1">({n.source_reference})</span>
                      )}
                    </span>
                    <span>UPDATED: {n.updated_at ? n.updated_at.slice(0, 10) : 'RECENT'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Node Detail & Event Ledger */}
        <div className="space-y-6">
          {/* Node Inspector */}
          <div className="bg-[#121624] border border-[#1e2438] p-5 rounded-lg space-y-4">
            <h2 className="text-sm font-semibold text-slate-300 font-mono flex items-center space-x-2 border-b border-[#1e2438] pb-3">
              <FileCode className="w-4 h-4 text-cyan-400" />
              <span>NODE INSPECTOR</span>
            </h2>

            {selectedNode ? (
              <div className="space-y-3 font-mono text-xs">
                <div>
                  <span className="text-slate-500">TITLE:</span>
                  <p className="text-slate-200 font-bold text-sm mt-0.5">{selectedNode.title}</p>
                </div>

                <div>
                  <span className="text-slate-500">PROVENANCE:</span>
                  <p className="text-purple-400 mt-0.5">
                    {selectedNode.source_type} — {selectedNode.source_reference || 'N/A'}
                  </p>
                </div>

                <div>
                  <span className="text-slate-500">CONFIDENCE RATING:</span>
                  <div className="mt-1">{getConfidenceBadge(selectedNode.confidence)}</div>
                </div>

                <div>
                  <span className="text-slate-500">CONTENT DESCRIPTION:</span>
                  <p className="text-slate-300 bg-[#0a0d14] p-2.5 rounded border border-[#1e2438] mt-1 leading-relaxed">
                    {selectedNode.content}
                  </p>
                </div>

                {selectedNode.metadata_payload && (
                  <div>
                    <span className="text-slate-500">METADATA PAYLOAD:</span>
                    <pre className="bg-[#0a0d14] p-2.5 rounded border border-[#1e2438] mt-1 text-[11px] text-cyan-300 overflow-x-auto">
                      {JSON.stringify(selectedNode.metadata_payload, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-slate-500 text-xs font-mono py-6 text-center">
                Select a knowledge node from the list to view provenance, confidence, and metadata details.
              </div>
            )}
          </div>

          {/* Event Audit History */}
          <div className="bg-[#121624] border border-[#1e2438] p-5 rounded-lg space-y-4">
            <h2 className="text-sm font-semibold text-slate-300 font-mono flex items-center space-x-2 border-b border-[#1e2438] pb-3">
              <History className="w-4 h-4 text-amber-400" />
              <span>EVENT AUDIT LEDGER</span>
            </h2>

            {events.length === 0 ? (
              <div className="text-slate-500 text-xs font-mono py-4 text-center">
                No recent brain audit events.
              </div>
            ) : (
              <div className="space-y-2 font-mono text-xs">
                {events.map((e, idx) => (
                  <div key={e.id || idx} className="border-b border-[#1e2438] pb-2 last:border-0">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-amber-400 font-bold">{e.event_type}</span>
                      <span className="text-slate-500">{e.created_at ? e.created_at.slice(11, 19) : ''}</span>
                    </div>
                    <p className="text-slate-300 text-[11px] mt-0.5">{e.description}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      REF: {e.source_reference}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
