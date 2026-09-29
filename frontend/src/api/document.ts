import http from './axios'

export interface DocumentItem {
  id: number
  kb_id: number
  filename: string
  file_type: string
  file_size: number
  status: 'pending' | 'parsing' | 'embedding' | 'ready' | 'failed'
  chunk_count: number
  error_message: string | null
  created_at: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export const documentApi = {
  upload(kbId: number, files: File[]) {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    return http.post(`/kb/${kbId}/documents`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }) as Promise<{ items: DocumentItem[]; message: string }>
  },
  createText(kbId: number, filename: string, content: string) {
    return http.post(`/kb/${kbId}/documents/text`, { filename, content }) as Promise<DocumentItem>
  },
  list(kbId: number, page: number, size: number, status?: string) {
    return http.get(`/kb/${kbId}/documents`, { params: { page, size, status } }) as Promise<
      PageResult<DocumentItem>
    >
  },
  get(id: number) {
    return http.get(`/documents/${id}`) as Promise<DocumentItem>
  },
  reEmbed(id: number) {
    return http.post(`/documents/${id}/re-embed`) as Promise<DocumentItem>
  },
  remove(id: number) {
    return http.delete(`/documents/${id}`) as Promise<any>
  },
  chunks(id: number, page: number, size: number) {
    return http.get(`/documents/${id}/chunks`, { params: { page, size } }) as Promise<
      PageResult<{ id: number; chunk_index: number; content: string; meta: Record<string, any> }>
    >
  },
}
