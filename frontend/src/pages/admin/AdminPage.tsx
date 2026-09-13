import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowLeft,
  FileCheck2,
  FilePlus2,
  KeyRound,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import { api } from '../../shared/api';
import type {
  Template,
  TemplateUploadResult,
} from '../../shared/api/types';
import { Banner } from '../../shared/ui/Banner';
import { Button } from '../../shared/ui/Button';
import { ThemeToggle } from '../../shared/ui/ThemeToggle';

const ADMIN_TOKEN_KEY = 'doc3-admin-token';
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

function readSavedToken(): string {
  try {
    return sessionStorage.getItem(ADMIN_TOKEN_KEY) ?? '';
  } catch {
    return '';
  }
}

function saveToken(token: string): void {
  try {
    sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
  } catch {
    // sessionStorage может быть недоступен в приватном режиме.
  }
}

function clearSavedToken(): void {
  try {
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
  } catch {
    // Токен всё равно удаляется из состояния текущей страницы.
  }
}

function validateFile(file: File): string | null {
  if (!file.name.toLowerCase().endsWith('.docx')) {
    return 'Выберите файл с расширением .docx';
  }
  if (file.size === 0) {
    return 'Файл пуст';
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return 'Размер DOCX не должен превышать 10 МБ';
  }
  return null;
}

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : 'Не удалось выполнить запрос';
}

