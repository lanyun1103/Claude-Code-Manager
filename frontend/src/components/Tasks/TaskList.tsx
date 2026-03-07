import { useMemo } from 'react';
import { api } from '../../api/client';
import type { Task, Project } from '../../api/client';
import { Trash2, RotateCcw, XCircle, MessageCircle } from 'lucide-react';

interface TaskListProps {
  tasks: Task[];
  projects: Project[];
  onRefresh: () => void;
  onOpenChat: (task: Task) => void;
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-500',
  in_progress: 'bg-blue-500',
  executing: 'bg-blue-400 animate-pulse',
  plan_review: 'bg-purple-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-gray-500',
};

export function TaskList({ tasks, projects, onRefresh, onOpenChat }: TaskListProps) {
  const projectMap = useMemo(() => {
    const map: Record<number, string> = {};
    for (const p of projects) map[p.id] = p.name;
    return map;
  }, [projects]);
  const handleDelete = async (id: number) => {
    await api.deleteTask(id);
    onRefresh();
  };
  const handleCancel = async (id: number) => {
    await api.cancelTask(id);
    onRefresh();
  };
  const handleRetry = async (id: number) => {
    await api.retryTask(id);
    onRefresh();
  };
  if (tasks.length === 0) {
    return <p className="text-gray-500 text-sm text-center py-8">No tasks yet</p>;
  }

  return (
    <div className="space-y-2">
      {tasks.map((t) => (
        <div key={t.id} className="bg-gray-800 rounded-lg p-3 flex items-start gap-3">
          <span className={`mt-1 w-2.5 h-2.5 rounded-full shrink-0 ${statusColors[t.status] || 'bg-gray-500'}`} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">#{t.id}</span>
              {t.project_id && projectMap[t.project_id] && (
                <span className="text-xs bg-emerald-600/30 text-emerald-300 px-1.5 rounded font-medium">{projectMap[t.project_id]}</span>
              )}
              {t.priority > 0 && (
                <span className="text-xs bg-indigo-600/30 text-indigo-300 px-1.5 rounded">P{t.priority}</span>
              )}
              <span className="text-xs text-gray-500 capitalize">{t.status.replace('_', ' ')}</span>
            </div>
            <p className="text-foreground text-sm mt-0.5 line-clamp-2">
              {t.mode === 'loop'
                ? (t.description || <span className="text-gray-500 italic">{t.todo_file_path}</span>)
                : t.description}
            </p>
            {t.mode === 'loop' && t.loop_progress && (
              <p className="text-indigo-400 text-xs mt-0.5">⟳ {t.loop_progress}</p>
            )}
            {t.target_repo && (
              <p className="text-gray-600 text-xs mt-0.5 truncate">{t.target_repo}</p>
            )}
            {t.error_message && (
              <p className="text-red-400 text-xs mt-1">{t.error_message}</p>
            )}
          </div>
          <div className="flex gap-1 shrink-0">
            {t.session_id && (
              <button
                onClick={() => onOpenChat(t)}
                className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30"
                title="Chat"
              >
                <MessageCircle size={14} /> Chat
              </button>
            )}
            {['in_progress', 'executing'].includes(t.status) && (
              <button onClick={() => handleCancel(t.id)} className="p-1.5 text-gray-400 hover:text-yellow-400" title="Cancel">
                <XCircle size={16} />
              </button>
            )}
            {t.status === 'failed' && (
              <button onClick={() => handleRetry(t.id)} className="p-1.5 text-gray-400 hover:text-blue-400" title="Retry">
                <RotateCcw size={16} />
              </button>
            )}
            {['pending', 'failed', 'cancelled'].includes(t.status) && (
              <button onClick={() => handleDelete(t.id)} className="p-1.5 text-gray-400 hover:text-red-400" title="Delete">
                <Trash2 size={16} />
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
