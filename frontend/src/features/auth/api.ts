import { apiClient } from '../../shared/api/client';

export interface CurrentUser {
  id: string;
  name: string;
  email: string;
  is_admin: boolean;
}

export interface RegisterAdminPayload {
  name: string;
  email: string;
  password: string;
  admin_code: string;
}

export const authApi = {
  login(email: string, password: string): Promise<{ message: string }> {
    return apiClient.post('/auth/login', { email, password });
  },
  registerAdmin(payload: RegisterAdminPayload): Promise<CurrentUser> {
    return apiClient.post('/users/register', payload);
  },
  logout(): Promise<{ message: string }> {
    return apiClient.post('/auth/logout', {});
  },
  me(): Promise<CurrentUser> {
    return apiClient.get('/users/me');
  },
};
