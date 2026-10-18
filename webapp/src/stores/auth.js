/**
 * Pinia store — authenticated user state.
 * Loaded once on app boot from /api/auth/me.
 */
import { defineStore } from 'pinia'
import { getMe } from '@/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,       // { id, first_name, username, balance, is_admin, app_title, version }
    appTitle: 'فروشگاه',
    appVersion: '5.4.1',
    loading: true,
    error: null,
  }),
  getters: {
    isAdmin: (s) => s.user?.is_admin === true,
    balance: (s) => s.user?.balance ?? 0,
    version: (s) => s.appVersion || s.user?.version || '5.4.1',
    guidesEnabled: (s) => s.user?.guides_enabled !== false,
  },
  actions: {
    async fetchMe() {
      this.loading = true
      this.error = null
      try {
        const { data } = await getMe()
        this.user = data
        if (data.app_title) {
          this.setAppTitle(data.app_title)
        }
        if (data.version) {
          this.appVersion = data.version
        }
      } catch (e) {
        this.error = e.response?.data?.detail || 'خطا در احراز هویت'
      } finally {
        this.loading = false
      }
    },
    setAppTitle(newTitle) {
      if (newTitle) {
        this.appTitle = newTitle
        document.title = newTitle
      }
    },
    updateBalance(newBalance) {
      if (this.user) this.user.balance = newBalance
    },
  },
})
