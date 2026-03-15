import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import type { Task, Project } from '../api/client';
import { TaskForm } from '../components/Tasks/TaskForm';
import { TaskList } from '../components/Tasks/TaskList';
import { PlanPanel } from '../components/PlanReview/PlanPanel';
import { ChatView } from '../components/Chat/ChatView';
import { LoopChatView } from '../components/Chat/LoopChatView';

export function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [allTasks, setAllTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [filter, setFilter] = useState<string>('');
  const [showArchived, setShowArchived] = useState(false);
  const [chatTask, setChatTask] = useState<Task | null>(null);
  const chatTaskRef = useRef<Task | null>(null);
  chatTaskRef.current = chatTask;

  const refresh = useCallback(async () => {
    try {
      const [filtered, all, projs] = await Promise.all([
        api.listTasks(filter || undefined, showArchived),
        api.listTasks(undefined, showArchived),
        api.listProjects(),
      ]);
      setTasks(filtered);
      setAllTasks(all);
      setProjects(projs);
      // Update chatTask if it's open (to get latest session_id etc.)
      const current = chatTaskRef.current;
      if (current) {
        const updated = all.find((t) => t.id === current.id);
        if (updated) setChatTask(updated);
      }
    } catch (e) {
      console.error('Failed to load tasks:', e);
    }
  }, [filter, showArchived]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  const filters = ['', 'pending', 'in_progress', 'plan_review', 'completed', 'failed'];

  return (
    <div className="space-y-4">
      <TaskForm onCreated={refresh} />

      <PlanPanel tasks={allTasks} onRefresh={refresh} />

      <div className="flex gap-2 flex-wrap items-center">
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              filter === f
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            {f || 'All'}
          </button>
        ))}
        <button
          onClick={() => setShowArchived(!showArchived)}
          className={`px-3 py-1 rounded text-xs font-medium transition-colors ml-2 ${
            showArchived
              ? 'bg-amber-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          Archived
        </button>
      </div>

      <TaskList tasks={tasks} projects={projects} onRefresh={refresh} onOpenChat={(t) => setChatTask(t)} />

      {chatTask && chatTask.mode === 'loop' && (
        <LoopChatView task={chatTask} onBack={() => setChatTask(null)} />
      )}
      {chatTask && chatTask.mode !== 'loop' && (
        <ChatView task={chatTask} onBack={() => setChatTask(null)} />
      )}
    </div>
  );
}
