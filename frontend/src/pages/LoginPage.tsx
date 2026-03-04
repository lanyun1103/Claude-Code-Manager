import { useState } from 'react';
import { setToken } from '../api/client';
import { getApiBase } from '../config/server';

interface LoginPageProps {
  onLogin: () => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [token, setTokenValue] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${getApiBase()}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
      });
      if (res.ok) {
        setToken(token);
        onLogin();
      } else {
        setError('Invalid token');
      }
    } catch {
      setError('Connection failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <form onSubmit={handleSubmit} className="bg-gray-800 rounded-lg p-6 w-full max-w-sm space-y-4">
        <h1 className="text-foreground text-lg font-bold text-center">Claude Code Manager</h1>
        <p className="text-gray-400 text-sm text-center">Enter your access token</p>
        <input
          type="password"
          className="w-full bg-gray-700 text-foreground rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="Token"
          value={token}
          onChange={(e) => setTokenValue(e.target.value)}
          autoFocus
          required
        />
        {error && <p className="text-red-400 text-xs">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2 rounded text-sm font-medium disabled:opacity-50"
        >
          {loading ? 'Verifying...' : 'Login'}
        </button>
      </form>
    </div>
  );
}
