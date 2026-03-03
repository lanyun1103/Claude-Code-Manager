interface HeaderProps {
  currentPage: string;
  onNavigate: (page: string) => void;
}

export function Header({ currentPage, onNavigate }: HeaderProps) {
  const pages = [
    { key: 'dashboard', label: 'Dashboard' },
    { key: 'tasks', label: 'Tasks' },
  ];

  return (
    <header className="bg-gray-900 border-b border-gray-700 px-4 py-2 pt-[max(0.5rem,env(safe-area-inset-top))] flex items-center gap-3 flex-wrap">
      <h1 className="text-base font-bold text-white">Claude Manager</h1>
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
    </header>
  );
}
