import http from './axios'
import type { PageResult } from './document'

export interface SessionItem {
  id: number
  title: string
  kb_id: number | null
  created_at: string
  updated_at: string
  last_message: string | null
  message_count: number
}

export interface MessageItem {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources: SourceItem[] | null
  prompt_tokens: number
  completion_tokens: number
  latency_ms: number
  meta: Record<string, any>
  feedback: number | null
  created_at: string
}

export interface SourceItem {
  index: number
  chunk_id: number
  document_id: number
  document_name: string
  excerpt: string
  content: string
  page: number | null
  sheet: string | null
  row: number | null
  relevance_score: number
  cited: boolean
}

export const sessionApi = {
  list(page: number, size: number, q?: string) {
    return http.get('/sessions', { params: { page, size, q } }) as Promise<
      PageResult<SessionItem>
    >
  },
  create(data: { title?: string; kb_id?: number | null }) {
    return http.post('/sessions', data) as Promise<SessionItem>
  },
  messages(sessionId: number, page: number, size: number) {
    return http.get(`/sessions/${sessionId}/messages`, { params: { page, size } }) as Promise<
      PageResult<MessageItem>
    >
  },
  update(sessionId: number, data: { title?: string; kb_id?: number | null }) {
    return http.patch(`/sessions/${sessionId}`, data) as Promise<SessionItem>
  },
  remove(sessionId: number) {
    return http.delete(`/sessions/${sessionId}`) as Promise<any>
  },
  // 导出需携带 JWT，用 fetch 下载 blob
  async exportSession(sessionId: number) {
    const token = localStorage.getItem('token')
    const resp = await fetch(`/api/sessions/${sessionId}/export`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!resp.ok) throw new Error('导出失败')
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `会话导出_${sessionId}.md`
    a.click()
    URL.revokeObjectURL(url)
  },
}
