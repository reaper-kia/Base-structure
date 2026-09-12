const API_BASE_URL = String(import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

const statusMessages: Record<number, string> = {
  400: 'Некорректные данные запроса',
  401: 'Требуется войти в систему',
  403: 'Недостаточно прав',
  404: 'Данные не найдены',
  409: 'Конфликт данных',
  422: 'Проверьте заполненные поля',
  429: 'Слишком много запросов. Попробуйте позже',
  500: 'Сервис временно недоступен',
};

export class ApiError extends Error {
  readonly status: number;
  readonly details?: unknown;

  constructor(
    message: string,
    status: number,
    details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

function extractMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === 'object') {
    const detail = 'detail' in payload ? payload.detail : undefined;
    const message = 'message' in payload ? payload.message : undefined;
    if (typeof detail === 'string') return detail;
    if (typeof message === 'string') return message;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (first && typeof first === 'object' && 'msg' in first && typeof first.msg === 'string') {
        return first.msg.replace(/^Value error,\s*/i, '');
      }
    }
  }
  return statusMessages[status] ?? `Ошибка запроса (${status})`;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const hasBody = options.body !== undefined;
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => undefined);
    throw new ApiError(extractMessage(payload, response.status), response.status, payload);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(endpoint: string, signal?: AbortSignal) =>
    request<T>(endpoint, { method: 'GET', signal }),
  post: <T>(endpoint: string, body: unknown) =>
    request<T>(endpoint, { method: 'POST', body: JSON.stringify(body) }),
  patch: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, {
      method: 'PATCH',
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    }),
  delete: <T>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
};
