// NotingHill — pages/Search.tsx
import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { useStore } from '../store'
import { searchFiles, getItem, openFile, revealFile, listRoots, getItemRawUrl } from '../api/client'
import { FileRow, SectionHeader, Badge, EmptyState } from '../components/ui'
import { formatSize, formatDateTime, getTypeIcon } from '../utils/helpers'

const FILE_TYPES = ['text', 'code', 'pdf', 'office', 'image', 'audio', 'video', 'archive', 'other']
const TEXT_LIKE_EXTS = new Set(['.txt', '.md', '.markdown', '.json', '.xml', '.yaml', '.yml', '.csv', '.log', '.ini', '.cfg', '.toml', '.py', '.js', '.ts', '.tsx', '.jsx', '.css', '.scss', '.html', '.sql', '.java', '.c', '.cpp', '.h', '.hpp', '.go', '.rs', '.php', '.rb', '.sh', '.bat', '.ps1'])
const OFFICE_EXTS = new Set(['.doc', '.docx', '.xls', '.xlsx', '.xlsm', '.ppt', '.pptx'])

export default function Search() {
  const {
    t, searchQuery, setSearchQuery, searchResults, setSearchResults,
    searchLoading, setSearchLoading, selectedItem, setSelectedItem,
    searchFilters, setSearchFilters,
  } = useStore()

  const [roots, setRoots] = useState<any[]>([])
  const [sortBy, setSortBy] = useState('rank')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    listRoots().then(d => setRoots(d.roots || []))
  }, [])

  const doSearch = useCallback(async (q: string, filters: any, sort: string) => {
    setSearchLoading(true)
    try {
      const params: any = { q, order_by: sort, limit: 100, ...filters }
      Object.keys(params).forEach(k => (params[k] === '' || params[k] == null) && delete params[k])
      const data = await searchFiles(params)
      setSearchResults(data.results || [])
    } catch {
      setSearchResults([])
    }
    setSearchLoading(false)
  }, [setSearchLoading, setSearchResults])

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      doSearch(searchQuery, searchFilters, sortBy)
    }, 280)

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [searchQuery, searchFilters, sortBy, doSearch])

  const handleSelectItem = async (item: any) => {
    try {
      const detail = await getItem(item.item_id)
      setSelectedItem(detail)
    } catch {
      setSelectedItem(item)
    }
  }

  const filterStyle: React.CSSProperties = {
    display: 'flex', flexDirection: 'column', gap: 6,
  }

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - var(--topbar-height))', overflow: 'hidden' }}>
      <aside style={{
        width: 200,
        borderRight: '1px solid var(--border)',
        padding: '16px 14px',
        overflowY: 'auto',
        flexShrink: 0,
        background: 'var(--bg1)',
      }}>
        <SectionHeader label={t('search_filters')} />

        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: 2, marginBottom: 8 }}>
            {t('search_type')}
          </div>
          <div style={filterStyle}>
            <button
              className={`nh-btn ${!searchFilters.file_type ? 'primary' : ''}`}
              style={{ textAlign: 'left', padding: '4px 8px', fontSize: 9 }}
              onClick={() => setSearchFilters({ ...searchFilters, file_type: '' })}
            >
              {t('search_all_types')}
            </button>
            {FILE_TYPES.map(ft => (
              <button
                key={ft}
                className={`nh-btn ${searchFilters.file_type === ft ? 'primary' : ''}`}
                style={{ textAlign: 'left', padding: '4px 8px', fontSize: 9 }}
                onClick={() => setSearchFilters({ ...searchFilters, file_type: ft === searchFilters.file_type ? '' : ft })}
              >
                {getTypeIcon(ft)} {t(`file_types.${ft}` as any)}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: 2, marginBottom: 8 }}>
            {t('search_folder')}
          </div>
          <select
            className="nh-input"
            style={{ fontSize: 10, padding: '6px 8px' }}
            value={searchFilters.root_id || ''}
            onChange={e => setSearchFilters({ ...searchFilters, root_id: e.target.value })}
          >
            <option value="">{t('search_all_folders')}</option>
            {roots.map((r: any) => (
              <option key={r.root_id} value={r.root_id}>{r.root_label || r.root_path}</option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: 2, marginBottom: 8 }}>
            {t('search_date_range')}
          </div>
          <input
            type="date"
            className="nh-input"
            style={{ fontSize: 10, padding: '6px 8px', marginBottom: 4 }}
            onChange={e => {
              const ts = e.target.value ? Math.floor(new Date(e.target.value).getTime() / 1000) : null
              setSearchFilters({ ...searchFilters, since_ts: ts })
            }}
          />
          <input
            type="date"
            className="nh-input"
            style={{ fontSize: 10, padding: '6px 8px' }}
            onChange={e => {
              const ts = e.target.value ? Math.floor(new Date(e.target.value).getTime() / 1000) : null
              setSearchFilters({ ...searchFilters, until_ts: ts })
            }}
          />
        </div>

        <div>
          <div style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: 2, marginBottom: 8 }}>
            {t('search_sort')}
          </div>
          {[
            { val: 'rank', label: t('sort_relevance') },
            { val: 'modified_ts DESC', label: t('sort_modified') },
            { val: 'size_bytes DESC', label: t('sort_size') },
            { val: 'file_name ASC', label: t('sort_name') },
          ].map(s => (
            <button
              key={s.val}
              className={`nh-btn ${sortBy === s.val ? 'primary' : ''}`}
              style={{ display: 'block', width: '100%', textAlign: 'left', padding: '4px 8px', fontSize: 9, marginBottom: 4 }}
              onClick={() => setSortBy(s.val)}
            >
              {s.label}
            </button>
          ))}
        </div>
      </aside>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg1)',
          flexShrink: 0,
        }}>
          <div style={{ position: 'relative' }}>
            <span style={{
              position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
              color: 'var(--cyan)', fontSize: 14, pointerEvents: 'none',
            }}>◎</span>
            <input
              autoFocus
              className="nh-input"
              style={{ paddingLeft: 36, fontSize: 13 }}
              placeholder={t('search_placeholder')}
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            {searchLoading && (
              <span style={{
                position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                color: 'var(--amber)', fontSize: 10, letterSpacing: 2,
              }}>
                SCANNING...
              </span>
            )}
          </div>
        </div>

        <div style={{
          padding: '6px 16px',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg1)',
          fontSize: 9,
          color: 'var(--text3)',
          letterSpacing: 2,
          flexShrink: 0,
        }}>
          {t('search_results')}: {searchResults.length}
          {searchQuery && <span style={{ color: 'var(--cyan)', marginLeft: 8 }}>&quot;{searchQuery}&quot;</span>}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px' }}>
          {!searchLoading && searchResults.length === 0 && searchQuery && (
            <EmptyState icon="◎" message={t('search_no_results')} />
          )}
          {!searchQuery && searchResults.length === 0 && (
            <EmptyState icon="◎" message={t('search_placeholder')} />
          )}
          {searchResults.map(item => (
            <FileRow
              key={item.item_id}
              item={item}
              selected={selectedItem?.item_id === item.item_id}
              onClick={() => handleSelectItem(item)}
            />
          ))}
        </div>
      </div>

      <aside style={{
        width: 420,
        borderLeft: '1px solid var(--border)',
        background: 'var(--bg1)',
        overflowY: 'auto',
        flexShrink: 0,
      }}>
        {!selectedItem ? (
          <EmptyState icon="▣" message={t('preview_no_select')} />
        ) : (
          <div style={{ padding: 16 }}>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 24, marginBottom: 8 }}>
                {getTypeIcon(selectedItem.file_type_group)}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text)', wordBreak: 'break-all', marginBottom: 4 }}>
                {selectedItem.file_name}
              </div>
              <Badge group={selectedItem.file_type_group || 'other'} />
            </div>

            <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
              <button
                className="nh-btn primary"
                style={{ flex: 1, fontSize: 9 }}
                onClick={() => openFile(selectedItem.item_id)}
              >
                {t('preview_open')}
              </button>
              <button
                className="nh-btn"
                style={{ flex: 1, fontSize: 9 }}
                onClick={() => revealFile(selectedItem.item_id)}
              >
                {t('preview_reveal')}
              </button>
            </div>

            <FilePreviewRenderer item={selectedItem} />

            <div style={{ marginBottom: 16 }}>
              <SectionHeader label={t('preview_metadata')} />
              <MetaRow label={t('path')} value={selectedItem.full_path} mono />
              <MetaRow label={t('size')} value={formatSize(selectedItem.size_bytes)} />
              <MetaRow label={t('modified')} value={formatDateTime(selectedItem.modified_ts)} />
              <MetaRow label={t('created')} value={formatDateTime(selectedItem.created_ts)} />
              {selectedItem.width && (
                <MetaRow label="DIMENSIONS" value={`${selectedItem.width}×${selectedItem.height}`} />
              )}
              {selectedItem.duration_seconds && (
                <MetaRow label="DURATION" value={formatDuration(selectedItem.duration_seconds)} />
              )}
              {selectedItem.title && <MetaRow label="TITLE" value={selectedItem.title} />}
              {selectedItem.artist && <MetaRow label="ARTIST" value={selectedItem.artist} />}
              {selectedItem.album && <MetaRow label="ALBUM" value={selectedItem.album} />}
              {selectedItem.camera_model && <MetaRow label="CAMERA" value={selectedItem.camera_model} />}
              {selectedItem.meta?.author && <MetaRow label="AUTHOR" value={selectedItem.meta.author} />}
              {selectedItem.meta?.page_count && <MetaRow label="PAGES" value={String(selectedItem.meta.page_count)} />}
              {selectedItem.meta?.sheets?.length && <MetaRow label="SHEETS" value={selectedItem.meta.sheets.join(', ')} />}
              {selectedItem.sha256 && (
                <MetaRow label="SHA256" value={selectedItem.sha256.slice(0, 16) + '…'} mono />
              )}
            </div>

            {selectedItem.duplicate_info?.length > 0 && (
              <div>
                <SectionHeader label={t('preview_duplicates')} accent="var(--amber)" />
                {selectedItem.duplicate_info.map((d: any) => (
                  <div key={d.group_id} style={{
                    background: 'var(--bg2)',
                    border: '1px solid var(--amber)',
                    padding: '8px 10px',
                    marginBottom: 4,
                    fontSize: 10,
                    color: 'var(--amber)',
                  }}>
                    ⚠ {d.group_type.toUpperCase()} · {d.item_count} files in group
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </aside>
    </div>
  )
}

function FilePreviewRenderer({ item }: { item: any }) {
  const preview = useMemo(() => buildPreviewModel(item), [item])
  const rawUrl = getItemRawUrl(item.item_id)
  const hasPreviewText = !!preview.previewText

  return (
    <div style={{ marginBottom: 16 }}>
      <SectionHeader label="INLINE PREVIEW">
        <a className="nh-btn" style={{ padding: '4px 8px', fontSize: 9 }} href={rawUrl} target="_blank" rel="noreferrer">
          OPEN IN BROWSER
        </a>
      </SectionHeader>

      <div style={{
        background: 'var(--bg2)',
        border: '1px solid var(--border)',
        minHeight: 220,
        overflow: 'hidden',
      }}>
        {preview.kind === 'pdf' && (
          <iframe title={item.file_name} src={rawUrl} style={{ width: '100%', height: 420, border: 'none', display: 'block' }} />
        )}

        {preview.kind === 'image' && (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 220, background: '#02070b' }}>
            <img src={rawUrl} alt={item.file_name} style={{ maxWidth: '100%', maxHeight: 460, display: 'block' }} />
          </div>
        )}

        {preview.kind === 'audio' && (
          <div style={{ padding: 16 }}>
            <audio controls preload="metadata" style={{ width: '100%' }} src={rawUrl} />
          </div>
        )}

        {preview.kind === 'video' && (
          <video controls preload="metadata" style={{ width: '100%', maxHeight: 420, background: '#000', display: 'block' }} src={rawUrl} />
        )}

        {(preview.kind === 'text' || preview.kind === 'office' || preview.kind === 'fallback-text') && (
          hasPreviewText ? (
            <div style={{ padding: '10px 12px', maxHeight: 420, overflowY: 'auto' }}>
              {preview.kind === 'office' ? (
                <OfficeTextPreview item={item} text={preview.previewText!} />
              ) : (
                <pre style={{
                  margin: 0,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontSize: 10,
                  lineHeight: 1.7,
                  color: 'var(--text2)',
                  fontFamily: '"IBM Plex Mono",monospace',
                }}>
                  {preview.previewText}
                </pre>
              )}
            </div>
          ) : (
            <FallbackNotice message="No extracted text available for inline preview." />
          )
        )}

        {preview.kind === 'unsupported' && (
          <FallbackNotice message="This file type cannot be rendered inline. Use Open File or Open in Browser." />
        )}
      </div>
    </div>
  )
}

function OfficeTextPreview({ item, text }: { item: any; text: string }) {
  const ext = String(item.extension || '').toLowerCase()
  const isSheet = ext === '.xlsx' || ext === '.xls' || ext === '.xlsm' || ext === '.csv'
  const lines = text.split('\n').filter(Boolean).slice(0, 120)

  if (isSheet) {
    const rows = lines.map(line => {
      const cleaned = line.replace(/^\[Sheet:\s*/i, '').replace(/\]$/, '')
      if (line.startsWith('[Sheet:')) {
        return { type: 'sheet', cells: [cleaned] }
      }
      return { type: 'row', cells: line.split('|').map(cell => cell.trim()).slice(0, 8) }
    })

    return (
      <div>
        {rows.map((row, idx) => row.type === 'sheet' ? (
          <div key={idx} style={{ fontSize: 10, color: 'var(--cyan)', letterSpacing: 1, margin: '8px 0 6px' }}>
            {row.cells[0]}
          </div>
        ) : (
          <div key={idx} style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(1, row.cells.length)}, minmax(0, 1fr))`, gap: 6, marginBottom: 6 }}>
            {row.cells.map((cell, cellIdx) => (
              <div key={cellIdx} style={{ border: '1px solid var(--border)', background: 'var(--bg1)', padding: '6px 8px', fontSize: 10, color: 'var(--text2)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {cell || '—'}
              </div>
            ))}
          </div>
        ))}
      </div>
    )
  }

  return (
    <pre style={{
      margin: 0,
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
      fontSize: 10,
      lineHeight: 1.7,
      color: 'var(--text2)',
      fontFamily: '"IBM Plex Mono",monospace',
    }}>
      {text}
    </pre>
  )
}

function FallbackNotice({ message }: { message: string }) {
  return (
    <div style={{ minHeight: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 18, color: 'var(--text3)', fontSize: 10, letterSpacing: 1, textAlign: 'center' }}>
      {message}
    </div>
  )
}

function buildPreviewModel(item: any): { kind: string; previewText?: string } {
  const ext = String(item.extension || '').toLowerCase()
  const group = String(item.file_type_group || '').toLowerCase()
  const fullText = String(item.extracted_text || item.content_preview || '')
  const previewText = fullText.slice(0, 20000)

  if (group === 'pdf') return { kind: 'pdf' }
  if (group === 'image') return { kind: 'image' }
  if (group === 'audio') return { kind: 'audio' }
  if (group === 'video') return { kind: 'video' }
  if (group === 'office' || OFFICE_EXTS.has(ext)) return { kind: 'office', previewText }
  if (group === 'text' || group === 'code' || TEXT_LIKE_EXTS.has(ext)) return { kind: 'text', previewText }
  if (previewText) return { kind: 'fallback-text', previewText }
  return { kind: 'unsupported' }
}

function formatDuration(totalSeconds: number) {
  const secs = Math.max(0, Math.floor(Number(totalSeconds) || 0))
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

function MetaRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between',
      padding: '5px 0', borderBottom: '1px solid var(--bg3)',
      gap: 8,
    }}>
      <span style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: 1, flexShrink: 0 }}>{label}</span>
      <span style={{
        fontSize: 10, color: 'var(--text2)',
        fontFamily: mono ? '"IBM Plex Mono",monospace' : undefined,
        textAlign: 'right', wordBreak: 'break-all',
      }}>{value || '—'}</span>
    </div>
  )
}
