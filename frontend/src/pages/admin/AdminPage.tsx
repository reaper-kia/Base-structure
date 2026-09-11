import { useLanguage } from '../../app/providers/LanguageProvider';
import { EmptyState } from '../../shared/ui/EmptyState';
import { authApi } from '../../features/auth/api';
import { Button } from '../../shared/ui/Button';

/**
 * Заглушка защищённой страницы. Показывает, что ProtectedRoute работает,
 * и даёт рабочую кнопку выхода. Наполняй под кейс.
 */
export function AdminPage() {
  const { t } = useLanguage();

  const logout = async () => {
    await authApi.logout();
    window.location.assign('/login');
  };

  return (
    <section className="container">
      <header className="page-header">
        <h1>{t('admin')}</h1>
        <Button type="button" variant="secondary" onClick={logout}>{t('logout')}</Button>
      </header>
      <EmptyState
        title={t('empty')}
        message="Это защищённая страница. Доступна только пользователю с is_admin = true."
      />
    </section>
  );
}
