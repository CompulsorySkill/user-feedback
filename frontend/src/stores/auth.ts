import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type UserRole = 'user' | 'admin'

export interface CurrentUser {
  id: number
  email: string
  displayName: string | null
  role: UserRole
}

/**
 * 鉴权状态：P0 仅提供骨架，P3 接入 SSO 后由 /api/v1/auth/me 填充。
 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUser | null>(null)

  const isAuthenticated = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function setUser(next: CurrentUser | null): void {
    user.value = next
  }

  function clear(): void {
    user.value = null
  }

  return { user, isAuthenticated, isAdmin, setUser, clear }
})
