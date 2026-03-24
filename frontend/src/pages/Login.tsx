import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { auth } from '../api/client';
import { Sparkles } from 'lucide-react';

export default function Login() {
  const [isSignup, setIsSignup] = useState(true);
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = isSignup
        ? await auth.signup({ email, username, password, display_name: displayName || username })
        : await auth.login({ email, password });
      setAuth(result.user, result.token);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-cream flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent/10 mb-4">
            <Sparkles className="w-8 h-8 text-accent" />
          </div>
          <h1 className="text-2xl font-semibold text-text-primary">
            {isSignup ? 'Create your account' : 'Welcome back'}
          </h1>
          <p className="text-text-secondary mt-2">
            {isSignup ? 'Start chatting with your AI assistant' : 'Sign in to continue'}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-border p-8 space-y-4">
          {error && (
            <div className="bg-red-50 text-red-600 text-sm rounded-lg p-3 border border-red-200">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-cream focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition text-text-primary"
              placeholder="you@example.com"
              required
            />
          </div>

          {isSignup && (
            <>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-border bg-cream focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition text-text-primary"
                  placeholder="johndoe"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">Display Name</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-border bg-cream focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition text-text-primary"
                  placeholder="John Doe"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-cream focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition text-text-primary"
              placeholder="••••••••"
              required
              minLength={6}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-accent text-white font-medium hover:bg-accent-hover transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Please wait...' : isSignup ? 'Create account' : 'Sign in'}
          </button>

          <div className="text-center pt-2">
            <button
              type="button"
              onClick={() => { setIsSignup(!isSignup); setError(''); }}
              className="text-sm text-accent hover:text-accent-hover transition"
            >
              {isSignup ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
            </button>
          </div>
        </form>

        <p className="text-center text-text-secondary text-xs mt-6">
          Powered by your local AI models via Ollama
        </p>
      </div>
    </div>
  );
}
