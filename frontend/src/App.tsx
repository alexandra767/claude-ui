import { Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuthStore } from './stores/authStore';
import { useChatStore } from './stores/chatStore';
import Login from './pages/Login';
import Chat from './pages/Chat';
import Settings from './pages/Settings';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import Share from './pages/Share';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const loadFromStorage = useAuthStore((s) => s.loadFromStorage);
  const detectLocation = useChatStore((s) => s.detectLocation);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    loadFromStorage();
    detectLocation();
    setReady(true);
  }, []);

  // Don't render routes until auth state is loaded from localStorage
  if (!ready) return null;

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
      <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
      <Route path="/chat/:conversationId" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
      <Route path="/projects" element={<ProtectedRoute><Projects /></ProtectedRoute>} />
      <Route path="/projects/:projectId" element={<ProtectedRoute><ProjectDetail /></ProtectedRoute>} />
      <Route path="/share" element={<ProtectedRoute><Share /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
