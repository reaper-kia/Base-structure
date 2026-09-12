import { useEffect, useState } from 'react';
import { api } from '../../shared/api';
import { useDocumentStore } from '../../shared/store/documentStore';

export function DevPanel() {
  const devState = useDocumentStore((state) => state.devState);
  const loadDevState = useDocumentStore((state) => state.loadDevState);
  const setAiForceFailure = useDocumentStore((state) => state.setAiForceFailure);
  const [templateBroken, setTemplateBroken] = useState(false);

  useEffect(() => {
    loadDevState();
    api.getTemplateBroken().then(setTemplateBroken);
  }, [loadDevState]);

  return (
    <div className="max-w-xl">
      <h1
        className="text-xl font-bold mb-2"
        style={{ fontFamily: 'var(--font-serif)', color: 'var(--foreground)' }}
      >
        Dev-панель
      </h1>
      <p className="text-sm mb-6" style={{ color: 'var(--muted-foreground)' }}>
        Инструменты для эксперта: сломайте сервис и убедитесь, что черновик
        переживает любую ошибку.
      </p>

      <div
        className="p-4 space-y-4"
        style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
        }}
      >
        <div>
          <label className="flex items-center gap-3 cursor-pointer select-none">
            <input
              type="checkbox"
              data-testid="break-ai-toggle"
              checked={devState?.ai_force_failure ?? false}
              onChange={(event) => setAiForceFailure(event.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm font-medium" style={{ color: 'var(--foreground)' }}>
              Имитировать отказ ИИ
            </span>
          </label>
          <p className="mt-2 text-xs ml-7" style={{ color: 'var(--muted-foreground)' }}>
            Демонстрационный режим. Имитирует недоступность ИИ-компонента,
            чтобы убедиться, что черновик сохраняется при ошибке.
          </p>
        </div>

        <label className="flex items-center gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            data-testid="break-template-toggle"
            checked={templateBroken}
            onChange={(event) => {
              setTemplateBroken(event.target.checked);
              api.setTemplateBroken(event.target.checked);
            }}
            className="w-4 h-4"
          />
          <span className="text-sm" style={{ color: 'var(--foreground)' }}>
            Демо: повредить шаблон «modern»
          </span>
        </label>

        {devState && (
          <dl
            className="text-xs space-y-1"
            style={{ color: 'var(--muted-foreground)' }}
          >
            <div>ml_service: {devState.ml_service_url}</div>
            <div>ML доступен: {devState.ml_reachable ? 'да' : 'нет'}</div>
            <div>Модель: {devState.model_version}</div>
            <div>Шаблоны: {devState.templates_loaded.join(', ')}</div>
          </dl>
        )}
      </div>
    </div>
  );
}