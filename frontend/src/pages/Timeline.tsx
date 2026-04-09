// NotingHill — pages/Timeline.tsx
import { useEffect, useCallback, useMemo, useState } from 'react'
import { useStore } from '../store'
import {
  getTimelineBuckets,
  getBucketItems,
  getItem,
  openFile,
  revealFile,
  getItemRawUrl,
  getItemTextUrl,
} from '../api/client'
import { SectionHeader, EmptyState } from '../components/ui'
import { formatSize, formatDate, getTypeIcon, getTypeColor, formatDateTime } from '../utils/helpers'
import ImageViewerModal from '../components/images/ImageViewerModal'

const FILE_TYPES = ['', 'text', 'code', 'pdf', 'office', 'image', 'audio', 'video']
type ViewMode = 'icon' | 'thumb'

export default function Timeline() {
  const {
    t, tlZoom, setTlZoom, tlBuckets, setTlBuckets,
    tlSelectedBucket, setTlSelectedBucket,
    tlBucketItems, setTlBucketItems,
    tlTypeFilter, setTlTypeFilter,
  } = useStore()

  const [viewMode, setViewMode] = useState<ViewMode>('icon')

  const [previewItem, setPreviewItem] = useState<any | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const [imageModalOpen, setImageModalOpen] = useState(false)
  const [imageCurrentIndex, setImageCurrentIndex] = useState(0)

  const imageItems = useMemo(
    () => tlBucketItems.filter((x: any) => x.file_type_group === 'image'),
    [tlBucketItems]
  )

  const loadBuckets = useCallback(async () => {
    try {
      const data = await getTimelineBuckets({
        zoom: tlZoom,
        file_type: tlTypeFilter || undefined,
      })
      setTlBuckets(data.buckets || [])
    } catch (e) {
      console.error(e)
    }
  }, [tlZoom, tlTypeFilter, setTlBuckets])

  useEffect(() => {
    loadBuckets()
  }, [loadBuckets])

  const selectBucket = async (bucket: string) => {
    setTlSelectedBucket(bucket === tlSelectedBucket ? null : bucket)
    if (bucket === tlSelectedBucket) {
      setTlBucketItems([])
      return
    }
    try {
      const data = await getBucketItems(bucket, {
        zoom: tlZoom,
        file_type: tlTypeFilter || undefined,
        limit: 200,
      })
      setTlBucketItems(data.items || [])
    } catch {
      setTlBucketItems([])
    }
  }

  const openPreview = async (item: any) => {
    if (item.file_type_group === 'image') {
      const idx = imageItems.findIndex((x: any) => x.item_id === item.item_id)
      setImageCurrentIndex(idx >= 0 ? idx : 0)
      setImageModalOpen(true)
      return
    }

    setPreviewLoading(true)
    try {
      const detail = await getItem(item.item_id)
      setPreviewItem(detail || item)
    } catch {
      setPreviewItem(item)
    } finally {
      setPreviewLoading(false)
    }
  }

  const closePreview = () => {
    setPreviewItem(null)
  }

  const maxCount = Math.max(...tlBuckets.map((b: any) => b.file_count), 1)

  return (
    <>
      <div style={{ display: 'flex', height: 'calc(100vh - var(--topbar-height))', overflow: 'hidden' }}>
        {/* ── Left: buckets ── */}
        <div
          style={{
            width: 380,
            borderRight: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            background: 'var(--bg1)',
          }}
        >
          {/* Controls */}
          <div
            style={{
              padding: '12px 16px',
              borderBottom: '1px solid var(--border)',
              flexShrink: 0,
            }}
          >
            <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
              {(['year', 'month', 'day'] as const).map(z => (
                <button
                  key={z}
                  className={`nh-btn ${tlZoom === z ? 'primary' : ''}`}
                  style={{ flex: 1, fontSize: 9 }}
                  onClick={() => {
                    setTlZoom(z)
                    setTlSelectedBucket(null)
                    setTlBucketItems([])
                  }}
                >
                  {t(`tl_zoom_${z}` as any)}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
              <button
                className={`nh-btn ${viewMode === 'icon' ? 'primary' : ''}`}
                style={{ flex: 1, fontSize: 9 }}
                onClick={() => setViewMode('icon')}
              >
                ICON
              </button>
              <button
                className={`nh-btn ${viewMode === 'thumb' ? 'primary' : ''}`}
                style={{ flex: 1, fontSize: 9 }}
                onClick={() => setViewMode('thumb')}
              >
                THUMB
              </button>
            </div>

            {/* Type filter */}
            <select
              className="nh-input"
              style={{ fontSize: 10, padding: '6px 8px' }}
              value={tlTypeFilter}
              onChange={e => {
                setTlTypeFilter(e.target.value)
                setTlSelectedBucket(null)
              }}
            >
              <option value="">
                {t('all')} {t('type')}
              </option>
              {FILE_TYPES.filter(Boolean).map(ft => (
                <option key={ft} value={ft}>
                  {ft.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {/* Bar chart + bucket list */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 0' }}>
            {tlBuckets.length === 0 ? (
              <EmptyState icon="◈" message={t('tl_no_data')} />
            ) : (
              tlBuckets.map((b: any) => {
                const pct = Math.max(4, (b.file_count / maxCount) * 100)
                const selected = tlSelectedBucket === b.bucket
                return (
                  <div
                    key={b.bucket}
                    onClick={() => selectBucket(b.bucket)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      padding: '6px 16px',
                      cursor: 'pointer',
                      background: selected ? 'rgba(0,229,255,0.06)' : 'transparent',
                      borderLeft: selected ? '2px solid var(--cyan)' : '2px solid transparent',
                      transition: 'all 0.15s',
                    }}
                  >
                    {/* Bucket label */}
                    <div style={{ width: 80, flexShrink: 0 }}>
                      <div
                        style={{
                          fontSize: tlZoom === 'year' ? 14 : 11,
                          color: selected ? 'var(--cyan)' : 'var(--text)',
                          fontFamily: '"Orbitron",monospace',
                          fontWeight: tlZoom === 'year' ? 700 : 400,
                        }}
                      >
                        {formatBucket(b.bucket, tlZoom)}
                      </div>
                      <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 2 }}>
                        {formatSize(b.total_size)}
                      </div>
                    </div>

                    {/* Bar */}
                    <div style={{ flex: 1, height: 6, background: 'var(--bg3)', position: 'relative' }}>
                      <div
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          bottom: 0,
                          width: `${pct}%`,
                          background: selected
                            ? 'linear-gradient(90deg,var(--cyan),var(--green))'
                            : 'linear-gradient(90deg,var(--border2),var(--text3))',
                          boxShadow: selected ? '0 0 6px var(--cyan)' : 'none',
                          transition: 'width 0.4s ease',
                        }}
                      />
                    </div>

                    {/* Count */}
                    <div
                      style={{
                        width: 48,
                        textAlign: 'right',
                        flexShrink: 0,
                        fontSize: 11,
                        color: selected ? 'var(--cyan)' : 'var(--text2)',
                        fontFamily: '"Orbitron",monospace',
                      }}
                    >
                      {b.file_count}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* ── Right: bucket items ── */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
          {!tlSelectedBucket ? (
            <EmptyState icon="◈" message={t('tl_click_bucket')} />
          ) : (
            <>
              <SectionHeader label={tlSelectedBucket}>
                <span style={{ fontSize: 9, color: 'var(--text3)' }}>
                  {tlBucketItems.length} {t('tl_files')}
                </span>
              </SectionHeader>

              {/* Group by type */}
              {groupByType(tlBucketItems).map(([group, items]) => (
                <div key={group} style={{ marginBottom: 20 }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      marginBottom: 8,
                      fontSize: 9,
                      color: getTypeColor(group),
                      letterSpacing: 2,
                    }}
                  >
                    <span>{getTypeIcon(group)}</span>
                    <span>{group.toUpperCase()}</span>
                    <span style={{ color: 'var(--text3)' }}>({items.length})</span>
                  </div>

                  {items.map((item: any) => {
                    const showThumb = viewMode === 'thumb' && item.file_type_group === 'image'
                    return (
                      <div
                        key={item.item_id}
                        style={{
                          background: 'var(--bg1)',
                          border: '1px solid var(--border)',
                          padding: '8px 12px',
                          marginBottom: 3,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 10,
                          cursor: 'pointer',
                          transition: 'border-color 0.15s',
                        }}
                        onClick={() => openPreview(item)}
                        onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--cyan)')}
                        onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
                      >
                        {showThumb ? (
                          <img
                            src={`/api/images/thumb/${item.item_id}?size=120`}
                            alt={item.file_name}
                            style={{
                              width: 42,
                              height: 42,
                              objectFit: 'cover',
                              display: 'block',
                              border: '1px solid var(--border)',
                              background: 'var(--bg2)',
                              flexShrink: 0,
                            }}
                          />
                        ) : (
                          <span style={{ fontSize: 14, width: 18, textAlign: 'center', flexShrink: 0 }}>
                            {getTypeIcon(item.file_type_group)}
                          </span>
                        )}

                        <div style={{ flex: 1, overflow: 'hidden' }}>
                          <div
                            style={{
                              fontSize: 11,
                              color: 'var(--text)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {item.file_name}
                          </div>
                          <div
                            style={{
                              fontSize: 9,
                              color: 'var(--text3)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {item.full_path}
                          </div>
                        </div>

                        <div style={{ textAlign: 'right', flexShrink: 0 }}>
                          <div style={{ fontSize: 9, color: 'var(--text3)' }}>{formatSize(item.size_bytes)}</div>
                          <div style={{ fontSize: 9, color: 'var(--text3)' }}>{formatDate(item.best_time_ts)}</div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      <ImageViewerModal
        isOpen={imageModalOpen}
        items={imageItems}
        currentIndex={imageCurrentIndex}
        onClose={() => setImageModalOpen(false)}
        onNavigate={(nextIndex: number) => setImageCurrentIndex(nextIndex)}
        selectedIds={[]}
        onToggleSelect={() => {}}
        onOpenFile={(itemId: number) => openFile(itemId)}
      />

      <FilePreviewModal
        item={previewItem}
        loading={previewLoading}
        onClose={closePreview}
        onOpenFile={(itemId: number) => openFile(itemId)}
        onRevealFile={(itemId: number) => revealFile(itemId)}
      />
    </>
  )
}

function FilePreviewModal({
  item,
  loading,
  onClose,
  onOpenFile,
  onRevealFile,
}: {
  item: any | null
  loading?: boolean
  onClose: () => void
  onOpenFile: (itemId: number) => void
  onRevealFile: (itemId: number) => void
}) {
  if (!item && !loading) return null

  const rawUrl = item ? getItemRawUrl(item.item_id) : ''
  const textUrl = item ? getItemTextUrl(item.item_id, 50000) : ''

  const group = item?.file_type_group || ''
  const isTextLike = group === 'text' || group === 'code'
  const isPdf = group === 'pdf'
  const isAudio = group === 'audio'
  const isVideo = group === 'video'
  const isImage = group === 'image'
  const isOffice = group === 'office'

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(4, 10, 16, 0.88)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1300,
        padding: 24,
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: 'min(1100px, 96vw)',
          height: 'min(88vh, 900px)',
          background: 'var(--bg1)',
          border: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 10px 40px rgba(0,0,0,0.35)',
        }}
        onClick={e => e.stopPropagation()}
      >
        <div
          style={{
            padding: '12px 16px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            flexShrink: 0,
          }}
        >
          <div style={{ minWidth: 0, flex: 1 }}>
            <div
              style={{
                fontSize: 13,
                color: 'var(--text)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {loading ? 'Loading preview...' : item?.file_name || 'Preview'}
            </div>
            {!loading && item && (
              <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 2 }}>
                {getTypeIcon(item.file_type_group)} {item.file_type_group?.toUpperCase() || 'FILE'} · {formatSize(item.size_bytes)}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            {!loading && item && (
              <>
                <button className="nh-btn primary" style={{ fontSize: 9 }} onClick={() => onOpenFile(item.item_id)}>
                  OPEN
                </button>
                <button className="nh-btn" style={{ fontSize: 9 }} onClick={() => onRevealFile(item.item_id)}>
                  REVEAL
                </button>
              </>
            )}
            <button className="nh-btn" style={{ fontSize: 9 }} onClick={onClose}>
              CLOSE
            </button>
          </div>
        </div>

        <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
          <div style={{ flex: 1, minWidth: 0, background: 'var(--bg2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {loading ? (
              <div style={{ color: 'var(--text3)', fontSize: 11 }}>Loading...</div>
            ) : !item ? null : isPdf ? (
              <iframe
                src={rawUrl}
                title={item.file_name}
                style={{ width: '100%', height: '100%', border: 0, background: '#fff' }}
              />
            ) : isAudio ? (
              <div style={{ width: '100%', maxWidth: 720, padding: 24 }}>
                <div style={{ fontSize: 48, textAlign: 'center', marginBottom: 16 }}>{getTypeIcon('audio')}</div>
                <audio controls src={rawUrl} style={{ width: '100%' }} />
              </div>
            ) : isVideo ? (
              <video
                controls
                src={rawUrl}
                style={{ width: '100%', height: '100%', background: '#000' }}
              />
            ) : isImage ? (
              <img
                src={rawUrl}
                alt={item.file_name}
                style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', display: 'block' }}
              />
            ) : isTextLike ? (
              <iframe
                src={textUrl}
                title={`${item.file_name}-text-preview`}
                style={{ width: '100%', height: '100%', border: 0, background: '#fff' }}
              />
            ) : isOffice ? (
              <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
                {item.content_preview ? (
                  <div
                    style={{
                      padding: 16,
                      overflowY: 'auto',
                      fontSize: 11,
                      color: 'var(--text2)',
                      lineHeight: 1.7,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      fontFamily: '"IBM Plex Mono", monospace',
                    }}
                  >
                    {item.content_preview}
                  </div>
                ) : (
                  <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text3)' }}>
                    <div style={{ fontSize: 44, marginBottom: 10 }}>{getTypeIcon('office')}</div>
                    <div style={{ fontSize: 11, marginBottom: 8 }}>No inline office preview available</div>
                    <div style={{ fontSize: 10 }}>Use OPEN to view in the system application.</div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text3)' }}>
                <div style={{ fontSize: 44, marginBottom: 10 }}>{getTypeIcon(item.file_type_group || 'other')}</div>
                <div style={{ fontSize: 11, marginBottom: 8 }}>Preview is not available for this file type.</div>
                <div style={{ fontSize: 10 }}>Use OPEN to view in the system application.</div>
              </div>
            )}
          </div>

          {!loading && item && (
            <aside
              style={{
                width: 300,
                borderLeft: '1px solid var(--border)',
                background: 'var(--bg1)',
                padding: 14,
                overflowY: 'auto',
                flexShrink: 0,
              }}
            >
              <div className="nh-card" style={{ padding: 12 }}>
                <div style={{ fontSize: 10, color: 'var(--text3)', letterSpacing: 2, marginBottom: 8 }}>DETAILS</div>
                <MetaRow label="PATH" value={item.full_path} mono />
                <MetaRow label="SIZE" value={formatSize(item.size_bytes)} />
                <MetaRow label="MODIFIED" value={formatDateTime(item.modified_ts)} />
                <MetaRow label="CREATED" value={formatDateTime(item.created_ts)} />
                {item.width && item.height && <MetaRow label="DIMENSIONS" value={`${item.width} × ${item.height}`} />}
                {item.duration_seconds != null && (
                  <MetaRow
                    label="DURATION"
                    value={`${Math.floor(item.duration_seconds / 60)}:${String(Math.floor(item.duration_seconds % 60)).padStart(2, '0')}`}
                  />
                )}
                {item.title && <MetaRow label="TITLE" value={item.title} />}
                {item.artist && <MetaRow label="ARTIST" value={item.artist} />}
                {item.album && <MetaRow label="ALBUM" value={item.album} />}
                {item.camera_model && <MetaRow label="CAMERA" value={item.camera_model} />}
              </div>
            </aside>
          )}
        </div>
      </div>
    </div>
  )
}

function MetaRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        gap: 10,
        borderBottom: '1px solid var(--bg3)',
        padding: '5px 0',
      }}
    >
      <div style={{ fontSize: 9, color: 'var(--text3)', flexShrink: 0 }}>{label}</div>
      <div
        style={{
          fontSize: 10,
          color: 'var(--text2)',
          textAlign: 'right',
          wordBreak: 'break-word',
          fontFamily: mono ? '"IBM Plex Mono", monospace' : undefined,
        }}
      >
        {value || '—'}
      </div>
    </div>
  )
}

function formatBucket(bucket: string, zoom: string): string {
  if (!bucket) return '—'
  if (zoom === 'year') return bucket
  if (zoom === 'day') {
    const [y, m, d] = bucket.split('-')
    return `${d}/${m}/${y}`
  }
  const [y, m] = bucket.split('-')
  const months = ['', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
  return `${months[parseInt(m, 10)]} ${y}`
}

function groupByType(items: any[]): [string, any[]][] {
  const map = new Map<string, any[]>()
  for (const item of items) {
    const g = item.file_type_group || 'other'
    if (!map.has(g)) map.set(g, [])
    map.get(g)!.push(item)
  }
  return Array.from(map.entries())
}