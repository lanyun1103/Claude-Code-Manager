import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import type { Task, Project, TagItem } from '../api/client';
import { TaskForm } from '../components/Tasks/TaskForm';
import { TaskList } from '../components/Tasks/TaskList';
import { PlanPanel } from '../components/PlanReview/PlanPanel';
import { ChatView } from '../components/Chat/ChatView';
import { LoopChatView } from '../components/Chat/LoopChatView';
import { ProjectSelect } from '../components/ProjectSelect';
import { resolveTagColor } from '../components/TagColors';

export function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [allTasks, setAllTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [filter, setFilter] = useState<string>('');
  const [tagFilter, setTagFilter] = useState<string>('');
  const [projectFilter, setProjectFilter] = useState<number | undefined>(undefined);
  const [starredFilter, setStarredFilter] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [tagItems, setTagItems] = useState<TagItem[]>([]);
  const [chatTask, setChatTask] = useState<Task | null>(null);
  const chatTaskRef = useRef<Task | null>(null);
  chatTaskRef.current = chatTask;

  const refresh = useCallback(async () => {
    try {
      const [filtered, all, projs, tags] = await Promise.all([
        api.listTasks(filter || undefined, showArchived, projectFilter, starredFilter || undefined),
        api.listTasks(undefined, showArchived),
        api.listProjects(),
        api.listTags(),
      ]);
      setTasks(filtered);
      setAllTasks(all);
      setProjects(projs);
      setTagItems(tags);
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

  const filters = ['', 'pending', 'in_progress', 'executing', 'plan_review', 'completed', 'failed'];

  // Collect all unique tags from loaded projects
  const allProjectTags = Array.from(new Set(projects.flatMap((p) => p.tags))).sort();

  // Build tag color map
  const tagColorMap: Record<string, string> = {};
  for (const t of tagItems) tagColorMap[t.name] = t.color;

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
        {allProjectTags.length > 0 && allProjectTags.map((tag) => {
          const c = resolveTagColor(tag, tagColorMap[tag]);
          const active = tagFilter === tag;
          return (
            <button
              key={tag}
              onClick={() => {
                const next = active ? '' : tag;
                setTagFilter(next);
                if (next && projectFilter !== undefined) {
                  const filtered = projects.filter((p) => p.tags.includes(next));
                  if (!filtered.some((p) => p.id === projectFilter)) {
                    setProjectFilter(undefined);
                  }
                }
              }}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors border ${c.bg} ${c.text} ${c.border} ${
                active ? 'opacity-100 ring-1 ring-white/30' : 'opacity-50 hover:opacity-80'
              }`}
            >
              {tag}
            </button>
          );
        })}

        <ProjectSelect
          projects={tagFilteredProjects}
          value={projectFilter}
          onChange={(v) => setProjectFilter(v ? Number(v) : undefined)}
          placeholder="All Projects"
          tagColorMap={tagColorMap}
        />

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

      <TaskList
        tasks={tagFilter
          ? tasks.filter((t) => {
              if (!t.project_id) return false;
              const proj = projects.find((p) => p.id === t.project_id);
              return proj ? proj.tags.includes(tagFilter) : false;
            })
          : tasks}
        projects={projects}
        onRefresh={refresh}
        onOpenChat={(t) => {
          setChatTask(t);
          if (t.has_unread) {
            api.markTaskRead(t.id).catch(() => {});
          }
        }}
      />

      {chatTask && chatTask.mode === 'loop' && (
        <LoopChatView task={chatTask} onBack={() => setChatTask(null)} />
      )}
      {chatTask && chatTask.mode !== 'loop' && (
        <ChatView task={chatTask} projects={projects} onBack={() => setChatTask(null)} />
      )}
    </div>
  );
}