export function AdminPage() {
  const [token, setToken] = useState(readSavedToken);
  const [file, setFile] = useState<File | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploaded, setUploaded] = useState<TemplateUploadResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadTemplates = useCallback(async () => {
    setListError(null);
    setLoadingTemplates(true);
    try {
      setTemplates(await api.getTemplates());
    } catch (error) {
      setListError(errorMessage(error));
    } finally {
      setLoadingTemplates(false);
    }
  }, []);

  useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  async function handleUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUploadError(null);
    setUploaded(null);

    const normalizedToken = token.trim();
    if (!normalizedToken) {
      setUploadError('Введите ключ администратора');
      return;
    }
    if (!file) {
      setUploadError('Выберите DOCX-файл');
      return;
    }
    const validationError = validateFile(file);
    if (validationError) {
      setUploadError(validationError);
      return;
    }

    setUploading(true);
    try {
      const result = await api.uploadTemplate(file, normalizedToken);
      saveToken(normalizedToken);
      setUploaded(result);
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      await loadTemplates();
    } catch (error) {
      setUploadError(errorMessage(error));
    } finally {
      setUploading(false);
    }
  }

  function forgetToken() {
    clearSavedToken();
    setToken('');
    setUploaded(null);
  }

  const availableCount = templates.filter(
    (template) => template.available
  ).length;

  return (
    <div
      className="min-h-screen"
      style={{ background: 'var(--background)', color: 'var(--foreground)' }}
    >
      <header
        className="border-b"
        style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
      >
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-4 flex items-center justify-between gap-4">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm font-semibold"
            style={{ color: 'var(--primary)' }}
          >
            <ArrowLeft size={18} />
            К конструктору
          </Link>
          <div className="flex items-center gap-3">
            <span
              className="hidden sm:inline text-xs"
              style={{ color: 'var(--muted-foreground)' }}
            >
              Управление шаблонами
            </span>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 md:px-6 py-8 md:py-12">
        <section className="mb-8">
          <div
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold mb-4"
            style={{
              background: 'var(--secondary)',
              color: 'var(--primary)',
            }}
          >
            <ShieldCheck size={16} />
            Административный раздел
          </div>
          <h1 className="text-3xl md:text-4xl font-bold mb-3">
            Шаблоны документов
          </h1>
          <p
            className="max-w-2xl text-sm leading-6"
            style={{ color: 'var(--muted-foreground)' }}
          >
            Загрузите DOCX, и сервис извлечёт параметры оформления. Ключ
            передаётся только в защищённый запрос и хранится до закрытия вкладки.
          </p>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] gap-6 items-start">
          <section
            className="p-5 md:p-6"
            style={{
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
            }}
          >
            <div className="flex items-start gap-3 mb-6">
              <span
                className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: 'var(--secondary)', color: 'var(--primary)' }}
              >
                <FilePlus2 size={21} />
              </span>
              <div>
                <h2 className="font-bold">Добавить шаблон</h2>
                <p
                  className="text-xs mt-1"
                  style={{ color: 'var(--muted-foreground)' }}
                >
                  Поддерживается DOCX размером до 10 МБ.
                </p>
              </div>
            </div>

            <form className="space-y-5" onSubmit={handleUpload}>
              <div>
                <div className="flex items-center justify-between gap-3 mb-2">
                  <label
                    htmlFor="admin-token"
                    className="text-sm font-semibold inline-flex items-center gap-2"
                  >
                    <KeyRound size={16} /> Ключ администратора
                  </label>
                  {token && (
                    <button
                      type="button"
                      className="text-xs underline"
                      style={{ color: 'var(--muted-foreground)' }}
                      onClick={forgetToken}
                    >
                      Забыть ключ
                    </button>
                  )}
                </div>
                <input
                  id="admin-token"
                  type="password"
                  autoComplete="off"
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                  className="field__control w-full"
                  placeholder="Введите ADMIN_TOKEN"
                />
              </div>

              <div>
                <label
                  htmlFor="template-file"
                  className="block text-sm font-semibold mb-2"
                >
                  DOCX-файл
                </label>
                <input
                  ref={fileInputRef}
                  id="template-file"
                  type="file"
                  accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  className="block w-full text-sm"
                  onChange={(event) => {
                    setFile(event.target.files?.[0] ?? null);
                    setUploadError(null);
                    setUploaded(null);
                  }}
                />
                {file && (
                  <p
                    className="text-xs mt-2"
                    style={{ color: 'var(--muted-foreground)' }}
                  >
                    {file.name} · {(file.size / 1024 / 1024).toFixed(2)} МБ
                  </p>
                )}
              </div>

              {uploadError && <Banner level="error">{uploadError}</Banner>}
              {uploaded && (
                <div className="space-y-3" aria-live="polite">
                  <Banner level="info">
                    Шаблон «{uploaded.name}» добавлен. ID: {uploaded.id}
                  </Banner>
                  {uploaded.warnings.length > 0 && (
                    <Banner level="warning">
                      <span>
                        Автопроверка завершилась с предупреждениями:
                        <ul className="list-disc pl-5 mt-1">
                          {uploaded.warnings.map((warning) => (
                            <li key={warning}>{warning}</li>
                          ))}
                        </ul>
                      </span>
                    </Banner>
                  )}
                </div>
              )}

              <Button
                type="submit"
                loading={uploading}
                disabled={!file || !token.trim()}
                className="w-full justify-center"
              >
                {uploading ? 'Загружаем…' : 'Загрузить шаблон'}
              </Button>
            </form>
          </section>

          <section
            className="overflow-hidden"
            style={{
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
            }}
          >
            <div
              className="px-5 py-4 flex items-center justify-between gap-4 border-b"
              style={{ borderColor: 'var(--border)' }}
            >
              <div>
                <h2 className="font-bold">Доступные шаблоны</h2>
                <p
                  className="text-xs mt-1"
                  style={{ color: 'var(--muted-foreground)' }}
                >
                  {availableCount} из {templates.length} готовы к использованию
                </p>
              </div>
              <Button
                type="button"
                variant="secondary"
                onClick={() => void loadTemplates()}
                disabled={loadingTemplates}
                aria-label="Обновить список шаблонов"
              >
                <RefreshCw size={16} />
              </Button>
            </div>

            {listError && (
              <div className="p-5">
                <Banner level="error">{listError}</Banner>
              </div>
            )}
            {loadingTemplates ? (
              <div
                className="p-8 text-sm text-center"
                style={{ color: 'var(--muted-foreground)' }}
              >
                Загружаем список…
              </div>
            ) : templates.length === 0 ? (
              <div
                className="p-8 text-sm text-center"
                style={{ color: 'var(--muted-foreground)' }}
              >
                Шаблоны пока не найдены
              </div>
            ) : (
              <ul className="divide-y" style={{ borderColor: 'var(--border)' }}>
                {templates.map((template) => (
                  <li
                    key={template.id}
                    className="px-5 py-4 flex items-start gap-3"
                    style={{ borderColor: 'var(--border)' }}
                  >
                    <span
                      className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{
                        background: template.available
                          ? 'var(--chip-found-bg)'
                          : 'var(--banner-error-bg)',
                        color: template.available
                          ? 'var(--chip-found-text)'
                          : 'var(--banner-error-text)',
                      }}
                    >
                      <FileCheck2 size={18} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-3">
                        <strong className="text-sm">{template.name}</strong>
                        <span
                          className="text-xs font-semibold"
                          style={{
                            color: template.available
                              ? 'var(--chip-found-text)'
                              : 'var(--banner-error-text)',
                          }}
                        >
                          {template.available ? 'Доступен' : 'Недоступен'}
                        </span>
                      </div>
                      <p
                        className="text-xs mt-1 break-words"
                        style={{ color: 'var(--muted-foreground)' }}
                      >
                        {template.description || template.id}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
