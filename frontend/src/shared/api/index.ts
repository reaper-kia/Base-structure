import type { DocumentApi } from './contract';
import { httpApi } from './httpApi';
import { mockApi } from './mock';

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export const api: DocumentApi = USE_MOCK ? mockApi : httpApi;
export const API_MODE: 'mock' | 'real' = USE_MOCK ? 'mock' : 'real';