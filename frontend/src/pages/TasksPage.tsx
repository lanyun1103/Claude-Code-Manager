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
  const [tagFilter, setTagFilter] = useState<string>('');
  const [projectFilter, setProjectFilter] = useState<number | undefined>(undefined);
  const [starredFilter, setStarredFilter] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [chatTask, setChatTask] = useState<Task | null>(null);
  const chatTaskRef = useRef<Task | null>(null);
  chatTaskRef.current = chatTask;

  const refresh = useCallback(async () => {
    try {
      const [filtered, all, projs] = await Promise.all([
        api.listTasks(filter || undefined, showArchived, projectFilter, starredFilter || undefined),
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
  }, [filter, showArchived, projectFilter, starredFilter]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  const filters = ['', 'pending', 'in_progress', 'plan_review', 'completed', 'failed'];

  // Collect all unique tags from loaded projects
  const allProjectTags = Array.from(new Set(projects.flatMap((p) => p.tags))).sort();

  // Projects filtered by tag (for the project dropdown)
  const tagFilteredProjects = tagFilter
    ? projects.filter((p) => p.tags.includes(tagFilter))
    : projects;

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

        <span className="w-px h-5 bg-gray-700 mx-1" />

        {/* Tag filter */}
        {allProjectTags.length > 0 && (
          <select
            value={tagFilter}
            onChange={(e) => {
              setTagFilter(e.target.value);
              // Clear project filter if it won't be in the new tag-filtered list
              if (e.target.value && projectFilter !== undefined) {
                const filtered = projects.filter((p) => p.tags.includes(e.target.value));
                if (!filtered.some((p) => p.id === projectFilter)) {
                  setProjectFilter(undefined);
                }
              }
            }}
            className="px-2 py-1 rounded text-xs font-medium bg-gray-800 text-gray-400 border-none outline-none cursor-pointer hover:bg-gray-700 transition-colors"
          >
            <option value="">All Tags</option>
            {allProjectTags.map((tag) => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
        )}

        <select
          value={projectFilter ?? ''}
          onChange={(e) => setProjectFilter(e.target.value ? Number(e.target.value) : undefined)}
          className="px-2 py-1 rounded text-xs font-medium bg-gray-800 text-gray-400 border-none outline-none cursor-pointer hover:bg-gray-700 transition-colors"
        >
          <option value="">All Projects</option>
          {tagFilteredProjects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>

        <button
          onClick={() => setStarredFilter(!starredFilter)}
          className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
            starredFilter
              ? 'bg-yellow-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          ★ Starred
        </button>
        <button
          onClick={() => setShowArchived(!showArchived)}
          className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
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
