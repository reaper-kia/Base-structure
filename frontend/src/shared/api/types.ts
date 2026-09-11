export type DocumentStatus = 'processing' | 'processed' | 'degraded' | 'failed';

export type ProcessingStage = 'llm' | 'fact_guard' | 'validation';

export type RequisiteStatus =
  | 'found_in_draft'
  | 'user_provided'
  | 'auto_filled'
  | 'missing'
  | 'left_blank';

export type ChangeType = 'spelling' | 'punctuation' | 'style' | 'structure';

export interface DocTypeRequisite {
  key: string;
  label: string;
  required: boolean;
}

export interface DocType {
  id: string;
  name: string;
  description: string;
  requisites: DocTypeRequisite[];
}

export interface Template {
  id: string;
  name: string;
  description: string;
  preview_url: string;
  available: boolean;
}

export interface ChangeItem {
  type: ChangeType;
  from: string;
  to: string;
}

export interface RequisiteState {
  key: string;
  label: string;
  value: string | null;
  status: RequisiteStatus;
  required: boolean;
}

export type FactGuard = {
  verdict: 'clean' | 'warning' | 'blocked';
  preserved: string[];
  lost: string[];
  added: string[];
  source_count: number;
  preserved_count: number;
};

export interface DocumentError {
  code: 'llm_unavailable' | 'llm_invalid_response' | 'template_missing' | 'internal';
  message: string;
  recoverable: boolean;
}

export interface DocumentState {
  id: string;
  status: DocumentStatus;
  stage: ProcessingStage | null;
  doc_type: string;
  template_id: string;
  draft: string;
  improved_text: string | null;
  changes: ChangeItem[];
  requisites: RequisiteState[];
  fact_guard: FactGuard | null;
  is_fallback: boolean;
  error: DocumentError | null;
}

export interface TraceEntry {
  stage: string;
  payload: Record<string, unknown>;
}

export interface DevState {
  ai_force_failure: boolean;
  ml_service_url: string;
  ml_reachable: boolean;
  model_version: string;
  templates_loaded: string[];
}

export type MockScenario = 'all_found' | 'no_addressee' | 'ai_failed';