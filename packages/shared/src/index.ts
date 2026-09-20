export interface Project {
  id: string;
  name: string;
  repo_url?: string | null;
  default_branch: string;
  github_owner?: string | null;
  github_repo?: string | null;
  github_url?: string | null;
  last_indexed_commit_sha?: string | null;
  last_indexed_at?: string | null;
  repository_snapshot?: RepositorySnapshot | null;
  created_at: string;
  updated_at: string;
}

export interface RootCauseHypothesis {
  summary: string;
  confidence: number;
  evidence: string[];
  files: string[];
  stack_frames: string[];
  unknowns: string[];
}

export interface ProposedFix {
  summary: string;
  files_to_change: string[];
  reason: string;
  expected_behavior: string;
  validation_plan: string[];
  risk_level: string;
}

export interface IncidentInvestigation {
  id: string;
  incident_id: string;
  status: string;
  confidence: number;
  hypothesis?: RootCauseHypothesis | null;
  evidence?: string[] | null;
  relevant_files?: string[] | null;
  relevant_stack_frames?: string[] | null;
  repository_matches?: any[] | null;
  proposed_fix?: ProposedFix | null;
  recommended_next_action?: string | null;
  created_at: string;
}

export interface Incident {
  id: string;
  project_id: string;
  title: string;
  status: 'OPEN' | 'INVESTIGATING' | 'PROPOSED_FIX' | 'AWAITING_APPROVAL' | 'RESOLVED' | 'IGNORED' | string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNKNOWN' | string;
  source: 'manual' | 'SENTRY' | 'MOCK_SENTRY' | 'datadog' | 'webhook' | string;
  description?: string | null;
  external_event_id?: string | null;
  external_issue_id?: string | null;
  error_type?: string | null;
  error_message?: string | null;
  environment?: string | null;
  release?: string | null;
  commit_sha?: string | null;
  culprit?: string | null;
  occurrence_count?: number;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  stack_trace?: any[] | null;
  investigation?: IncidentInvestigation | null;
  created_at: string;
  updated_at: string;
}

export interface ServiceStatus {
  service: string;
  version: string;
  environment: string;
  status: 'ok' | 'degraded' | 'down';
  database: {
    connected: boolean;
    details: string;
  };
  redis: {
    connected: boolean;
    details: string;
  };
}

export interface FrameworkDetection {
  name: string;
  type: 'framework' | 'runtime' | 'language' | 'package_manager';
  status: 'DETECTED' | 'INFERRED';
  confidence: number;
  evidence: string[];
}

export interface RepositoryTreeNode {
  path: string;
  name: string;
  type: 'file' | 'directory';
  size?: number;
  children?: RepositoryTreeNode[];
}

export interface RepositorySnapshot {
  owner: string;
  repo: string;
  default_branch: string;
  commit_sha: string;
  url: string;
  total_files: number;
  total_directories: number;
  detected_languages: string[];
  detections: FrameworkDetection[];
  important_files: string[];
  source_directories: string[];
  test_directories: string[];
  configuration_files: string[];
  tree: RepositoryTreeNode[];
  inspected_at: string;
}

export interface GitHubStatusResponse {
  provider_type: 'mock' | 'oauth';
  mock_enabled: boolean;
  client_id_configured: boolean;
  status: string;
}

export interface GitHubRepoSummary {
  id: string | number;
  owner: string;
  name: string;
  full_name: string;
  default_branch: string;
  html_url: string;
  private: boolean;
  description?: string | null;
}

// Agent Runtime & Code Agent Interfaces

export type AgentStatus = 'PENDING' | 'RUNNING' | 'WAITING' | 'AWAITING_APPROVAL' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export interface ToolCallRecord {
  tool_name: string;
  input_params: Record<string, any>;
  success: boolean;
  summary: string;
  started_at: string;
  completed_at: string;
  error?: string | null;
}

