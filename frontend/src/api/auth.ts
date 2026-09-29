import http from './axios'
import type { UserInfo } from '../stores/auth'

export interface TokenResult {
  access_token: string
  token_type: string
  user: UserInfo
}

export const authApi = {
  register(username: string, password: string) {
    return http.post('/auth/register', { username, password }) as Promise<any>
  },
  login(username: string, password: string) {
    return http.post('/auth/login', { username, password }) as Promise<TokenResult>
  },
  me() {
    return http.get('/auth/me') as Promise<UserInfo>
  },
  changePassword(old_password: string, new_password: string) {
    return http.post('/auth/change-password', { old_password, new_password }) as Promise<any>
  },
}
