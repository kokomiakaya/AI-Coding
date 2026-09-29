import type { SourceItem } from './session'

export interface StreamHandlers {
  onMeta?: (data: {
    message_id: number
    user_message_id: number
    session_id: number
    session_title: string
    kb_id: number | null
  }) => void
  onDelta?: (content: string) => void
  onSources?: (sources: SourceItem[]) => void
  onUsage?: (data: {
    prompt_tokens: number
    completion_tokens: number
    latency_ms: number
    meta: Record<string, any>
  }) => void
  onDone?: (messageId: number) => void
  onError?: (detail: string) => void
}

/**
 * 流式问答（SSE）：原生 fetch + ReadableStream 解析。
 * EventSource 只支持 GET，因此用 fetch 解析 POST 流。
 */
export async function streamChat(
  body: { question: string; session_id?: number | null; kb_id?: number | null },
  handlers: StreamHandlers,
): Promise<void> {
  const token = localStorage.getItem('token')
  const resp = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  })

  if (!resp.ok || !resp.body) {
    const err = await resp.json().catch(() => ({ detail: '网络请求失败' }))
    throw new Error(err.detail || `请求失败（${resp.status}）`)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const dispatch = (event: string, data: string) => {
    let payload: any
    try {
      payload = JSON.parse(data)
    } catch {
      return
    }
    switch (event) {
      case 'meta':
        handlers.onMeta?.(payload)
        break
      case 'delta':
        handlers.onDelta?.(payload.content)
        break
      case 'sources':
        handlers.onSources?.(payload.sources)
        break
      case 'usage':
        handlers.onUsage?.(payload)
        break
      case 'done':
        handlers.onDone?.(payload.message_id)
        break
      case 'error':
        handlers.onError?.(payload.detail)
        break
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      const chunk = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      let event = 'message'
      let data = ''
      for (const line of chunk.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7).trim()
        else if (line.startsWith('data: ')) data += line.slice(6)
      }
      if (data) dispatch(event, data)
    }
  }
}
