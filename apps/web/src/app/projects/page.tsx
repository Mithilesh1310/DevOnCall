'use client';

import React, { useEffect, useState } from 'react';
import { 
  FolderGit2, 
  GitBranch, 
  Plus, 
  RefreshCw, 
  Cpu, 
  CheckCircle2, 
  FileText, 
  Folder, 
  Code, 
  Layers, 
  ShieldCheck, 
  Bot,
  Play,
  Terminal,
  ExternalLink,
  Zap,
  AlertCircle,
  GitPullRequest,
  Check,
  FileCode,
  Shield,
  Box,
  CheckSquare,
  AlertTriangle
} from 'lucide-react';

interface GitHubRepo {
  id: string;
  owner: string;
  name: string;
  full_name: string;
  default_branch: string;
  html_url: string;
  is_private: boolean;
  description?: string;
}

interface Project {
  id: string;
  name: string;
  github_owner?: string;
  github_repo?: string;
  github_url?: string;
  default_branch: string;
  last_indexed_commit_sha?: string;
  last_indexed_at?: string;
  repository_snapshot?: any;
}

interface ToolCallRecord {
  tool_name: string;
  input_params: any;
  success: boolean;
  summary: string;
  started_at: string;
  completed_at: string;
  error?: string;
}

interface ChangePlan {
  goal: string;
  reason: string;
  files_to_modify: string[];
  files_to_add: string[];
  validation_steps: string[];
  risk_level: string;
}

interface GitDiff {
  files_changed: string[];
  diff_text: string;
  total_additions: number;
  total_deletions: number;
}

interface ValidationDiagnostic {
  message: string;
  file?: string;
  line?: number;
  column?: number;
  code?: string;
  source?: string;
}

interface ValidationHistoryItem {
  sandbox_run_id?: string;
  command_type: 'TEST' | 'BUILD' | 'LINT' | 'TYPECHECK';
  status: 'PASSED' | 'FAILED' | 'TIMED_OUT' | 'BLOCKED' | 'ERROR';
  summary?: string;
  iteration: number;
  failure_type?: string;
  diagnostic_data?: ValidationDiagnostic[];
  action_taken?: string;
}

interface RepairAttempt {
  iteration: number;
  failure_type: string;
  diagnostic?: string;
  files_changed: string[];
  validation_before?: string;
  validation_after?: string;
  result: string;
}

interface AgentRun {
  id: string;
  project_id: string;
  user_task: string;
  status: 'PENDING' | 'RUNNING' | 'FIXING' | 'VALIDATING' | 'PASSED' | 'FAILED' | 'AWAITING_HUMAN_REVIEW' | 'AWAITING_APPROVAL' | 'COMPLETED' | 'CANCELLED' | 'STOPPED';
  current_goal?: string;
  current_step: number;
  iteration_count: number;
  summary?: string;
  tool_calls: ToolCallRecord[];
  workspace_path?: string;
  agent_branch?: string;
  change_plan?: ChangePlan;
  diff_summary?: GitDiff;
  pull_request_url?: string;
  pull_request_status?: string;
  approved_by?: string;
  approved_at?: string;
  validation_history?: ValidationHistoryItem[];
  failure_analysis?: {
    failure_type?: string;
    summary?: string;
    diagnostics?: ValidationDiagnostic[];
    affected_files?: string[];
    suggested_action?: string;
  };
  repair_attempts?: RepairAttempt[];
  successful_validations?: string[];
  failed_validations?: string[];
  current_validation?: string;
  last_validation_result?: any;
  next_action?: string;
  stop_reason?: string;
  created_at: string;
}

interface SandboxRun {
  id: string;
  project_id: string;
  agent_run_id?: string;
  workspace_id: string;
  command_type: 'TEST' | 'BUILD' | 'LINT' | 'TYPECHECK';
  runtime: string;
  provider_type: 'MOCK_SANDBOX' | 'DOCKER_SANDBOX';
  status: 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'TIMED_OUT' | 'CANCELLED' | 'BLOCKED' | 'ERROR';
  exit_code: number;
  stdout: string;
  stderr: string;
  duration_ms: number;
  timeout_seconds: number;
  error_message?: string;
  created_at: string;
}

interface BrowserStepResultUI {
  step_index: number;
  action: string;
  selector?: string;
  selector_strategy: string;
  status: string;
  duration_ms: number;
  error?: string;
  screenshot_path?: string;
  observed_value?: string;
}

