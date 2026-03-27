import { useState, useEffect, useRef } from 'react';

type Status = 'connected' | 'reconnecting' | 'disconnected';

export default function ConnectionStatus() {
  const [status, setStatus] = useState<Status>('connected');
  const failCount = useRef(0);

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('/api/health', { signal: AbortSignal.timeout(5000) });
        if (res.ok) {
          failCount.current = 0;
          setStatus('connected');
        } else throw new Error();
      } catch {
        failCount.current++;
        setStatus(failCount.current >= 3 ? 'disconnected' : 'reconnecting');
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  const colors = {
    connected: 'bg-green-500',
    reconnecting: 'bg-yellow-500',
    disconnected: 'bg-red-500',
  };

  return (
    <div className="flex items-center gap-1.5" title={status}>
      <div className={`w-2 h-2 rounded-full ${colors[status]}`} />
      {status !== 'connected' && (
        <span className="text-xs text-text-secondary">
          {status === 'reconnecting' ? 'Reconnecting...' : 'Disconnected'}
        </span>
      )}
    </div>
  );
}
