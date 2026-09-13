import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from '../features/auth/ProtectedRoute';
import { AdminPage } from '../pages/admin/AdminPage';
import { LoginPage } from '../pages/login/LoginPage';
import { NotFoundPage } from '../pages/not-found/NotFoundPage';
import { WizardPage } from '../pages/document-wizard/WizardPage';
import { DocumentPage } from '../pages/document-detail/DocumentPage';
import { AppShell } from '../widgets/app-shell/AppShell';
import { PublicLayout } from '../widgets/layout/PublicLayout';
import { DevPanel } from '../pages/dev/DevPanel';
import { TracePage } from '../pages/trace/TracePage';

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route path="/" element={<Navigate to="/wizard" replace />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        <Route element={<AppShell />}>
          <Route path="/wizard" element={<WizardPage />} />
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="/dev" element={<DevPanel />} />
          <Route path="/trace/:id" element={<TracePage />} />
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