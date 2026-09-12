import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AppShell } from '../widgets/app-shell/AppShell';
import { WizardPage } from '../pages/document-wizard/WizardPage';
import { DocumentPage } from '../pages/document-detail/DocumentPage';
import { DevPanel } from '../pages/dev/DevPanel';
import { TracePage } from '../pages/trace/TracePage';
import { NotFoundPage } from '../pages/not-found/NotFoundPage';

/**
 * Единственный сценарий продукта — три шага до готового DOCX, поэтому
 * корень сразу открывает мастер: лишний промежуточный экран между
 * «зашёл» и «вставил черновик» ничего не добавляет.
 */
export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<WizardPage />} />
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="/dev" element={<DevPanel />} />
          <Route path="/trace/:id" element={<TracePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