export interface ChangePlan {
  goal: string;
  reason: string;
  files_to_modify: string[];
  files_to_add: string[];
  validation_steps: string[];
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface GitDiff {
  files_changed: string[];
  diff_text: string;
  total_additions: number;
  total_deletions: number;
}

export interface PullRequestInfo {
  pr_number: number;
  pr_url: string;
  title: string;
  body: string;
  head_branch: string;
  base_branch: string;
  status: string;
}

export interface AgentRun {
  id: string;
  incident_id?: string | null;
  project_id: string;
  user_task: string;
  status: AgentStatus;
  current_goal?: string | null;
  current_step: number;
  iteration_count: number;
  started_at?: string | null;
  completed_at?: string | null;
  summary?: string | null;
  tool_calls: ToolCallRecord[];
  workspace_path?: string | null;
  agent_branch?: string | null;
  change_plan?: ChangePlan | null;
  diff_summary?: GitDiff | null;
  pull_request_url?: string | null;
  pull_request_status?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  created_at: string;
}

export interface CreateAgentRunRequest {
  project_id: string;
  task: string;
  incident_id?: string;
}

export interface ApproveAgentRunResponse {
  run_id: string;
  status: AgentStatus;
  message: string;
  pull_request_url?: string | null;
  provider?: 'mock' | 'github';
  is_mock?: boolean;
  pull_request_status?: string | null;
}

// Phase 5 Sandbox Validation Interfaces

export type CommandType = 'TEST' | 'BUILD' | 'LINT' | 'TYPECHECK';
export type SandboxStatus = 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'TIMED_OUT' | 'CANCELLED' | 'BLOCKED' | 'ERROR';
export type SandboxProviderType = 'MOCK_SANDBOX' | 'DOCKER_SANDBOX';

export interface SandboxRun {
  id: string;
  project_id: string;
  agent_run_id?: string | null;
  workspace_id: string;
  command_type: CommandType;
  runtime: string;
  provider_type: SandboxProviderType;
  status: SandboxStatus;
  exit_code: number;
  stdout: string;
  stderr: string;
  duration_ms: number;
  timeout_seconds: number;
  resource_limits?: Record<string, any> | null;
  error_message?: string | null;
  started_at: string;
  finished_at?: string | null;
  created_at: string;
}

export interface SandboxRunCreateRequest {
  project_id: string;
  workspace_id: string;
  command_type: CommandType;
  agent_run_id?: string;
  runtime?: string;
  force_mock?: boolean;
}

// Phase 6 Automated Verification & Self-Correction Interfaces

export type FailureType = 
  | 'TEST_FAILURE'
  | 'BUILD_FAILURE'
  | 'TYPE_ERROR'
  | 'LINT_FAILURE'
  | 'DEPENDENCY_ERROR'
  | 'CONFIGURATION_ERROR'
  | 'TIMEOUT'
  | 'RESOURCE_LIMIT'
  | 'UNKNOWN';

export interface FailureDiagnostic {
  message: string;
  file?: string | null;
  line?: number | null;
  column?: number | null;
  code?: string | null;
  source: string;
  raw_snippet?: string | null;
}

export interface ValidationResult {
  sandbox_run_id: string;
  status: SandboxStatus;
  command_type: CommandType;
  exit_code: number;
  summary: string;
  stdout: string;
  stderr: string;
  failure_type?: FailureType | null;
  diagnostics: FailureDiagnostic[];
  affected_files: string[];
  suggested_action: 'CONTINUE' | 'FIX' | 'RETRY' | 'STOP' | 'HUMAN_REVIEW';
}

export interface ValidationAttempt {
  id: string;
  agent_run_id: string;
  sandbox_run_id?: string | null;
  iteration: number;
  command_type: CommandType;
  status: SandboxStatus;
  failure_type?: FailureType | null;
  summary: string;
  diagnostic_data?: Record<string, any> | null;
  action_taken: string;
  created_at: string;
}

// Phase 7 Browser Verification Interfaces

export type BrowserActionType =
  | 'NAVIGATE'
  | 'CLICK'
  | 'FILL'
  | 'SELECT'
  | 'ASSERT_VISIBLE'
  | 'ASSERT_TEXT'
  | 'ASSERT_URL'
  | 'WAIT_FOR'
  | 'SCREENSHOT';

export type BrowserFailureType =
  | 'ELEMENT_NOT_FOUND'
  | 'ASSERTION_FAILED'
  | 'NAVIGATION_FAILED'
  | 'TIMEOUT'
  | 'CONSOLE_ERROR'
  | 'NETWORK_ERROR'
  | 'APPLICATION_ERROR'
  | 'BROWSER_CRASH'
  | 'BLOCKED_URL'
  | 'SCENARIO_INVALID'
  | 'APPLICATION_NOT_READY'
  | 'UNKNOWN';

export type BrowserRunStatus = 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'TIMED_OUT' | 'BLOCKED' | 'ERROR';

export interface BrowserStepResult {
  step_index: number;
  action: BrowserActionType;
  selector?: string | null;
  selector_strategy: string;
  status: BrowserRunStatus;
  duration_ms: number;
  error?: string | null;
  screenshot_path?: string | null;
  observed_value?: string | null;
}

export interface BrowserRun {
  id: string;
  project_id: string;
  agent_run_id?: string | null;
  workspace_id: string;
  scenario_id: string;
  provider_type: 'MOCK_BROWSER' | 'PLAYWRIGHT_BROWSER';
  status: BrowserRunStatus;
  base_url: string;
  current_url?: string | null;
  duration_ms: number;
  step_count: number;
  passed_steps: number;
  failed_steps: number;
  error_type?: BrowserFailureType | null;
  error_message?: string | null;
  suspected_file?: string | null;
  step_results: BrowserStepResult[];
  console_errors?: Record<string, any>[] | null;
  network_errors?: Record<string, any>[] | null;
  screenshot_paths?: string[] | null;
  created_at: string;
}

