import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from '../features/auth/ProtectedRoute';
import { AdminPage } from '../pages/admin/AdminPage';
import { HomePage } from '../pages/home/HomePage';
import { LoginPage } from '../pages/login/LoginPage';
import { NotFoundPage } from '../pages/not-found/NotFoundPage';
import { WizardPage } from '../pages/document-wizard/WizardPage';
import { DocumentPage } from '../pages/document-detail/DocumentPage';
import { PublicLayout } from '../widgets/layout/PublicLayout';

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/wizard" element={<WizardPage />} />
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}