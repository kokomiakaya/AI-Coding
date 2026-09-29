import http from './axios'
import type { PageResult } from './document'
import type { UserInfo } from '../stores/auth'

export interface StatsOverview {
  user_count: number
  session_count: number
  message_count: number
  kb_count: number
  document_count: number
  chunk_count: number
  total_tokens: number
}

export interface ConfigItem {
  key: string
  default: any
  value: any
  description: string
}

export const adminApi = {
  statsOverview() {
    return http.get('/admin/stats/overview') as Promise<StatsOverview>
  },
  statsTrend(days: number) {
    return http.get('/admin/stats/trend', { params: { days } }) as Promise<{
      days: number
      items: Array<{ date: string; messages: number; tokens: number }>
    }>
  },
  statsKb() {
    return http.get('/admin/stats/kb') as Promise<
      Array<{ kb_id: number; name: string; document_count?: number; chunk_count?: number; answer_count: number }>
    >
  },
  statsFeedback() {
    return http.get('/admin/stats/feedback') as Promise<{
      likes: number
      dislikes: number
      total: number
      satisfaction_rate: number | null
      trend: Array<{ date: string; likes: number; dislikes: number }>
    }>
  },
  getConfigs() {
    return http.get('/admin/config') as Promise<ConfigItem[]>
  },
  updateConfigs(configs: Record<string, any>) {
    return http.put('/admin/config', configs) as Promise<any>
  },
  listUsers(page: number, size: number, q?: string, role?: string) {
    return http.get('/users', { params: { page, size, q, role } }) as Promise<
      PageResult<UserInfo>
    >
  },
  updateUser(id: number, data: { is_active?: boolean; role?: string }) {
    return http.patch(`/users/${id}`, data) as Promise<UserInfo>
  },
}
