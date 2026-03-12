import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { Project, GlobalSettings } from '../api/client';
import { Trash2, RotateCcw, FolderGit2, Globe, HardDrive, Plus, Settings, X, ChevronDown, ChevronUp } from 'lucide-react';

// ── Shared: identity warning ──────────────────────────────────────────────────

function IdentityWarning({ name, email }: { name: string; email: string }) {
  const hasName = name.trim() !== '';
  const hasEmail = email.trim() !== '';
  if ((hasName && hasEmail) || (!hasName && !hasEmail)) return null;
  return (
    <p className="col-span-2 text-xs text-amber-400">
      姓名和邮箱必须同时填写才会生效，否则将使用全局配置
    </p>
  );
}

// ── Global Git Config Modal ───────────────────────────────────────────────────

function GlobalGitConfigModal({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState<Omit<GlobalSettings, never>>({
    git_author_name: null,
    git_author_email: null,
    git_credential_type: null,
    git_ssh_key_path: null,
    git_https_username: null,
    git_https_token: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const name = form.git_author_name ?? '';
  const email = form.git_author_email ?? '';
  const credType = form.git_credential_type ?? '';

  useEffect(() => {
    api.getGitSettings().then((data) => {
      setForm(data);
      setLoading(false);
    }).catch((e) => {
      setError(String(e));
      setLoading(false);
    });
  }, []);

  const set = (key: keyof GlobalSettings, value: string) =>
    setForm((f) => ({ ...f, [key]: value || null }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.updateGitSettings({
        git_author_name: name.trim() || null,
        git_author_email: email.trim() || null,
        git_credential_type: credType || null,
        git_ssh_key_path: form.git_ssh_key_path?.trim() || null,
        git_https_username: form.git_https_username?.trim() || null,
        git_https_token: form.git_https_token?.trim() || null,
      });
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <h3 className="text-foreground font-semibold">Global Git Config</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200"><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && <p className="text-red-400 text-sm">{error}</p>}
          {loading ? (
            <p className="text-gray-400 text-sm">Loading...</p>
          ) : (
            <>
              <p className="text-xs text-gray-500">项目未配置时使用此全局默认值。</p>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Author name</label>
                  <input
                    className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                    value={name} onChange={(e) => set('git_author_name', e.target.value)}
                    placeholder="Zhang San"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Author email</label>
                  <input
                    className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                    value={email} onChange={(e) => set('git_author_email', e.target.value)}
                    placeholder="zhang@example.com"
                  />
                </div>
                <IdentityWarning name={name} email={email} />
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Credential type</label>
                <select
                  className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                  value={credType} onChange={(e) => set('git_credential_type', e.target.value)}
                >
                  <option value="">None</option>
                  <option value="ssh">SSH key</option>
                  <option value="https">HTTPS token</option>
                </select>
              </div>

              {credType === 'ssh' && (
                <div>
                  <label className="block text-xs text-gray-400 mb-1">SSH private key path</label>
                  <input
                    className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                    value={form.git_ssh_key_path ?? ''} onChange={(e) => set('git_ssh_key_path', e.target.value)}
                    placeholder="/home/alice/.ssh/id_ed25519"
                  />
                </div>
              )}

              {credType === 'https' && (
                <div className="space-y-2">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Username</label>
                    <input
                      className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                      value={form.git_https_username ?? ''} onChange={(e) => set('git_https_username', e.target.value)}
                      placeholder="github-username"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Personal access token</label>
                    <input
                      type="password"
                      className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                      value={form.git_https_token ?? ''} onChange={(e) => set('git_https_token', e.target.value)}
                      placeholder="ghp_..."
                    />
                  </div>
                </div>
              )}
            </>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-300 hover:text-white">Cancel</button>
            <button
              type="submit"
              disabled={submitting || loading}
              className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-500 disabled:opacity-50"
            >
              {submitting ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Create Project Modal ──────────────────────────────────────────────────────

interface CreateForm {
  name: string;
  git_url: string;
  default_branch: string;
  git_author_name: string;
  git_author_email: string;
  git_credential_type: string;  // "" | "ssh" | "https"
  git_ssh_key_path: string;
  git_https_username: string;
  git_https_token: string;
}

const emptyForm = (): CreateForm => ({
  name: '',
  git_url: '',
  default_branch: 'main',
  git_author_name: '',
  git_author_email: '',
  git_credential_type: '',
  git_ssh_key_path: '',
  git_https_username: '',
  git_https_token: '',
});

function CreateModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState<CreateForm>(emptyForm());
  const [showGit, setShowGit] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const identityName = form.git_author_name;
  const identityEmail = form.git_author_email;

  const set = (key: keyof CreateForm, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.createProject({
        name: form.name.trim(),
        git_url: form.git_url.trim() || undefined,
        default_branch: form.default_branch.trim() || 'main',
        git_author_name: form.git_author_name.trim() || undefined,
        git_author_email: form.git_author_email.trim() || undefined,
        git_credential_type: form.git_credential_type || undefined,
        git_ssh_key_path: form.git_ssh_key_path.trim() || undefined,
        git_https_username: form.git_https_username.trim() || undefined,
        git_https_token: form.git_https_token.trim() || undefined,
      });
      onCreated();
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <h3 className="text-foreground font-semibold">New Project</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200"><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && <p className="text-red-400 text-sm">{error}</p>}

          {/* Basic */}
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Project name *</label>
              <input
                className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                value={form.name} onChange={(e) => set('name', e.target.value)}
                placeholder="my-project" required
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Git URL (leave empty for local-only)</label>
              <input
                className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                value={form.git_url} onChange={(e) => set('git_url', e.target.value)}
                placeholder="https://github.com/org/repo.git"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Default branch</label>
              <input
                className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                value={form.default_branch} onChange={(e) => set('default_branch', e.target.value)}
                placeholder="main"
              />
            </div>
          </div>

          {/* Git config (collapsible) */}
          <div className="border border-gray-700 rounded-lg overflow-hidden">
            <button
              type="button"
              className="w-full flex items-center justify-between px-4 py-3 text-sm text-gray-300 hover:bg-gray-700/50"
              onClick={() => setShowGit(!showGit)}
            >
              <span className="flex items-center gap-2"><Settings size={14} /> Git identity &amp; credentials</span>
              {showGit ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            {showGit && (
              <div className="px-4 pb-4 space-y-3 border-t border-gray-700">
                <p className="text-xs text-gray-500 pt-3">Optional. Overrides the machine's global git config for this project.</p>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Author name</label>
                    <input
                      className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                      value={form.git_author_name} onChange={(e) => set('git_author_name', e.target.value)}
                      placeholder="Zhang San"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Author email</label>
                    <input
                      className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                      value={form.git_author_email} onChange={(e) => set('git_author_email', e.target.value)}
                      placeholder="zhang@example.com"
                    />
                  </div>
                  <IdentityWarning name={identityName} email={identityEmail} />
                </div>

                <div>
                  <label className="block text-xs text-gray-400 mb-1">Credential type</label>
                  <select
                    className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                    value={form.git_credential_type} onChange={(e) => set('git_credential_type', e.target.value)}
                  >
                    <option value="">System default</option>
                    <option value="ssh">SSH key</option>
                    <option value="https">HTTPS token</option>
                  </select>
                </div>

                {form.git_credential_type === 'ssh' && (
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">SSH private key path</label>
                    <input
                      className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                      value={form.git_ssh_key_path} onChange={(e) => set('git_ssh_key_path', e.target.value)}
                      placeholder="/home/alice/.ssh/id_ed25519_work"
                    />
                  </div>
                )}

                {form.git_credential_type === 'https' && (
                  <div className="space-y-2">
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Username</label>
                      <input
                        className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                        value={form.git_https_username} onChange={(e) => set('git_https_username', e.target.value)}
                        placeholder="github-username"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Personal access token</label>
                      <input
                        type="password"
                        className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                        value={form.git_https_token} onChange={(e) => set('git_https_token', e.target.value)}
                        placeholder="ghp_..."
                      />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-300 hover:text-white">Cancel</button>
            <button
              type="submit"
              disabled={submitting || !form.name.trim()}
              className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-500 disabled:opacity-50"
            >
              {submitting ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Git Config Edit Modal ─────────────────────────────────────────────────────

function GitConfigModal({ project, onClose, onSaved }: { project: Project; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    git_author_name: project.git_author_name ?? '',
    git_author_email: project.git_author_email ?? '',
    git_credential_type: project.git_credential_type ?? '',
    git_ssh_key_path: project.git_ssh_key_path ?? '',
    git_https_username: project.git_https_username ?? '',
    git_https_token: project.git_https_token ?? '',
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const set = (key: keyof typeof form, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.updateProject(project.id, {
        git_author_name: form.git_author_name.trim() || undefined,
        git_author_email: form.git_author_email.trim() || undefined,
        git_credential_type: form.git_credential_type || undefined,
        git_ssh_key_path: form.git_ssh_key_path.trim() || undefined,
        git_https_username: form.git_https_username.trim() || undefined,
        git_https_token: form.git_https_token.trim() || undefined,
      });
      onSaved();
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <h3 className="text-foreground font-semibold">Git config — {project.name}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200"><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <p className="text-xs text-gray-500">Overrides the machine's global git config for this project only. Leave blank to use system default.</p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Author name</label>
              <input
                className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                value={form.git_author_name} onChange={(e) => set('git_author_name', e.target.value)}
                placeholder="Zhang San"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Author email</label>
              <input
                className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                value={form.git_author_email} onChange={(e) => set('git_author_email', e.target.value)}
                placeholder="zhang@example.com"
              />
            </div>
            <IdentityWarning name={form.git_author_name} email={form.git_author_email} />
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Credential type</label>
            <select
              className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
              value={form.git_credential_type} onChange={(e) => set('git_credential_type', e.target.value)}
            >
              <option value="">System default</option>
              <option value="ssh">SSH key</option>
              <option value="https">HTTPS token</option>
            </select>
          </div>

          {form.git_credential_type === 'ssh' && (
            <div>
              <label className="block text-xs text-gray-400 mb-1">SSH private key path</label>
              <input
                className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                value={form.git_ssh_key_path} onChange={(e) => set('git_ssh_key_path', e.target.value)}
                placeholder="/home/alice/.ssh/id_ed25519_work"
              />
            </div>
          )}

          {form.git_credential_type === 'https' && (
            <div className="space-y-2">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Username</label>
                <input
                  className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                  value={form.git_https_username} onChange={(e) => set('git_https_username', e.target.value)}
                  placeholder="github-username"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Personal access token</label>
                <input
                  type="password"
                  className="w-full bg-gray-700 text-foreground text-sm rounded px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                  value={form.git_https_token} onChange={(e) => set('git_https_token', e.target.value)}
                  placeholder="ghp_..."
                />
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-300 hover:text-white">Cancel</button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-500 disabled:opacity-50"
            >
              {submitting ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<Record<number, boolean>>({});
  const [showCreate, setShowCreate] = useState(false);
  const [editingGit, setEditingGit] = useState<Project | null>(null);
  const [showGlobalGit, setShowGlobalGit] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const list = await api.listProjects();
      setProjects(list);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  const toggleSelector = async (project: Project) => {
    setLoading((prev) => ({ ...prev, [project.id]: true }));
    try {
      await api.updateProject(project.id, { show_in_selector: !project.show_in_selector });
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading((prev) => ({ ...prev, [project.id]: false }));
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this project?')) return;
    try {
      await api.deleteProject(id);
      await refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  const statusColor: Record<string, string> = {
    ready: 'bg-green-500',
    pending: 'bg-yellow-500',
    cloning: 'bg-blue-500 animate-pulse',
    error: 'bg-red-500',
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-foreground font-semibold text-lg">Projects</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowGlobalGit(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-300 border border-gray-600 rounded hover:bg-gray-700"
            title="Global Git Config"
          >
            <Settings size={14} /> Global Git Config
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-500"
          >
            <Plus size={14} /> New project
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/20 text-red-400 px-4 py-2 rounded text-sm">
          Error: {error}
        </div>
      )}

      {projects.length === 0 ? (
        <p className="text-gray-400 text-sm">No projects yet.</p>
      ) : (
        <div className="space-y-3">
          {projects.map((p) => (
            <div key={p.id} className="bg-gray-800 rounded-lg p-4 flex items-start gap-4">
              {/* Icon */}
              <div className="mt-1 text-gray-400">
                <FolderGit2 size={20} />
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-foreground font-medium">{p.name}</span>
                  <span className={`inline-block w-2 h-2 rounded-full ${statusColor[p.status] || 'bg-gray-500'}`} title={p.status} />
                  <span className="text-xs text-gray-500 capitalize">{p.status}</span>
                  {p.has_remote ? (
                    <span className="flex items-center gap-1 text-xs text-sky-400">
                      <Globe size={12} /> Remote
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs text-gray-500">
                      <HardDrive size={12} /> Local
                    </span>
                  )}
                </div>

                {p.git_url && (
                  <p className="text-xs text-gray-500 truncate" title={p.git_url}>{p.git_url}</p>
                )}
                {p.local_path && (
                  <p className="text-xs text-gray-500 truncate" title={p.local_path}>{p.local_path}</p>
                )}
                {p.error_message && (
                  <p className="text-xs text-red-400 truncate" title={p.error_message}>{p.error_message}</p>
                )}

                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>Branch: {p.default_branch}</span>
                  {p.git_author_name && <span>Author: {p.git_author_name}</span>}
                  {p.git_credential_type && <span>Creds: {p.git_credential_type}</span>}
                  <span>Created: {new Date(p.created_at).toLocaleDateString()}</span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-3 shrink-0">
                {/* Show in selector toggle */}
                <label className="flex items-center gap-2 cursor-pointer select-none" title="Show in task project dropdown">
                  <span className="text-xs text-gray-400">Selector</span>
                  <button
                    onClick={() => toggleSelector(p)}
                    disabled={loading[p.id]}
                    className={`relative w-10 h-5 rounded-full transition-colors ${
                      p.show_in_selector ? 'bg-indigo-600' : 'bg-gray-600'
                    } ${loading[p.id] ? 'opacity-50' : ''}`}
                  >
                    <span
                      className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                        p.show_in_selector ? 'translate-x-5' : ''
                      }`}
                    />
                  </button>
                </label>

                {/* Edit git config */}
                <button
                  onClick={() => setEditingGit(p)}
                  className="p-2 text-gray-400 hover:text-indigo-400 hover:bg-gray-700 rounded transition-colors"
                  title="Edit git config"
                >
                  <Settings size={16} />
                </button>

                {/* Reclone (remote only) */}
                {p.has_remote && (
                  <button
                    onClick={async () => {
                      try {
                        await api.recloneProject(p.id);
                        await refresh();
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                    className="p-2 text-gray-400 hover:text-sky-400 hover:bg-gray-700 rounded transition-colors"
                    title="Re-clone"
                  >
                    <RotateCcw size={16} />
                  </button>
                )}

                <button
                  onClick={() => handleDelete(p.id)}
                  className="p-2 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded transition-colors"
                  title="Delete project"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && <CreateModal onClose={() => setShowCreate(false)} onCreated={refresh} />}
      {editingGit && <GitConfigModal project={editingGit} onClose={() => setEditingGit(null)} onSaved={refresh} />}
      {showGlobalGit && <GlobalGitConfigModal onClose={() => setShowGlobalGit(false)} />}
    </div>
  );
}
