import { api } from './client'

export interface AuthUser {
  id: number
  email: string
  display_name: string | null
  role: 'user' | 'admin'
}

export interface AuthMe {
  authenticated: boolean
  is_admin: boolean
  is_anonymous: boolean
  user: AuthUser | null
}

export function getMe(): Promise<AuthMe> {
  return api.get<AuthMe>('/v1/auth/me')
}

export function refreshSession(): Promise<AuthMe> {
  return api.post<AuthMe>('/v1/auth/refresh')
}

export function logoutSession(): Promise<{ ok: boolean }> {
  return api.post<{ ok: boolean }>('/v1/auth/logout')
}