interface BrowserRunUI {
  id: string;
  project_id: string;
  agent_run_id?: string;
  workspace_id: string;
  scenario_id: string;
  provider_type: 'MOCK_BROWSER' | 'PLAYWRIGHT_BROWSER';
  status: 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'TIMED_OUT' | 'BLOCKED' | 'ERROR';
  base_url: string;
  current_url?: string;
  duration_ms: number;
  step_count: number;
  passed_steps: number;
  failed_steps: number;
  error_type?: string;
  error_message?: string;
  suspected_file?: string;
  step_results: BrowserStepResultUI[];
  console_errors?: any[];
  network_errors?: any[];
  screenshot_paths?: string[];
  created_at: string;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [availableRepos, setAvailableRepos] = useState<GitHubRepo[]>([]);
  const [githubStatus, setGithubStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [inspectingId, setInspectingId] = useState<string | null>(null);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [selectedRepoFullName, setSelectedRepoFullName] = useState<string>('');

  // Phase 3 & Phase 6 Code Agent State
  const [agentTasks, setAgentTasks] = useState<Record<string, string>>({});
  const [activeRuns, setActiveRuns] = useState<Record<string, AgentRun>>({});
  const [runningAgentProjectId, setRunningAgentProjectId] = useState<string | null>(null);
  const [approvingRunId, setApprovingRunId] = useState<string | null>(null);

  // Phase 5 Sandbox State
  const [sandboxRuns, setSandboxRuns] = useState<Record<string, SandboxRun>>({});
  const [runningSandboxCommand, setRunningSandboxCommand] = useState<string | null>(null);

  // Phase 7 Browser State
  const [browserRuns, setBrowserRuns] = useState<Record<string, BrowserRunUI>>({});
  const [selectedScenarios, setSelectedScenarios] = useState<Record<string, string>>({});
  const [runningBrowserProjectId, setRunningBrowserProjectId] = useState<string | null>(null);

  const runBrowserValidation = async (projectId: string, scenarioId: string, workspaceId: string, agentRunId?: string) => {
    setRunningBrowserProjectId(projectId);
    try {
      const res = await fetch(`${apiUrl}/api/v1/browser/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          workspace_id: workspaceId || `ws-${projectId.substring(0, 8)}`,
          scenario_id: scenarioId || 'login-smoke',
          base_url: 'http://localhost:3000',
          agent_run_id: agentRunId,
          use_mock: true
        })
      });

      if (res.ok) {
        const bRun: BrowserRunUI = await res.json();
        setBrowserRuns(prev => ({ ...prev, [projectId]: bRun }));
      }
    } catch (err) {
      console.error("Failed to execute browser verification:", err);
    } finally {
      setRunningBrowserProjectId(null);
    }
  };


  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchData = async () => {
    setLoading(true);
    try {
      const statusRes = await fetch(`${apiUrl}/api/v1/github/status`);
      if (statusRes.ok) setGithubStatus(await statusRes.json());

      const projRes = await fetch(`${apiUrl}/api/v1/projects`);
      if (projRes.ok) setProjects(await projRes.json());

      const reposRes = await fetch(`${apiUrl}/api/v1/github/repos`);
      if (reposRes.ok) setAvailableRepos(await reposRes.json());
    } catch (e) {
      console.error("Failed to load Phase 5 data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleConnectRepo = async () => {
    if (!selectedRepoFullName) return;
    const repo = availableRepos.find(r => r.full_name === selectedRepoFullName);
    if (!repo) return;

    try {
      const res = await fetch(`${apiUrl}/api/v1/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: repo.name,
          github_owner: repo.owner,
          github_repo: repo.name,
          default_branch: repo.default_branch,
          repo_url: repo.html_url
        })
      });

