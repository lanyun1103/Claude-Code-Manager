import { useState } from 'react';
import { Sun, Moon } from 'lucide-react';
import { isCapacitor } from '../../config/server';
import { getTheme, toggleTheme } from '../../config/theme';

interface HeaderProps {
  currentPage: string;
  onNavigate: (page: string) => void;
}

export function Header({ currentPage, onNavigate }: HeaderProps) {
  const [theme, setTheme] = useState(getTheme());

  const pages = [
    { key: 'dashboard', label: 'Dashboard' },
    { key: 'tasks', label: 'Tasks' },
    ...(isCapacitor() ? [{ key: 'server', label: 'Server' }] : []),
  ];

  const handleToggleTheme = () => {
    const next = toggleTheme();
    setTheme(next);
  };

  return (
    <header className="bg-gray-900 border-b border-gray-700 px-4 py-2 pt-[max(0.5rem,env(safe-area-inset-top))] flex items-center gap-3 flex-wrap">
      <h1 className="text-base font-bold text-foreground">Claude Manager</h1>
      <nav className="flex gap-2">
        {pages.map((p) => (
          <button
            key={p.key}
            onClick={() => onNavigate(p.key)}
            className={`px-4 py-2 min-h-[44px] rounded text-sm font-medium transition-colors ${
              currentPage === p.key
                ? 'bg-indigo-600 text-white'
                : 'text-gray-300 hover:bg-gray-800'
            }`}
          >
            {p.label}
          </button>
        ))}
      </nav>
      <button
        onClick={handleToggleTheme}
        className="ml-auto p-2 rounded text-gray-400 hover:text-foreground hover:bg-gray-800 transition-colors"
        title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      >
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>
    </header>
  );
}
