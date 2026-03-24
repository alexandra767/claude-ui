import { useEffect } from 'react';
import { useAuthStore } from '../stores/authStore';

export function useTheme() {
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    const theme = user?.theme || localStorage.getItem('theme') || 'system';
    applyTheme(theme);
  }, [user?.theme]);
}

export function applyTheme(theme: string) {
  localStorage.setItem('theme', theme);
  const html = document.documentElement;

  if (theme === 'dark') {
    html.classList.add('dark');
  } else if (theme === 'light') {
    html.classList.remove('dark');
  } else {
    // System preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      html.classList.add('dark');
    } else {
      html.classList.remove('dark');
    }
  }
}
