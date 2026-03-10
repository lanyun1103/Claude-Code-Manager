import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { Project } from '../api/client';
import { Trash2, RotateCcw, FolderGit2, Globe, HardDrive } from 'lucide-react';

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<Record<number, boolean>>({});

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
      <h2 className="text-foreground font-semibold text-lg">Projects</h2>

      {error && (
        <div className="bg-red-500/20 text-red-400 px-4 py-2 rounded text-sm">
          Error: {error}
        </div>
      )}

      {projects.length === 0 ? (
        <p className="text-gray-400 text-sm">No projects yet. Create one from the Tasks page.</p>
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
    </div>
  );
}
