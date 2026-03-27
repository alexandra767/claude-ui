import { AlertCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useToastStore } from '../stores/toastStore';

const iconMap = {
  error: { Icon: AlertCircle, border: 'border-l-red-500', bg: 'bg-red-500/10', text: 'text-red-500' },
  warning: { Icon: AlertTriangle, border: 'border-l-amber-500', bg: 'bg-amber-500/10', text: 'text-amber-500' },
  info: { Icon: Info, border: 'border-l-blue-500', bg: 'bg-blue-500/10', text: 'text-blue-500' },
};

export default function Toast() {
  const { toasts, removeToast } = useToastStore();
  if (!toasts.length) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => {
        const { Icon, border, bg, text } = iconMap[t.type];
        return (
          <div
            key={t.id}
            className={`flex items-start gap-3 px-4 py-3 rounded-lg border-l-4 ${border} ${bg} bg-input-bg shadow-lg backdrop-blur-sm animate-[slideIn_0.2s_ease-out]`}
          >
            <Icon className={`w-5 h-5 shrink-0 mt-0.5 ${text}`} />
            <span className="flex-1 text-sm text-text-primary font-sans">{t.message}</span>
            <button
              onClick={() => removeToast(t.id)}
              className="shrink-0 p-0.5 rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4 text-text-secondary" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
