import { useEffect, useState, type FormEvent } from 'react';
import { LockKeyhole } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../app/providers/LanguageProvider';
import { ApiError } from '../../shared/api/client';
import { Button } from '../../shared/ui/Button';
import { Input } from '../../shared/ui/Input';
import { authApi } from '../../features/auth/api';

/**
 * Вход и регистрация администратора в одной форме.
 *
 * Admin-код (ADMIN_REGISTRATION_CODE в .env) отправляется только на бэкенд
 * и нигде не сохраняется в браузере. Первого админа создавай через эту
 * форму либо скриптом src/modules/users/scripts/create_admin.py.
 */
export function LoginPage() {
  const navigate = useNavigate();
  const { language } = useLanguage();
  const ru = language === 'ru';

  const [registerMode, setRegisterMode] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [adminCode, setAdminCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    authApi.me()
      .then((user) => { if (user.is_admin) navigate('/admin', { replace: true }); })
      .catch(() => undefined);
  }, [navigate]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');

    if (!email.trim() || password.length < 8 || (registerMode && (!name.trim() || !adminCode.trim()))) {
      setError(ru
        ? 'Заполните все поля. Пароль — не короче 8 символов.'
        : 'Complete every field. Password must contain at least 8 characters.');
      return;
    }

    setLoading(true);
    try {
      if (registerMode) {
        const created = await authApi.registerAdmin({
          name: name.trim(), email: email.trim(), password, admin_code: adminCode.trim(),
        });
        if (!created.is_admin) {
          throw new Error(ru
            ? 'Пользователь создан без прав администратора: проверьте admin-код.'
            : 'The user was created without admin access. Check the admin code.');
        }
      }

      await authApi.login(email.trim(), password);
      const user = await authApi.me();
      if (!user.is_admin) {
        await authApi.logout();
        throw new Error(ru
          ? 'У этого пользователя нет прав администратора.'
          : 'This user does not have admin access.');
      }
      navigate('/admin', { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError(ru ? 'Неверный email или пароль.' : 'Incorrect email or password.');
      } else if (err instanceof ApiError && err.status === 409) {
        setError(ru ? 'Пользователь с таким email уже существует.' : 'A user with this email already exists.');
      } else {
        setError(err instanceof Error ? err.message : 'Login failed');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-page">
      <div className="login-page__form">
        <form onSubmit={submit} noValidate>
          <span className="login-icon"><LockKeyhole /></span>
          <h1>
            {registerMode
              ? (ru ? 'Регистрация администратора' : 'Admin registration')
              : (ru ? 'Вход' : 'Sign in')}
          </h1>

          {registerMode && (
            <Input
              label={ru ? 'Имя' : 'Name'}
              value={name}
              onChange={(event) => setName(event.target.value)}
              autoComplete="name"
              required
            />
          )}

          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            required
          />

          <Input
            label={ru ? 'Пароль' : 'Password'}
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={registerMode ? 'new-password' : 'current-password'}
            minLength={8}
            required
          />

          {registerMode && (
            <Input
              label="Admin code"
              type="password"
              value={adminCode}
              onChange={(event) => setAdminCode(event.target.value)}
              autoComplete="off"
              required
            />
          )}

          {error && <p className="form-error" role="alert">{error}</p>}

          <Button type="submit" loading={loading}>
            {registerMode
              ? (ru ? 'Создать администратора' : 'Create administrator')
              : (ru ? 'Войти' : 'Sign in')}
          </Button>

          <button
            className="login-mode-toggle"
            type="button"
            onClick={() => { setRegisterMode((value) => !value); setError(''); setAdminCode(''); }}
          >
            {registerMode
              ? (ru ? 'Уже есть аккаунт? Войти' : 'Already have an account? Sign in')
              : (ru ? 'Зарегистрировать администратора' : 'Register an administrator')}
          </button>
        </form>
      </div>
    </main>
  );
}
