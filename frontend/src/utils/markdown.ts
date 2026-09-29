import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const md = new MarkdownIt({ html: true, linkify: true, breaks: true })

/**
 * Markdown 渲染 + 引用角标：
 * 先把 [n] 替换为可点击的上标角标，再走 markdown 渲染，最后 DOMPurify 消毒（XSS 防护）。
 */
export function renderWithCitations(text: string): string {
  const withCites = text.replace(
    /\[(\d{1,2})\]/g,
    '<sup class="cite-chip" data-cite="$1">[$1]</sup>',
  )
  const html = md.render(withCites)
  return DOMPurify.sanitize(html, { ADD_ATTR: ['data-cite'] })
}

/** ISO 时间转本地显示 */
export function formatDateTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 文件大小格式化 */
export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}
