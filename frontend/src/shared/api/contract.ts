import type {
  DevState,
  DocumentState,
  DocType,
  Template,
  TemplateUploadResult,
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
  uploadTemplate(
    file: File,
    adminToken: string
  ): Promise<TemplateUploadResult>;
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
  /** Ручная правка улучшенного текста перед генерацией файла (сценарий 7). */
  updateText(id: string, improvedText: string): Promise<DocumentState>;
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