      if (res.ok) {
        const newProj = await res.json();
        setShowConnectModal(false);
        await triggerInspection(newProj.id);
      }
    } catch (err) {
      console.error("Failed to connect repository:", err);
    }
  };

  const triggerInspection = async (projectId: string) => {
    setInspectingId(projectId);
    try {
      const res = await fetch(`${apiUrl}/api/v1/projects/${projectId}/github/inspect`, {
        method: 'POST'
      });
      if (res.ok) {
        await fetchData();
      }
    } catch (err) {
      console.error("Failed to inspect repository:", err);
    } finally {
      setInspectingId(null);
    }
  };

  const runAgentTask = async (projectId: string) => {
    const task = agentTasks[projectId] || "Fix hello greeting function in code";
    setRunningAgentProjectId(projectId);

    try {
      const res = await fetch(`${apiUrl}/api/v1/agent/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          task: task
        })
      });

      if (res.ok) {
        const runData: AgentRun = await res.json();
        setActiveRuns(prev => ({ ...prev, [projectId]: runData }));
      }
    } catch (err) {
      console.error("Failed to execute code agent run:", err);
    } finally {
      setRunningAgentProjectId(null);
    }
  };

  const approveRun = async (projectId: string, runId: string) => {
    setApprovingRunId(runId);
    try {
      const res = await fetch(`${apiUrl}/api/v1/agent/runs/${runId}/approve`, {
        method: 'POST'
      });
      if (res.ok) {
        const runRes = await fetch(`${apiUrl}/api/v1/agent/runs/${runId}`);
        if (runRes.ok) {
          const updatedRun: AgentRun = await runRes.json();
          setActiveRuns(prev => ({ ...prev, [projectId]: updatedRun }));
        }
      }
    } catch (err) {
      console.error("Failed to approve agent run:", err);
    } finally {
      setApprovingRunId(null);
    }
  };

  const runSandboxValidation = async (projectId: string, workspaceId: string, commandType: 'TEST' | 'BUILD' | 'LINT' | 'TYPECHECK', agentRunId?: string) => {
    const key = `${projectId}-${commandType}`;
    setRunningSandboxCommand(key);

    try {
      const res = await fetch(`${apiUrl}/api/v1/sandbox/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          workspace_id: workspaceId || `ws-${projectId.substring(0, 8)}`,
          command_type: commandType,
          agent_run_id: agentRunId,
          runtime: 'python'
        })
      });

      if (res.ok) {
        const sandboxRun: SandboxRun = await res.json();
        setSandboxRuns(prev => ({ ...prev, [projectId]: sandboxRun }));
      }
    } catch (err) {
      console.error("Failed to execute sandbox validation:", err);
    } finally {
      setRunningSandboxCommand(null);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1e2438] pb-5">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-3">
              <Bot className="w-6 h-6 text-purple-400" />
              <span>DevOnCall Coding Agent Runtime & Browser Verification</span>
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-mono rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 font-bold">
              Phase 7 Active
            </span>
          </div>
          <p className="text-sm text-slate-400 font-mono">
            Controlled Coding Agent with Playwright Browser Verification, UI Testing Scenarios, Failure Classification, and PR Approval Gate.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="px-3 py-1.5 rounded-lg bg-[#121624] border border-[#1e2438] text-xs font-mono text-slate-300 flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Policy: BROWSER_SANDBOX (Allowlist URLs Only)</span>
          </div>
          <button 
            onClick={() => setShowConnectModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Connect Repository</span>
          </button>
        </div>
      </div>

      {/* Connect Modal */}
      {showConnectModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#121624] border border-[#1e2438] rounded-xl max-w-lg w-full p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-[#1e2438] pb-4">
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <FolderGit2 className="w-5 h-5 text-blue-400" />
                <span>Select GitHub Repository</span>
              </h3>
              <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                {githubStatus?.provider_type === 'mock' ? 'Mock Provider' : 'OAuth'}
              </span>
            </div>

            <div className="space-y-3">
              <label className="text-xs font-mono text-slate-400">Available Repositories</label>
              <select
                value={selectedRepoFullName}
                onChange={(e) => setSelectedRepoFullName(e.target.value)}
                className="w-full bg-[#0a0d14] border border-[#1e2438] rounded-lg p-3 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
              >
                <option value="">-- Choose a repository --</option>
                {availableRepos.map((repo) => (
                  <option key={repo.id} value={repo.full_name}>
                    {repo.full_name} ({repo.default_branch})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center justify-end space-x-3 pt-4 border-t border-[#1e2438]">
              <button
                onClick={() => setShowConnectModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleConnectRepo}
                disabled={!selectedRepoFullName}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center space-x-2"
              >
                <Zap className="w-4 h-4" />
                <span>Connect & Inspect</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Projects List */}
      <div className="space-y-8">
        {projects.length === 0 ? (
          <div className="bg-[#121624] border border-[#1e2438] rounded-xl p-12 text-center space-y-4">
            <Bot className="w-10 h-10 text-purple-400 mx-auto" />
            <h3 className="text-base font-semibold text-white">No Connected Workspaces Available</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Connect a repository to activate DevOnCall Phase 5 Docker sandbox validation and PR generation.
            </p>
            <button
              onClick={() => setShowConnectModal(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold inline-flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Connect Repository</span>
            </button>
          </div>
        ) : (
          projects.map((proj) => {
            const snapshot = proj.repository_snapshot;
            const isInspecting = inspectingId === proj.id;
            const isAgentRunning = runningAgentProjectId === proj.id;
            const activeRun = activeRuns[proj.id];
            const activeSandbox = sandboxRuns[proj.id];

            return (
              <div key={proj.id} className="bg-[#121624] border border-[#1e2438] rounded-xl p-6 space-y-6">
                {/* Repository Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1e2438] pb-4">
                  <div>
                    <div className="flex items-center space-x-3">
                      <h2 className="text-lg font-bold text-white font-mono">{proj.name}</h2>
                      {proj.github_owner && (
                        <a 
                          href={proj.github_url || '#'} 
                          target="_blank" 
                          rel="noreferrer"
                          className="text-xs text-blue-400 hover:underline font-mono flex items-center space-x-1"
                        >
                          <span>{proj.github_owner}/{proj.github_repo}</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 font-mono mt-1">
                      Branch: <span className="text-slate-200">{proj.default_branch}</span> • Commit: <span className="text-slate-200">{proj.last_indexed_commit_sha ? proj.last_indexed_commit_sha.substring(0, 8) : 'Not Inspected'}</span>
                    </p>
                  </div>

                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => triggerInspection(proj.id)}
                      disabled={isInspecting}
                      className="px-3.5 py-1.5 bg-[#1a2032] border border-[#2a3450] hover:border-blue-500 rounded-lg text-xs font-mono text-slate-200 flex items-center space-x-2 transition-colors"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${isInspecting ? 'animate-spin' : ''}`} />
                      <span>{isInspecting ? 'Inspecting...' : 'Re-Inspect Repository'}</span>
                    </button>
                  </div>
                </div>

                {/* PHASE 3 & 5: CODING AGENT WORKSPACE & SANDBOX PANEL */}
                <div className="bg-[#0b0e17] border border-purple-500/30 rounded-xl p-5 space-y-5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-sm font-bold text-purple-300">
                      <Bot className="w-5 h-5 text-purple-400" />
                      <span>DevOnCall Phase 5 Agent Runtime & Sandbox</span>
                    </div>
                    <span className="text-xs font-mono text-slate-400 bg-purple-500/10 border border-purple-500/20 px-2.5 py-0.5 rounded">
                      EXECUTE_SANDBOX + PR Approval Gate
                    </span>
                  </div>

                  {/* Task Input Box */}
                  <div className="flex flex-col sm:flex-row gap-3">
                    <input
                      type="text"
                      placeholder="e.g. Fix hello greeting function in code"
                      value={agentTasks[proj.id] ?? 'Fix hello greeting function in code'}
                      onChange={(e) => setAgentTasks(prev => ({ ...prev, [proj.id]: e.target.value }))}
                      className="flex-1 bg-[#121624] border border-[#1e2438] rounded-lg px-4 py-2.5 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
                    />
                    <button
                      onClick={() => runAgentTask(proj.id)}
                      disabled={isAgentRunning}
                      className="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition-colors"
                    >
                      <Play className={`w-4 h-4 ${isAgentRunning ? 'animate-spin' : ''}`} />
                      <span>{isAgentRunning ? 'Running Coding Agent...' : 'Run Coding Agent Task'}</span>
                    </button>
                  </div>

                  {/* PHASE 5: CONTROLLED SANDBOX VALIDATION CONTROLS */}
                  <div className="p-4 bg-[#121624] border border-[#1e2438] rounded-xl space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2 text-xs font-mono font-bold text-cyan-300">
                        <Box className="w-4 h-4 text-cyan-400" />
                        <span>Controlled Sandbox Validation Controls</span>
                      </div>
                      <span className="text-[11px] font-mono text-slate-400 bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 rounded">
                        Command Allowlist Only
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs">
                      {(['TEST', 'BUILD', 'LINT', 'TYPECHECK'] as const).map((cmd) => {
                        const isRunning = runningSandboxCommand === `${proj.id}-${cmd}`;
                        return (
                          <button
                            key={cmd}
                            onClick={() => runSandboxValidation(proj.id, activeRun?.workspace_path || `ws-${proj.id.substring(0, 8)}`, cmd, activeRun?.id)}
                            disabled={isRunning}
                            className="px-3 py-2 bg-[#1a2032] hover:bg-[#252e48] disabled:opacity-50 border border-[#2a3450] hover:border-cyan-500 text-slate-200 rounded-lg flex items-center justify-center space-x-1.5 transition-colors"
                          >
                            <Play className={`w-3 h-3 text-cyan-400 ${isRunning ? 'animate-spin' : ''}`} />
                            <span>Run {cmd}</span>
                          </button>
                        );
                      })}
                    </div>

                    {/* Active Sandbox Run Output */}
                    {activeSandbox && (
                      <div className="p-4 bg-[#080b12] border border-[#1e2438] rounded-lg space-y-3 font-mono text-xs">
                        <div className="flex items-center justify-between border-b border-[#1e2438] pb-2">
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-slate-200">Sandbox Command: {activeSandbox.command_type}</span>
                            <span className={`px-2 py-0.5 text-[10px] rounded font-bold border ${
                              activeSandbox.provider_type === 'MOCK_SANDBOX'
                                ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                                : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                            }`}>
                              {activeSandbox.provider_type === 'MOCK_SANDBOX' ? 'MOCK SANDBOX' : 'DOCKER SANDBOX'}
                            </span>
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className="text-slate-400 text-[11px]">Duration: {activeSandbox.duration_ms}ms</span>
                            <span className={`px-2 py-0.5 rounded font-bold border ${
                              activeSandbox.status === 'PASSED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                              activeSandbox.status === 'FAILED' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                              activeSandbox.status === 'BLOCKED' ? 'bg-amber-500/10 text-amber-300 border-amber-500/20' :
                              'bg-slate-800 text-slate-300 border-slate-700'
                            }`}>
                              {activeSandbox.status} (Exit: {activeSandbox.exit_code})
                            </span>
                          </div>
                        </div>

                        {activeSandbox.stdout && (
                          <div>
                            <span className="text-slate-400 text-[11px] block mb-1">stdout:</span>
                            <pre className="p-3 bg-[#030508] border border-[#1e2438] rounded text-emerald-300 overflow-x-auto max-h-40">{activeSandbox.stdout}</pre>
                          </div>
                        )}

                        {activeSandbox.stderr && (
                          <div>
                            <span className="text-slate-400 text-[11px] block mb-1">stderr:</span>
                            <pre className="p-3 bg-[#030508] border border-[#1e2438] rounded text-rose-300 overflow-x-auto max-h-40">{activeSandbox.stderr}</pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* PHASE 7: PLAYWRIGHT BROWSER VERIFICATION PANEL */}
                  <div className="p-4 bg-[#121624] border border-blue-500/30 rounded-xl space-y-4 font-mono text-xs">
                    <div className="flex items-center justify-between border-b border-[#1e2438] pb-3">
                      <div className="flex items-center space-x-2">
                        <ExternalLink className="w-4 h-4 text-blue-400" />
                        <span className="font-bold text-blue-200">Phase 7 Playwright Browser Verification</span>
                      </div>
                      <span className="text-[11px] font-mono text-slate-400 bg-blue-500/10 border border-blue-500/20 px-2.5 py-0.5 rounded">
                        Target: http://localhost:3000 (Allowlisted)
                      </span>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-3">
                      <select
                        value={selectedScenarios[proj.id] || 'login-smoke'}
                        onChange={(e) => setSelectedScenarios(prev => ({ ...prev, [proj.id]: e.target.value }))}
                        className="flex-1 bg-[#0a0d14] border border-[#1e2438] rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-blue-500"
                      >
                        <option value="login-smoke">Scenario: Login Smoke Test (PASS)</option>
                        <option value="dashboard-navigation">Scenario: Dashboard Navigation (PASS)</option>
                        <option value="element-missing-test">Scenario: Element Missing Test (FAIL - ELEMENT_NOT_FOUND)</option>
                        <option value="assertion-failure-test">Scenario: Assertion Failure Test (FAIL - ASSERTION_FAILED)</option>
                        <option value="network-error-test">Scenario: Network 500 Error Test (FAIL - NETWORK_ERROR)</option>
                        <option value="console-error-test">Scenario: Uncaught Console Error Test (FAIL - CONSOLE_ERROR)</option>
                        <option value="app-unavailable-test">Scenario: App Unavailable Test (FAIL - APPLICATION_NOT_READY)</option>
                      </select>
                      <button
                        onClick={() => runBrowserValidation(proj.id, selectedScenarios[proj.id] || 'login-smoke', activeRun?.workspace_path || `ws-${proj.id.substring(0, 8)}`, activeRun?.id)}
                        disabled={runningBrowserProjectId === proj.id}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold font-mono flex items-center justify-center space-x-2 transition-colors"
                      >
                        <Play className={`w-3.5 h-3.5 text-white ${runningBrowserProjectId === proj.id ? 'animate-spin' : ''}`} />
                        <span>{runningBrowserProjectId === proj.id ? 'Running Browser Agent...' : 'Run Browser Verification'}</span>
                      </button>
                    </div>

                    {/* Active Browser Run Display */}
                    {browserRuns[proj.id] && (
                      <div className="p-4 bg-[#080b12] border border-blue-500/20 rounded-lg space-y-4">
                        <div className="flex items-center justify-between border-b border-[#1e2438] pb-2">
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-slate-200">Scenario: {browserRuns[proj.id].scenario_id}</span>
                            <span className={`px-2 py-0.5 text-[10px] rounded font-bold border ${
                              browserRuns[proj.id].provider_type === 'MOCK_BROWSER'
                                ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                                : 'bg-blue-500/10 text-blue-300 border-blue-500/30'
                            }`}>
                              {browserRuns[proj.id].provider_type === 'MOCK_BROWSER' ? 'MOCK BROWSER' : 'PLAYWRIGHT BROWSER'}
                            </span>
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className="text-slate-400 text-[11px]">Duration: {browserRuns[proj.id].duration_ms}ms</span>
                            <span className={`px-2.5 py-0.5 rounded font-bold border ${
                              browserRuns[proj.id].status === 'PASSED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                              browserRuns[proj.id].status === 'FAILED' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                              'bg-amber-500/10 text-amber-300 border-amber-500/20'
                            }`}>
                              {browserRuns[proj.id].status}
                            </span>
                          </div>
                        </div>

                        {/* Error Classification & Repository File Correlation */}
                        {browserRuns[proj.id].error_type && (
                          <div className="p-3 bg-rose-950/20 border border-rose-500/30 rounded text-[11px] space-y-1">
                            <div className="flex items-center justify-between text-rose-300 font-bold">
                              <span>Failure Classified: {browserRuns[proj.id].error_type}</span>
                              {browserRuns[proj.id].suspected_file && (
                                <span className="text-cyan-300 font-bold bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-500/30">
                                  Suspected File: {browserRuns[proj.id].suspected_file}
                                </span>
                              )}
                            </div>
                            <p className="text-slate-300">{browserRuns[proj.id].error_message}</p>
                          </div>
                        )}

                        {/* Step Execution Stepper */}
                        <div className="space-y-1.5">
                          <span className="text-[11px] font-bold text-slate-400 uppercase">Scenario Execution Timeline</span>
                          <div className="space-y-1">
                            {browserRuns[proj.id].step_results.map((s, idx) => (
                              <div key={idx} className="p-2 bg-[#05070c] border border-[#1e2438] rounded flex items-center justify-between text-[11px]">
                                <div className="flex items-center space-x-2">
                                  <span className={`font-bold ${s.status === 'PASSED' ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    {s.status === 'PASSED' ? '✓' : '✗'} Step #{s.step_index}: {s.action}
                                  </span>
                                  {s.selector && <code className="text-cyan-300 text-[10px]">{s.selector}</code>}
                                </div>
                                <div className="flex items-center space-x-2 text-slate-400">
                                  <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded">{s.selector_strategy}</span>
                                  <span>{s.duration_ms}ms</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Console & Network Logs */}
                        {browserRuns[proj.id].console_errors && browserRuns[proj.id].console_errors!.length > 0 && (
                          <div className="space-y-1">
                            <span className="text-amber-300 text-[10px] font-bold uppercase">Captured Console Errors</span>
                            <pre className="p-2 bg-[#030508] border border-amber-500/20 rounded text-amber-300 text-[10px] overflow-x-auto max-h-24">
                              {JSON.stringify(browserRuns[proj.id].console_errors, null, 2)}
                            </pre>
                          </div>
                        )}

                        {browserRuns[proj.id].network_errors && browserRuns[proj.id].network_errors!.length > 0 && (
                          <div className="space-y-1">
                            <span className="text-rose-300 text-[10px] font-bold uppercase">Captured Failed Network Requests</span>
                            <pre className="p-2 bg-[#030508] border border-rose-500/20 rounded text-rose-300 text-[10px] overflow-x-auto max-h-24">
                              {JSON.stringify(browserRuns[proj.id].network_errors, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Agent Run Output & Change Inspector */}
                  {activeRun && (
                    <div className="pt-4 border-t border-[#1e2438] space-y-5">
                      {/* Agent Run Output Header & Status */}
                      <div className="flex flex-wrap items-center justify-between text-xs font-mono gap-2">
                        <span className="text-slate-400">Run ID: <span className="text-slate-200">{activeRun.id.substring(0, 8)}</span></span>
                        {activeRun.agent_branch && (
                          <span className="text-slate-400 flex items-center space-x-1">
                            <GitBranch className="w-3.5 h-3.5 text-blue-400" />
                            <span>Branch: <span className="text-blue-300 font-bold">{activeRun.agent_branch}</span></span>
                          </span>
                        )}
                        <div className="flex items-center space-x-3">
                          <span className={`px-2.5 py-1 rounded border font-semibold ${
                            activeRun.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                            activeRun.status === 'PASSED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                            activeRun.status === 'AWAITING_HUMAN_REVIEW' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse' :
                            activeRun.status === 'AWAITING_APPROVAL' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse' :
                            activeRun.status === 'FIXING' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' :
                            activeRun.status === 'VALIDATING' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' :
                            'bg-slate-800 text-slate-300 border-slate-700'
                          }`}>
                            {activeRun.status === 'AWAITING_HUMAN_REVIEW' ? '⚠️ AWAITING HUMAN REVIEW' :
                             activeRun.status === 'AWAITING_APPROVAL' ? '⚠️ AWAITING HUMAN APPROVAL' :
                             activeRun.status}
                          </span>
                        </div>
                      </div>

                      {/* PHASE 6: AUTOMATED VERIFICATION & BOUNDED SELF-CORRECTION TIMELINE */}
                      <div className="p-4 bg-[#080b12] border border-purple-500/30 rounded-xl space-y-4 font-mono text-xs">
                        <div className="flex items-center justify-between border-b border-[#1e2438] pb-3">
                          <div className="flex items-center space-x-2">
                            <RefreshCw className="w-4 h-4 text-purple-400" />
                            <span className="font-bold text-purple-200">Verification & Bounded Self-Correction Loop</span>
                          </div>
                          <div className="flex items-center space-x-3 text-[11px] text-slate-400">
                            <span>Iterations: <strong className="text-purple-300">{activeRun.iteration_count || 1} / 10</strong></span>
                            <span>Next Action: <strong className="text-cyan-300">{activeRun.next_action || 'CONTINUE'}</strong></span>
                          </div>
                        </div>

                        {/* Current Failure Analysis & Diagnostic Box */}
                        {activeRun.failure_analysis && activeRun.failure_analysis.failure_type && (
                          <div className="p-3 bg-rose-950/20 border border-rose-500/30 rounded-lg space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-rose-300 flex items-center space-x-2">
                                <AlertTriangle className="w-4 h-4 text-rose-400" />
                                <span>Failure Classified: {activeRun.failure_analysis.failure_type}</span>
                              </span>
                              <span className="px-2 py-0.5 text-[10px] bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded font-bold">
                                ACTION: {activeRun.failure_analysis.suggested_action || activeRun.next_action || 'FIX'}
                              </span>
                            </div>
                            <p className="text-slate-300 text-[11px]">{activeRun.failure_analysis.summary}</p>

                            {activeRun.failure_analysis.diagnostics && activeRun.failure_analysis.diagnostics.length > 0 && (
                              <div className="space-y-1 pt-1">
                                <span className="text-slate-400 text-[10px] uppercase font-bold">Extracted Diagnostics:</span>
                                {activeRun.failure_analysis.diagnostics.map((diag, idx) => (
                                  <div key={idx} className="p-2 bg-[#030508] border border-rose-900/40 rounded text-[11px] space-y-1">
                                    <div className="flex items-center justify-between text-cyan-300 font-bold">
                                      <span>{diag.file ? `${diag.file}:${diag.line || 1}${diag.column ? `:${diag.column}` : ''}` : 'Unknown File'}</span>
                                      {diag.code && <span className="text-amber-400 text-[10px]">[{diag.code}]</span>}
                                    </div>
                                    <p className="text-slate-300 font-mono text-[11px]">{diag.message}</p>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Iteration Timeline Stepper */}
                        {activeRun.validation_history && activeRun.validation_history.length > 0 ? (
                          <div className="space-y-2">
                            <span className="text-[11px] font-bold text-slate-400 uppercase">Verification History Timeline</span>
                            <div className="space-y-2">
                              {activeRun.validation_history.map((val, idx) => (
                                <div key={idx} className="p-3 bg-[#0d111d] border border-[#1e2438] rounded-lg flex items-center justify-between">
                                  <div className="flex items-center space-x-3">
                                    <span className="px-2 py-0.5 text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded font-bold">
                                      Iteration #{val.iteration}
                                    </span>
                                    <span className="font-bold text-slate-200">Command: {val.command_type}</span>
                                    {val.failure_type && (
                                      <span className="px-2 py-0.5 text-[10px] bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded font-mono font-semibold">
                                        {val.failure_type}
                                      </span>
                                    )}
                                  </div>
                                  <div className="flex items-center space-x-3">
                                    <span className={`px-2.5 py-0.5 rounded font-bold border text-[11px] ${
                                      val.status === 'PASSED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                      val.status === 'FAILED' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                                      'bg-amber-500/10 text-amber-300 border-amber-500/20'
                                    }`}>
                                      {val.status}
                                    </span>
                                    {val.action_taken && (
                                      <span className="text-slate-400 text-[10px]">Action: <strong className="text-cyan-300">{val.action_taken}</strong></span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="p-3 bg-[#0d111d] border border-[#1e2438] rounded-lg text-slate-400 text-[11px] text-center">
                            No validation iterations recorded yet. Run a coding agent task or sandbox command to populate verification timeline.
                          </div>
                        )}

                        {activeRun.stop_reason && (
                          <div className="p-2.5 bg-amber-950/20 border border-amber-500/30 rounded text-[11px] text-amber-300 flex items-center justify-between">
                            <span>Loop Stop Reason: <strong>{activeRun.stop_reason}</strong></span>
                            <span className="text-[10px] text-slate-400 font-normal">Bounded Execution Safeguard Active</span>
                          </div>
                        )}
                      </div>

                      {/* Human Approval Gate Banner */}
                      {activeRun.status === 'AWAITING_APPROVAL' && (
                        <div className="p-4 bg-amber-950/30 border border-amber-500/40 rounded-xl space-y-3">
                          <div className="flex items-start space-x-3">
                            <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                            <div>
                              <h4 className="text-sm font-bold text-amber-200 font-mono">Human Approval Required for Pull Request</h4>
                              <p className="text-xs text-slate-300 font-mono mt-1">
                                Workspace modifications have been staged and committed to feature branch <code className="text-amber-300 font-bold">{activeRun.agent_branch}</code>. Review the diff below and approve PR creation.
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center justify-end space-x-3 pt-2">
                            <button
                              onClick={() => approveRun(proj.id, activeRun.id)}
                              disabled={approvingRunId === activeRun.id}
                              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold font-mono flex items-center space-x-2 transition-colors"
                            >
                              <GitPullRequest className="w-4 h-4" />
                              <span>{approvingRunId === activeRun.id ? 'Submitting PR...' : 'Approve & Create Pull Request'}</span>
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Created Pull Request Link */}
                      {activeRun.pull_request_url && (
                        <div className="p-4 bg-emerald-950/30 border border-emerald-500/40 rounded-xl flex items-center justify-between font-mono text-xs">
                          <div className="flex items-center space-x-3">
                            <GitPullRequest className="w-5 h-5 text-emerald-400" />
                            <div>
                              <div className="flex items-center space-x-2">
                                <span className="font-bold text-emerald-200">
                                  {activeRun.pull_request_status === 'MOCK_CREATED' ? 'Mock Pull Request Created' : 'GitHub Pull Request Created'}
                                </span>
                                <span className={`px-2 py-0.5 text-[10px] rounded font-mono font-bold border ${
                                  activeRun.pull_request_status === 'MOCK_CREATED' 
                                    ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                                    : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                                }`}>
                                  {activeRun.pull_request_status === 'MOCK_CREATED' ? 'PROVIDER: MOCK' : 'PROVIDER: GITHUB'}
                                </span>
                              </div>
                              <p className="text-slate-400 text-[11px] mt-0.5">
                                Targeting default branch <code className="text-emerald-300">{proj.default_branch}</code> from feature branch <code className="text-blue-300">{activeRun.agent_branch}</code>
                              </p>
                            </div>
                          </div>
                          <a
                            href={activeRun.pull_request_url}
                            target="_blank"
                            rel="noreferrer"
                            className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-bold flex items-center space-x-1.5 transition-colors"
                          >
                            <span>View {activeRun.pull_request_status === 'MOCK_CREATED' ? 'Mock PR #101' : 'PR #101'}</span>
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </div>
                      )}

                      {/* Unified Diff Inspector */}
                      {activeRun.diff_summary && (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-xs font-mono">
                            <span className="text-slate-300 font-bold flex items-center space-x-2">
                              <FileCode className="w-4 h-4 text-cyan-400" />
                              <span>Workspace Unified Diff</span>
                            </span>
                            <span className="text-emerald-400 font-mono text-[11px]">
                              +{activeRun.diff_summary.total_additions} additions
                            </span>
                          </div>
                          <div className="bg-[#05070c] border border-[#1e2438] rounded-lg p-4 font-mono text-xs text-slate-300 overflow-x-auto max-h-60">
                            <pre className="whitespace-pre-wrap">{activeRun.diff_summary.diff_text || 'No diff text available.'}</pre>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Intelligence Snapshot Display */}
                {snapshot && (
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-2">
                    <div className="space-y-4">
                      <div className="bg-[#0b0e17] border border-[#1e2438] rounded-lg p-4 space-y-3">
                        <h4 className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center space-x-2">
                          <Cpu className="w-4 h-4 text-purple-400" />
                          <span>Detected Frameworks & Runtimes</span>
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {snapshot.detections.map((d: any, idx: number) => (
                            <span 
                              key={idx}
                              className={`px-2.5 py-1 text-xs font-mono rounded-md border flex items-center space-x-1.5 ${
                                d.status === 'DETECTED' 
                                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                                  : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                              }`}
                            >
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                              <span>{d.name} ({d.status})</span>
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="bg-[#0b0e17] border border-[#1e2438] rounded-lg p-4 space-y-3 font-mono text-xs">
                        <h4 className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center space-x-2">
                          <Code className="w-4 h-4 text-blue-400" />
                          <span>Languages & Stats</span>
                        </h4>
                        <div className="space-y-2 text-slate-300">
                          <div className="flex justify-between">
                            <span className="text-slate-400">Languages:</span>
                            <span>{snapshot.detected_languages.join(', ') || 'N/A'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-400">Total Files:</span>
                            <span>{snapshot.total_files}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-400">Total Directories:</span>
                            <span>{snapshot.total_directories}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="bg-[#0b0e17] border border-[#1e2438] rounded-lg p-4 space-y-3">
                        <h4 className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center space-x-2">
                          <FileText className="w-4 h-4 text-amber-400" />
                          <span>Manifests & Configurations</span>
                        </h4>
                        <ul className="space-y-1.5 font-mono text-xs text-slate-300">
                          {snapshot.important_files.map((file: string, idx: number) => (
                            <li key={idx} className="flex items-center space-x-2 text-slate-300">
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                              <span>{file}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="bg-[#0b0e17] border border-[#1e2438] rounded-lg p-4 space-y-3">
                        <h4 className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center space-x-2">
                          <Layers className="w-4 h-4 text-emerald-400" />
                          <span>Source & Test Directories</span>
                        </h4>
                        <div className="font-mono text-xs space-y-2">
                          <div>
                            <span className="text-slate-400">Source Dirs:</span>
                            <div className="text-slate-200 font-semibold">{snapshot.source_directories.join(', ') || 'None'}</div>
                          </div>
                          <div>
                            <span className="text-slate-400">Test Dirs:</span>
                            <div className="text-slate-200 font-semibold">{snapshot.test_directories.join(', ') || 'None'}</div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="bg-[#0b0e17] border border-[#1e2438] rounded-lg p-4 space-y-3">
                      <h4 className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center space-x-2">
                        <Folder className="w-4 h-4 text-blue-400" />
                        <span>Normalized Repository Tree</span>
                      </h4>
                      <div className="max-h-72 overflow-y-auto space-y-1 font-mono text-xs text-slate-300 pr-2">
                        {snapshot.tree.map((node: any, idx: number) => (
                          <div key={idx} className="flex items-center space-x-2 py-0.5 hover:text-white">
                            {node.type === 'directory' ? (
                              <Folder className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                            ) : (
                              <FileText className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                            )}
                            <span className="truncate">{node.path}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
