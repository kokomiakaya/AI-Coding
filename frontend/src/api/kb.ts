import http from './axios'

export interface KnowledgeBase {
  id: number
  name: string
  description: string
  chunk_size: number
  chunk_overlap: number
  top_k: number
  score_threshold: number
  rewrite_enabled: boolean
  is_active: boolean
  created_at: string
  document_count: number
  chunk_count: number
}

export interface SearchTestResult {
  question: string
  retrieved_count: number
  hybrid: Array<{
    chunk_id: number
    document_name: string
    page: number | null
    sheet: string | null
    row: number | null
    excerpt: string
    rrf_score: number
    relevance_score: number | null
  }>
  reranked: Array<any>
  rerank_skipped: boolean
}

export const kbApi = {
  list() {
    return http.get('/kb') as Promise<KnowledgeBase[]>
  },
  get(id: number) {
    return http.get(`/kb/${id}`) as Promise<KnowledgeBase>
  },
  create(data: Partial<KnowledgeBase>) {
    return http.post('/kb', data) as Promise<KnowledgeBase>
  },
  update(id: number, data: Partial<KnowledgeBase>) {
    return http.patch(`/kb/${id}`, data) as Promise<KnowledgeBase>
  },
  remove(id: number) {
    return http.delete(`/kb/${id}`) as Promise<any>
  },
  searchTest(id: number, question: string) {
    return http.post(`/kb/${id}/search-test`, { question }) as Promise<SearchTestResult>
  },
}
