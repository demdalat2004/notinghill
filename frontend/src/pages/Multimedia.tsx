import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useStore } from '../store'
import { searchFiles, getItem, getItemRawUrl, openFile, revealFile } from '../api/client'
import { Badge, EmptyState, SectionHeader } from '../components/ui'
import { formatDateTime, formatSize, getTypeIcon } from '../utils/helpers'

type MediaKind = 'all' | 'audio' | 'video'

export default function Multimedia() {
  const { t } = useStore()
  const [query, setQuery] = useState('')
  const [kind, setKind] = useState<MediaKind>('all')
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedItem, setSelectedItem] = useState<any | null>(null)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [autoplay, setAutoplay] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const doSearch = useCallback(async (q: string, mediaKind: MediaKind) => {
    setLoading(true)
    try {
      const baseParams: Record<string, any> = { q, order_by: 'modified_ts DESC', limit: 120 }
      const requests = mediaKind === 'all'
        ? [searchFiles({ ...baseParams, file_type: 'audio' }), searchFiles({ ...baseParams, file_type: 'video' })]
        : [searchFiles({ ...baseParams, file_type: mediaKind })]

      const results = await Promise.all(requests)
      const merged = results
        .flatMap((r) => r?.results || [])
        .filter(Boolean)

      const deduped = Array.from(new Map(merged.map((item) => [item.item_id, item])).values())
      deduped.sort((a: any, b: any) => {
        const ta = a.modified_ts || a.best_time_ts || 0
        const tb = b.modified_ts || b.best_time_ts || 0
        return tb - ta
      })

      setItems(deduped)

      if (deduped.length === 0) {
        setSelectedItem(null)
        setSelectedIndex(-1)
      } else if (selectedItem) {
        const idx = deduped.findIndex((it: any) => it.item_id === selectedItem.item_id)
        if (idx >= 0) {
          setSelectedIndex(idx)
        } else {
          setSelectedItem(null)
          setSelectedIndex(-1)
        }
      }
    } catch {
      setItems([])
      setSelectedItem(null)
      setSelectedIndex(-1)
    }
    setLoading(false)
  }, [selectedItem])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      doSearch(query, kind)
    }, 250)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query, kind, doSearch])

  const selectItem = useCallback(async (item: any, index: number) => {
    setSelectedIndex(index)
    try {
      const detail = await getItem(item.item_id)
      setSelectedItem(detail)
    } catch {
      setSelectedItem(item)
    }
  }, [])

  const selectedRawUrl = useMemo(() => {
    if (!selectedItem?.item_id) return ''
    return getItemRawUrl(selectedItem.item_id)
  }, [selectedItem])

  const handlePrev = useCallback(() => {
    if (items.length === 0) return
    const nextIndex = selectedIndex > 0 ? selectedIndex - 1 : items.length - 1
    const target = items[nextIndex]
    if (target) selectItem(target, nextIndex)
  }, [items, selectedIndex, selectItem])

  const handleNext = useCallback(() => {
    if (items.length === 0) return
    const nextIndex = selectedIndex >= 0 && selectedIndex < items.length - 1 ? selectedIndex + 1 : 0
    const target = items[nextIndex]
    if (target) selectItem(target, nextIndex)
  }, [items, selectedIndex, selectItem])

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (!selectedItem) return
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        handlePrev()
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        handleNext()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [selectedItem, handlePrev, handleNext])

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 52px)', overflow: 'hidden' }}>
      <aside style={{
        width: 280,
        borderRight: '1px solid var(--border)',
        background: 'var(--bg1)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
      }}>
        <div style={{ padding: '16px 14px 12px', borderBottom: '1px solid var(--border)' }}>
          <SectionHeader label={t('nav_multimedia')} />
          <input
            className="nh-input"
            style={{ fontSize: 12, marginBottom: 10 }}
            placeholder={t('media_search_placeholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {[
              { id: 'all', label: t('all') },
              { id: 'audio', label: t('file_types.audio') },
              { id: 'video', label: t('file_types.video') },
            ].map((opt) => (
              <button
                key={opt.id}
                className={`nh-btn ${kind === opt.id ? 'primary' : ''}`}
                style={{ fontSize: 10, padding: '6px 10px' }}
                onClick={() => setKind(opt.id as MediaKind)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ padding: '8px 14px', borderBottom: '1px solid var(--border)', fontSize: 10, color: 'var(--text3)', letterSpacing: 1.4 }}>
          {t('search_results')}: {items.length}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 10 }}>
          {!loading && items.length === 0 && (
            <EmptyState icon="♫" message={t('media_no_results')} />
          )}

          {items.map((item, index) => {
            const active = selectedItem?.item_id === item.item_id
            return (
              <button
                key={item.item_id}
                onClick={() => selectItem(item, index)}
                className={`nh-card ${active ? 'active' : ''}`}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: '12px 12px',
                  marginBottom: 8,
                  background: active ? 'linear-gradient(180deg, rgba(103,232,249,0.10), rgba(103,232,249,0.04))' : undefined,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div className="nh-card" style={{ width: 42, height: 42, minWidth: 42, borderRadius: 14, display: 'grid', placeItems: 'center', padding: 0, boxShadow: 'none', background: 'rgba(255,255,255,0.04)' }}>
                    <span style={{ fontSize: 18 }}>{getTypeIcon(item.file_type_group)}</span>
                  </div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontSize: 12, color: 'var(--text)', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.file_name}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text3)', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.full_path}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginTop: 10, alignItems: 'center' }}>
                  <Badge group={item.file_type_group || 'other'} />
                  <div style={{ fontSize: 10, color: 'var(--text3)' }}>{formatSize(item.size_bytes || 0)}</div>
                </div>
              </button>
            )
          })}
        </div>
      </aside>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {!selectedItem ? (
          <div style={{ padding: 18, flex: 1 }}>
            <EmptyState icon="▶" message={t('media_pick_item')} />
          </div>
        ) : (
          <>
            <div style={{ padding: '16px 18px 10px', borderBottom: '1px solid var(--border)', background: 'var(--bg1)', flexShrink: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start' }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 22, marginBottom: 8 }}>{getTypeIcon(selectedItem.file_type_group)}</div>
                  <div style={{ fontSize: 15, color: 'var(--text)', fontWeight: 700, wordBreak: 'break-word' }}>
                    {selectedItem.file_name}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 6, wordBreak: 'break-all' }}>
                    {selectedItem.full_path}
                  </div>
                </div>
                <Badge group={selectedItem.file_type_group || 'other'} />
              </div>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: 18 }}>
              <div className="nh-card" style={{ padding: 16, marginBottom: 16 }}>
                <SectionHeader label={t('media_player')}>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button className="nh-btn" style={{ fontSize: 10 }} onClick={handlePrev}>{t('media_prev')}</button>
                    <button className="nh-btn" style={{ fontSize: 10 }} onClick={handleNext}>{t('media_next')}</button>
                    <button className={`nh-btn ${autoplay ? 'primary' : ''}`} style={{ fontSize: 10 }} onClick={() => setAutoplay((v) => !v)}>
                      {t('media_autoplay')}
                    </button>
                  </div>
                </SectionHeader>

                {selectedItem.file_type_group === 'audio' ? (
                  <div>
                    <audio
                      key={selectedItem.item_id}
                      controls
                      autoPlay
                      style={{ width: '100%' }}
                      src={selectedRawUrl}
                      onEnded={() => {
                        if (autoplay) handleNext()
                      }}
                    />
                    <div style={{ marginTop: 14, fontSize: 11, color: 'var(--text2)', lineHeight: 1.8 }}>
                      {t('media_audio_ready')}
                    </div>
                  </div>
                ) : (
                  <div>
                    <video
                      key={selectedItem.item_id}
                      controls
                      autoPlay
                      style={{ width: '100%', maxHeight: '62vh', borderRadius: 14, background: '#000' }}
                      src={selectedRawUrl}
                      onEnded={() => {
                        if (autoplay) handleNext()
                      }}
                    />
                  </div>
                )}
              </div>

              <div className="nh-card" style={{ padding: 16, marginBottom: 16 }}>
                <SectionHeader label={t('preview_metadata')} />
                <MetaRow label={t('path')} value={selectedItem.full_path} mono />
                <MetaRow label={t('size')} value={formatSize(selectedItem.size_bytes || 0)} />
                <MetaRow label={t('modified')} value={formatDateTime(selectedItem.modified_ts)} />
                <MetaRow label={t('created')} value={formatDateTime(selectedItem.created_ts)} />
                {selectedItem.duration_seconds && (
                  <MetaRow
                    label={t('media_duration')}
                    value={`${Math.floor(selectedItem.duration_seconds / 60)}:${String(Math.floor(selectedItem.duration_seconds % 60)).padStart(2, '0')}`}
                  />
                )}
                {selectedItem.title && <MetaRow label="TITLE" value={selectedItem.title} />}
                {selectedItem.artist && <MetaRow label="ARTIST" value={selectedItem.artist} />}
                {selectedItem.album && <MetaRow label="ALBUM" value={selectedItem.album} />}
              </div>

              <div className="nh-card" style={{ padding: 16 }}>
                <SectionHeader label={t('media_actions')} />
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button className="nh-btn primary" style={{ fontSize: 10 }} onClick={() => openFile(selectedItem.item_id)}>
                    {t('preview_open')}
                  </button>
                  <button className="nh-btn" style={{ fontSize: 10 }} onClick={() => revealFile(selectedItem.item_id)}>
                    {t('preview_reveal')}
                  </button>
                  <a className="nh-btn" style={{ fontSize: 10, textDecoration: 'none' }} href={getItemRawUrl(selectedItem.item_id, true)}>
                    {t('media_download')}
                  </a>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function MetaRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      padding: '6px 0',
      borderBottom: '1px solid var(--bg3)',
      gap: 8,
    }}>
      <span style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: 1, flexShrink: 0 }}>{label}</span>
      <span style={{
        fontSize: 10,
        color: 'var(--text2)',
        fontFamily: mono ? '"IBM Plex Mono", monospace' : undefined,
        textAlign: 'right',
        wordBreak: 'break-all',
      }}>{value || '—'}</span>
    </div>
  )
}
