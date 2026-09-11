import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { NotFoundPage } from '../pages/not-found/NotFoundPage';
import { WizardPage } from '../pages/document-wizard/WizardPage';
import { DocumentPage } from '../pages/document-detail/DocumentPage';
import { PublicLayout } from '../widgets/layout/PublicLayout';

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<PublicLayout />}>
          {/* Корень — сразу мастер создания документа, это и есть продукт.
              Заглушка home/login/admin из FE-шаблона продукту не нужна. */}
          <Route path="/" element={<WizardPage />} />
          <Route path="/wizard" element={<WizardPage />} />
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}