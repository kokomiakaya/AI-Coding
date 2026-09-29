import { defineStore } from 'pinia'
import { authApi } from '../api/auth'

export interface UserInfo {
  id: number
  username: string
  role: string
  is_active: boolean
  created_at: string
}

interface AuthState {
  token: string
  user: UserInfo | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === 'admin',
  },
  actions: {
    setSession(token: string, user: UserInfo) {
      this.token = token
      this.user = user
      localStorage.setItem('token', token)
      localStorage.setItem('user', JSON.stringify(user))
    },
    async login(username: string, password: string) {
      const data = await authApi.login(username, password)
      this.setSession(data.access_token, data.user)
    },
    async register(username: string, password: string) {
      await authApi.register(username, password)
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
    async changePassword(oldPassword: string, newPassword: string) {
      await authApi.changePassword(oldPassword, newPassword)
    },
  },
})
