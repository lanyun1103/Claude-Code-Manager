import { useState, useEffect, useRef } from 'react';
import { api } from '../../api/client';
import type { ChatMessage, Task } from '../../api/client';
import { useWebSocket } from '../../hooks/useWebSocket';
import { Send, ArrowLeft, Loader2, ChevronDown, ChevronRight } from 'lucide-react';

interface ChatViewProps {
  task: Task;
  onBack: () => void;
}

export function ChatView({ task, onBack }: ChatViewProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { lastMessage } = useWebSocket([`task:${task.id}`]);

  // Load chat history
  useEffect(() => {
    api.getTaskChatHistory(task.id).then((msgs) => {
      // Filter out empty text messages (partial streaming chunks), keep tool/thinking/system events
      setMessages(msgs.filter((m) =>
        !((m.event_type === 'message' || m.event_type === 'result') && !m.content)
      ));
    }).catch(() => {});
  }, [task.id]);

  // Handle real-time WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;
    const msg = lastMessage as { channel?: string; data?: Record<string, unknown> };
    if (msg.channel !== `task:${task.id}` || !msg.data) return;

    const eventType = msg.data.event_type as string;

    if (eventType === 'process_exit') {
      setSending(false);
      return;
    }

    // Only show meaningful events in chat (skip user_message - already added optimistically)
    const showTypes = ['message', 'result', 'tool_use', 'tool_result', 'system_init', 'system_event', 'thinking'];
    if (!showTypes.includes(eventType)) return;

    const content = (msg.data.content as string) || null;
    // Skip empty assistant messages (partial streaming chunks with no text)
    if ((eventType === 'message' || eventType === 'result') && !content) return;

    const entry: ChatMessage = {
      id: Date.now() + Math.random(),
      role: (msg.data.role as string) || 'assistant',
      event_type: eventType,
      content,
      tool_name: (msg.data.tool_name as string) || null,
      tool_input: (msg.data.tool_input as string) || null,
      tool_output: (msg.data.tool_output as string) || null,
      is_error: (msg.data.is_error as boolean) || false,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, entry]);
  }, [lastMessage, task.id]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setInput('');
    setSending(true);
    setError(null);

    // Optimistically add user message
    const userMsg: ChatMessage = {
      id: Date.now(),
      role: 'user',
      event_type: 'user_message',
      content: text,
      tool_name: null,
      tool_input: null,
      tool_output: null,
      is_error: false,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      await api.sendTaskChat(task.id, text);
    } catch (e) {
      setSending(false);
      setError(String(e));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-950 flex flex-col z-50">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 bg-gray-900">
        <button onClick={onBack} className="text-gray-400 hover:text-white">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-medium text-sm truncate">{task.title}</h3>
          <p className="text-xs text-gray-500">
            Task #{task.id} · {task.session_id ? 'Session active' : 'No session yet'}
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-600 mt-20">
            <p className="text-lg mb-2">Chat with this task</p>
            <p className="text-sm">
              {task.session_id
                ? 'Send a follow-up message to continue the conversation'
                : 'This task has no session yet. Run it first via Ralph Loop or manually.'}
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {sending && (
          <div className="flex gap-2 items-center text-gray-500 text-sm px-3">
            <Loader2 size={14} className="animate-spin" />
            <span>Claude is thinking...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mb-2 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="border-t border-gray-800 bg-gray-900 p-3">
        <div className="flex gap-2 items-end max-w-3xl mx-auto">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              !task.session_id
                ? 'Run the task first to start a session...'
                : sending
                  ? 'Waiting for response...'
                  : 'Type a follow-up message...'
            }
            disabled={sending || !task.session_id}
            rows={1}
            className="flex-1 bg-gray-800 text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none disabled:opacity-50 max-h-32"
            style={{ minHeight: '40px' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending || !task.session_id}
            className="p-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

function CollapsibleContent({ content, maxLines = 5 }: { content: string; maxLines?: number }) {
  const [expanded, setExpanded] = useState(false);
  const lines = content.split('\n');
  const shouldCollapse = lines.length > maxLines;

  if (!shouldCollapse) {
    return (
      <pre className="text-gray-300 whitespace-pre-wrap text-xs overflow-x-auto">{content}</pre>
    );
  }

  return (
    <div>
      <pre className={`text-gray-300 whitespace-pre-wrap text-xs overflow-x-auto ${expanded ? 'max-h-96 overflow-y-auto' : 'max-h-28 overflow-hidden'}`}>
        {content}
      </pre>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 mt-1"
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {expanded ? 'Collapse' : `Show all (${lines.length} lines)`}
      </button>
    </div>
  );
}

function formatToolInput(input: string): string {
  try {
    const parsed = JSON.parse(input);
    // For common tools, show a readable format
    if (parsed.command) return parsed.command; // Bash
    if (parsed.file_path && parsed.old_string !== undefined) {
      // Edit tool
      return `File: ${parsed.file_path}\n--- old ---\n${parsed.old_string}\n+++ new +++\n${parsed.new_string}`;
    }
    if (parsed.file_path && parsed.content !== undefined) {
      // Write tool
      return `File: ${parsed.file_path}\n${parsed.content}`;
    }
    if (parsed.file_path) return `File: ${parsed.file_path}`; // Read
    if (parsed.pattern) return `Pattern: ${parsed.pattern}${parsed.path ? ` in ${parsed.path}` : ''}`; // Grep/Glob
    return JSON.stringify(parsed, null, 2);
  } catch {
    return input;
  }
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  const isTool = message.event_type === 'tool_use' || message.event_type === 'tool_result';

  if (isTool) {
    const isToolUse = message.event_type === 'tool_use';
    const icon = isToolUse ? '🔧' : '📋';
    const label = isToolUse ? message.tool_name || 'tool_use' : message.tool_name || 'tool_result';
    const borderColor = message.is_error ? 'border-red-500/30' : 'border-gray-700/50';

    // Determine the content to show
    let detail: string | null = null;
    if (isToolUse && message.tool_input) {
      detail = formatToolInput(message.tool_input);
    } else if (!isToolUse && (message.tool_output || message.content)) {
      detail = message.tool_output || message.content;
    } else if (message.content) {
      detail = message.content;
    }

    return (
      <div className={`mx-4 px-3 py-2 bg-gray-800/50 rounded text-xs border ${borderColor}`}>
        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">{icon}</span>
          <span className="text-blue-400 font-medium">{label}</span>
        </div>
        {detail && (
          <div className="mt-1.5">
            <CollapsibleContent content={detail} />
          </div>
        )}
      </div>
    );
  }

  if (message.event_type === 'thinking') {
    return (
      <div className="mx-4 px-3 py-2 bg-gray-800/30 rounded text-xs border border-gray-700/30">
        <div className="flex items-center gap-1.5 text-gray-500">
          <span>💭</span>
          <span className="font-medium">Thinking</span>
        </div>
        {message.content && (
          <div className="mt-1.5">
            <CollapsibleContent content={message.content} maxLines={3} />
          </div>
        )}
      </div>
    );
  }

  if (message.event_type === 'system_init' || message.event_type === 'process_exit' || message.event_type === 'system_event') {
    const label = message.event_type === 'system_init'
      ? '— Session started —'
      : message.event_type === 'process_exit'
        ? '— Done —'
        : `— ${message.content || 'system'} —`;
    return (
      <div className="text-center text-xs text-gray-600 py-1">
        {label}
      </div>
    );
  }

  if (message.is_error) {
    return (
      <div className="mx-4 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
        {message.content}
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
          isUser
            ? 'bg-indigo-600 text-white rounded-br-md'
            : 'bg-gray-800 text-gray-200 rounded-bl-md'
        }`}
      >
        {message.content || ''}
      </div>
    </div>
  );
}
