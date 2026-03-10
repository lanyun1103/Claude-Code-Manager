import { useState, useEffect } from 'react';
import { api } from '../../api/client';
import type { Project } from '../../api/client';
import { Plus } from 'lucide-react';
import { VoiceButton } from '../Voice/VoiceButton';

interface TaskFormProps {
  onCreated: () => void;
}

const NEW_PROJECT_VALUE = '__new__';

export function TaskForm({ onCreated }: TaskFormProps) {
  const [description, setDescription] = useState('');
  const [projectId, setProjectId] = useState<number | ''>('');
  const [isNewProject, setIsNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectUrl, setNewProjectUrl] = useState('');
  const [priority, setPriority] = useState(0);
  const [mode, setMode] = useState('auto');
  const [todoFilePath, setTodoFilePath] = useState('');
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);

  const loadProjects = () => {
    api.listProjects().then(setProjects).catch(() => {});
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleProjectChange = (val: string) => {
    if (val === NEW_PROJECT_VALUE) {
      setIsNewProject(true);
      setProjectId('');
    } else {
      setIsNewProject(false);
      setNewProjectName('');
      setNewProjectUrl('');
      setProjectId(val ? Number(val) : '');
    }
  };

  const canSubmit =
    (description || mode === 'loop') &&
    (mode !== 'loop' || todoFilePath) &&
    (projectId || (isNewProject && newProjectName));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    try {
      let pid = projectId || undefined;

      // Create new project first if needed
      if (isNewProject && newProjectName) {
        const project = await api.createProject({
          name: newProjectName,
          git_url: newProjectUrl || undefined,
        });
        pid = project.id;
        // Refresh project list and reset new project fields
        loadProjects();
        setIsNewProject(false);
        setNewProjectName('');
        setNewProjectUrl('');
        setProjectId(project.id);
      }

      await api.createTask({
        description: description || undefined,
        project_id: pid as number,
        priority,
        mode,
        ...(mode === 'loop' ? { todo_file_path: todoFilePath } : {}),
      });
      setDescription('');
      setPriority(0);
      onCreated();
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-gray-800 rounded-lg p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-300">New Task</h3>
      <div className="flex gap-2">
        <textarea
          className="flex-1 bg-gray-700 text-foreground rounded px-3 py-2 text-sm h-24 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder={mode === 'loop' ? 'Background / context (optional)' : 'Prompt / Description (this will be sent to Claude Code)'}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required={mode !== 'loop'}
        />
        <VoiceButton onTranscribed={(text) => setDescription((prev) => prev ? prev + ' ' + text : text)} />
      </div>
      <div className="space-y-2">
        <select
          className="w-full bg-gray-700 text-foreground rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          value={isNewProject ? NEW_PROJECT_VALUE : projectId}
          onChange={(e) => handleProjectChange(e.target.value)}
        >
          <option value="">Select project...</option>
          {projects.filter((p) => p.show_in_selector).map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} {p.status !== 'ready' ? `(${p.status})` : ''}
            </option>
          ))}
          <option value={NEW_PROJECT_VALUE}>+ New project</option>
        </select>
        {isNewProject && (
          <div className="flex gap-2">
            <input
              className="flex-1 bg-gray-700 text-foreground rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Project name (required)"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              required
            />
            <input
              className="flex-1 bg-gray-700 text-foreground rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Remote repo URL (optional)"
              value={newProjectUrl}
              onChange={(e) => setNewProjectUrl(e.target.value)}
            />
          </div>
        )}
      </div>
      <div className="flex items-center gap-3 flex-wrap">
        <label className="text-sm text-gray-400">Priority:</label>
        <input
          type="number"
          className="w-20 bg-gray-700 text-foreground rounded px-2 py-1 text-sm"
          value={priority}
          onChange={(e) => setPriority(Number(e.target.value))}
        />
        <label className="text-sm text-gray-400 ml-2">Mode:</label>
        <select
          className="bg-gray-700 text-foreground rounded px-2 py-1 text-sm"
          value={mode}
          onChange={(e) => setMode(e.target.value)}
        >
          <option value="auto">Auto (direct execute)</option>
          <option value="plan">Plan (review first)</option>
          <option value="loop">Loop (todo list)</option>
        </select>
        {mode === 'loop' && (
          <input
            className="flex-1 min-w-0 bg-gray-700 text-foreground rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Todo file path (e.g. TODO.md)"
            value={todoFilePath}
            onChange={(e) => setTodoFilePath(e.target.value)}
            required
          />
        )}
        <button
          type="submit"
          disabled={loading || !canSubmit}
          className="ml-auto flex items-center gap-1 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
        >
          <Plus size={16} />
          {loading ? 'Creating...' : 'Create Task'}
        </button>
      </div>
    </form>
  );
}
