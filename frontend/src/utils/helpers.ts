// NotingHill — utils/helpers.ts

export function formatSize(bytes: number | null | undefined): string {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)} ${units[i]}`
}

export function formatDate(ts: number | null | undefined): string {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleDateString('en-CA', {
    year: 'numeric', month: '2-digit', day: '2-digit',
  })
}

export function formatDateTime(ts: number | null | undefined): string {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString('en-CA', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

export function formatDuration(startTs: number, endTs: number | null): string {
  if (!endTs) return 'running'
  const secs = endTs - startTs
  if (secs < 60) return `${secs}s`
  if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s`
  return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`
}

export function getBadgeClass(group: string): string {
  const map: Record<string, string> = {
    text:    'badge-text',
    code:    'badge-code',
    pdf:     'badge-pdf',
    office:  'badge-office',
    image:   'badge-image',
    audio:   'badge-audio',
    video:   'badge-video',
    archive: 'badge-archive',
  }
  return map[group] ?? 'badge-other'
}

export function getTypeIcon(group: string): string {
  const map: Record<string, string> = {
    text:    '📄',
    code:    '⌨',
    pdf:     '📕',
    office:  '📊',
    image:   '🖼',
    audio:   '🎵',
    video:   '🎬',
    archive: '📦',
    other:   '📎',
  }
  return map[group] ?? '📎'
}

export function getTypeColor(group: string): string {
  const map: Record<string, string> = {
    text:    '#4a80ff',
    code:    'var(--green)',
    pdf:     'var(--red)',
    office:  'var(--amber)',
    image:   'var(--purple)',
    audio:   'var(--pink)',
    video:   '#44ccff',
    archive: '#ffcc44',
    other:   'var(--text3)',
  }
  return map[group] ?? 'var(--text3)'
}

export function truncate(str: string, max: number): string {
  if (!str) return ''
  return str.length > max ? str.slice(0, max) + '…' : str
}

export function pct(part: number, total: number): number {
  if (!total) return 0
  return Math.round((part / total) * 100)
}
