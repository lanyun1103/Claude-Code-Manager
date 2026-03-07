import { getApiBase } from '../config/server';

function getBase(): string {
  return getApiBase();
}

export function getToken(): string {
  return localStorage.getItem('cc_token') || '';
}

export function setToken(token: string) {
  localStorage.setItem('cc_token', token);
}

export function clearToken() {
  localStorage.removeItem('cc_token');
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(`${getBase()}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    window.location.reload();
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export interface Project {
  id: number;
  name: string;
  git_url: string | null;
  has_remote: boolean;
  local_path: string | null;
  default_branch: string;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  status: string;
  priority: number;
  project_id: number | null;
  target_repo: string | null;
  target_branch: string;
  result_branch: string | null;
  merge_status: string;
  instance_id: number | null;
  retry_count: number;
  max_retries: number;
  mode: string;
  todo_file_path: string | null;
  loop_progress: string | null;
  plan_content: string | null;
  plan_approved: boolean | null;
  session_id: string | null;
  error_message: string | null;
  tags: string[] | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface Instance {
  id: number;
  name: string;
  pid: number | null;
  status: string;
  current_task_id: number | null;
  worktree_path: string | null;
  model: string;
  total_tasks_completed: number;
  total_cost_usd: number;
  started_at: string | null;
  last_heartbeat: string | null;
}

export interface ChatMessage {
  id: number;
  role: string;
  event_type: string;
  content: string | null;
  tool_name: string | null;
  tool_input: string | null;
  tool_output: string | null;
  is_error: boolean;
  loop_iteration: number | null;
  timestamp: string | null;
}

export interface LogEntry {
  id: number;
  instance_id: number;
  task_id: number | null;
  event_type: string;
  role: string | null;
  content: string | null;
  tool_name: string | null;
  is_error: boolean;
  timestamp: string;
}

export const api = {
  // Projects
  listProjects: () => request<Project[]>('/api/projects'),
  createProject: (data: { name: string; git_url?: string; default_branch?: string }) =>
    request<Project>('/api/projects', { method: 'POST', body: JSON.stringify(data) }),
  deleteProject: (id: number) =>
    request<{ ok: boolean }>(`/api/projects/${id}`, { method: 'DELETE' }),

  // Tasks
  listTasks: (status?: string) =>
    request<Task[]>(`/api/tasks${status ? `?status=${status}` : ''}`),
  createTask: (data: { title?: string; description?: string; project_id?: number; priority?: number; target_branch?: string; mode?: string; todo_file_path?: string }) =>
    request<Task>('/api/tasks', { method: 'POST', body: JSON.stringify(data) }),
  deleteTask: (id: number) =>
    request<{ ok: boolean }>(`/api/tasks/${id}`, { method: 'DELETE' }),
  cancelTask: (id: number) =>
    request<Task>(`/api/tasks/${id}/cancel`, { method: 'POST' }),
  retryTask: (id: number) =>
    request<Task>(`/api/tasks/${id}/retry`, { method: 'POST' }),
  approvePlan: (id: number) =>
    request<Task>(`/api/tasks/${id}/plan/approve`, { method: 'POST' }),
  rejectPlan: (id: number) =>
    request<Task>(`/api/tasks/${id}/plan/reject`, { method: 'POST' }),
  // Instances
  listInstances: () => request<Instance[]>('/api/instances'),
  createInstance: (data: { name: string; model?: string }) =>
    request<Instance>('/api/instances', { method: 'POST', body: JSON.stringify(data) }),
  deleteInstance: (id: number) =>
    request<{ ok: boolean }>(`/api/instances/${id}`, { method: 'DELETE' }),
  stopInstance: (id: number) =>
    request<{ ok: boolean }>(`/api/instances/${id}/stop`, { method: 'POST' }),
  runOnInstance: (id: number, params: { task_id?: number; prompt?: string }) =>
    request<{ ok: boolean; pid: number }>(`/api/instances/${id}/run?${new URLSearchParams(params as Record<string, string>)}`, { method: 'POST' }),
  getInstanceLogs: (id: number, limit = 100) =>
    request<LogEntry[]>(`/api/instances/${id}/logs?limit=${limit}`),

  // Ralph Loop (legacy)
  startRalph: (id: number) =>
    request<{ ok: boolean }>(`/api/instances/${id}/ralph/start`, { method: 'POST' }),
  stopRalph: (id: number) =>
    request<{ ok: boolean }>(`/api/instances/${id}/ralph/stop`, { method: 'POST' }),
  ralphStatus: (id: number) =>
    request<{ running: boolean }>(`/api/instances/${id}/ralph/status`),

  // Dispatcher
  dispatcherStatus: () =>
    request<{ running: boolean; active_tasks: Record<string, boolean> }>('/api/dispatcher/status'),
  startDispatcher: () =>
    request<{ ok: boolean }>('/api/dispatcher/start', { method: 'POST' }),
  stopDispatcher: () =>
    request<{ ok: boolean }>('/api/dispatcher/stop', { method: 'POST' }),

  // Chat (task-based)
  sendTaskChat: (taskId: number, message: string) =>
    request<{ ok: boolean; pid: number; instance_id: number; session_id: string }>(`/api/tasks/${taskId}/chat`, { method: 'POST', body: JSON.stringify({ message }) }),
  getTaskChatHistory: (taskId: number, limit = 200) =>
    request<ChatMessage[]>(`/api/tasks/${taskId}/chat/history?limit=${limit}`),

  // System
  health: () => request<{ status: string }>('/api/system/health'),
  stats: () => request<{ tasks: Record<string, number>; running_instances: number }>('/api/system/stats'),
};
