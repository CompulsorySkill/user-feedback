import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

import { getMe, logoutSession, refreshSession, type AuthMe, type AuthUser } from '@/api/auth';

export const useAuthStore = defineStore('auth', () => {
  const me = ref<AuthMe | null>(null);
  const loading = ref(false);

  const user = computed<AuthUser | null>(() => me.value?.user ?? null);
  const isAuthenticated = computed(() => Boolean(me.value?.authenticated));
  const isAdmin = computed(() => Boolean(me.value?.is_admin));
  const isAnonymous = computed(() => Boolean(me.value?.is_anonymous));
  const displayName = computed(
    () => user.value?.display_name?.trim() || user.value?.email || '用户',
  );

  async function hydrate(): Promise<void> {
    loading.value = true;
    try {
      me.value = await getMe();
    } catch {
      me.value = null;
    } finally {
      loading.value = false;
    }
  }

  async function refresh(): Promise<boolean> {
    try {
      me.value = await refreshSession();
      return Boolean(me.value.authenticated);
    } catch {
      return false;
    }
  }

  async function logout(): Promise<void> {
    try {
      await logoutSession();
    } finally {
      me.value = null;
    }
  }

  return {
    me,
    loading,
    user,
    isAuthenticated,
    isAdmin,
    isAnonymous,
    displayName,
    hydrate,
    refresh,
    logout,
  };
});
