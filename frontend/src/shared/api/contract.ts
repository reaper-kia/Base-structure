import type {
  DevState,
  DocumentState,
  DocType,
  Template,
  TraceEntry,
} from './types';

export interface RenderResult {
  blob: Blob;
  filename: string;
  fallback: boolean;
  fallbackReason: string | null;
}

export interface DocumentApi {
  getDocTypes(): Promise<DocType[]>;
  getTemplates(): Promise<Template[]>;
  createDocument(data: {
    draft: string;
    doc_type: string;
    template_id: string;
  }): Promise<DocumentState>;
  getDocument(id: string): Promise<DocumentState>;
  patchRequisites(
    id: string,
    values: Record<string, string | null>
  ): Promise<DocumentState>;
  reprocessDocument(id: string): Promise<DocumentState>;
  renderDocument(id: string): Promise<RenderResult>;
  getTrace(id: string): Promise<TraceEntry[]>;
  getDevState(): Promise<DevState>;
  setAiForceFailure(enabled: boolean): Promise<DevState>;
  getTemplateBroken(): Promise<boolean>;
  setTemplateBroken(
    enabled: boolean
  ): Promise<{ template_broken: boolean }>;
}