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

export interface AuthCapabilities {
  sso: boolean
  dev_login: boolean
}

export function getMe(): Promise<AuthMe> {
  return api.get<AuthMe>('/v1/auth/me')
}

export function getAuthCapabilities(): Promise<AuthCapabilities> {
  return api.get<AuthCapabilities>('/v1/auth/capabilities')
}

export function devLogin(email: string, name?: string): Promise<AuthMe> {
  return api.post<AuthMe>('/v1/auth/dev-login', { email, name: name || null })
}

export function refreshSession(): Promise<AuthMe> {
  return api.post<AuthMe>('/v1/auth/refresh')
}

export function logoutSession(): Promise<{ ok: boolean }> {
  return api.post<{ ok: boolean }>('/v1/auth/logout')
}
