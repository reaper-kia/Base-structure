import { useEffect, useState, type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { ApiError } from '../../shared/api/client';
import { ErrorMessage } from '../../shared/ui/ErrorMessage';
import { Loading } from '../../shared/ui/Loading';
import { authApi } from './api';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const [state, setState] = useState<'loading' | 'allowed' | 'denied' | 'error'>('loading');
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let active = true;
    setState('loading');
    authApi.me()
      .then((user) => active && setState(user.is_admin ? 'allowed' : 'denied'))
      .catch((error: unknown) => {
        if (!active) return;
        setState(error instanceof ApiError && (error.status === 401 || error.status === 403) ? 'denied' : 'error');
      });
    return () => { active = false; };
  }, [retryKey]);

  if (state === 'loading') return <div className="route-state"><Loading /></div>;
  if (state === 'denied') return <Navigate to="/login" replace />;
  if (state === 'error') return <div className="route-state"><ErrorMessage message="Не удалось проверить сессию" onRetry={() => setRetryKey((key) => key + 1)} /></div>;
  return children;
}
