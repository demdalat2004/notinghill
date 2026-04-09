import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getImageItem, listImages, listRoots, openFile } from '../api/client'
import { EmptyState, Panel, SectionHeader, Spinner } from '../components/ui'
import ImageViewerModal from '../components/images/ImageViewerModal'
import { formatDate, formatSize } from '../utils/helpers'

const SORT_OPTIONS = [
  { value: 'best_time_ts DESC', label: 'TAKEN / TIME ↓' },
  { value: 'best_time_ts ASC', label: 'TAKEN / TIME ↑' },
  { value: 'modified_ts DESC', label: 'MODIFIED ↓' },
  { value: 'size_bytes DESC', label: 'SIZE ↓' },
  { value: 'file_name ASC', label: 'NAME A→Z' },
]

export default function Images() {
  const [roots, setRoots] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState('')
  const [items, setItems] = useState<any[]>([])
  const [viewerItems, setViewerItems] = useState<any[]>([])
  const [viewerOpen, setViewerOpen] = useState(false)
  const [viewerIndex, setViewerIndex] = useState(0)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [filters, setFilters] = useState({
    root_id: '',
    has_gps: false,
    sort: 'best_time_ts DESC',
  })
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    listRoots().then(data => setRoots(data.roots || []))
  }, [])

  const fetchImages = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, any> = {
        q: query,
        root_id: filters.root_id || undefined,
        has_gps: filters.has_gps ? 1 : undefined,
        order_by: filters.sort,
        limit: 240,
      }
      const data = await listImages(params)
      const nextItems = data.results || []
      setItems(nextItems)
      setViewerItems(nextItems)
      setSelectedIds(prev => prev.filter(id => nextItems.some((item: any) => item.item_id === id)))
    } catch {
      setItems([])
      setViewerItems([])
    }
    setLoading(false)
  }, [query, filters])

  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current)
    debounceRef.current = window.setTimeout(() => {
      fetchImages()
    }, 220)
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
    }
  }, [fetchImages])

  const selectedCount = selectedIds.length
  const selectedSize = useMemo(
    () => items.filter(item => selectedIds.includes(item.item_id)).reduce((sum, item) => sum + (item.size_bytes || 0), 0),
    [items, selectedIds],
  )

  const toggleSelect = (itemId: number) => {
    setSelectedIds(prev => prev.includes(itemId) ? prev.filter(id => id !== itemId) : [...prev, itemId])
  }

  const openViewer = async (index: number) => {
    const baseItem = items[index]
    if (!baseItem) return
    try {
      const detail = await getImageItem(baseItem.item_id)
      const next = [...items]
      next[index] = { ...baseItem, ...detail }
      setItems(next)
      setViewerItems(next)
    } catch {
      setViewerItems(items)
    }
    setViewerIndex(index)
    setViewerOpen(true)
  }

  const handleOpenFile = (itemId: number) => {
    openFile(itemId)
  }

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - var(--topbar-height))', overflow: 'hidden' }}>
      <aside
        style={{
          width: 240,
          borderRight: '1px solid var(--border)',
          background: 'var(--bg1)',
          padding: 16,
          overflowY: 'auto',
          flexShrink: 0,
        }}
      >
        <SectionHeader label="IMAGE BROWSER" />

        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: 2, marginBottom: 8 }}>SEARCH</div>
          <input className="nh-input" value={query} onChange={e => setQuery(e.target.value)} placeholder="name, path, camera, gps..." />
        </div>

        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: 2, marginBottom: 8 }}>ROOT</div>
          <select className="nh-input" value={filters.root_id} onChange={e => setFilters(v => ({ ...v, root_id: e.target.value }))}>
            <option value="">ALL FOLDERS</option>
            {roots.map((root: any) => (
              <option key={root.root_id} value={root.root_id}>{root.root_label || root.root_path}</option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: 2, marginBottom: 8 }}>SORT</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {SORT_OPTIONS.map(opt => (
              <button
                key={opt.value}
                className={`nh-btn ${filters.sort === opt.value ? 'primary' : ''}`}
                style={{ textAlign: 'left', padding: '6px 8px', fontSize: 9 }}
                onClick={() => setFilters(v => ({ ...v, sort: opt.value }))}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <Panel style={{ padding: 12 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10, color: 'var(--text2)' }}>
            <input type="checkbox" checked={filters.has_gps} onChange={e => setFilters(v => ({ ...v, has_gps: e.target.checked }))} />
            GPS ONLY
          </label>
        </Panel>

        <Panel style={{ padding: 12 }}>
          <div style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: 2, marginBottom: 8 }}>SELECTION</div>
          <div style={{ fontSize: 12, color: 'var(--cyan)', marginBottom: 4 }}>{selectedCount}</div>
          <div style={{ fontSize: 10, color: 'var(--text2)' }}>{formatSize(selectedSize)}</div>
          <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
            <button className="nh-btn" style={{ flex: 1, fontSize: 9 }} onClick={() => setSelectedIds([])}>CLEAR</button>
            <button className="nh-btn" style={{ flex: 1, fontSize: 9 }} onClick={() => setSelectedIds(items.map(item => item.item_id))}>ALL</button>
          </div>
        </Panel>
      </aside>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', background: 'var(--bg1)', flexShrink: 0, display: 'flex', justifyContent: 'space-between', gap: 12 }}>
          <div style={{ fontSize: 10, color: 'var(--text3)', letterSpacing: 2 }}>
            IMAGES: <span style={{ color: 'var(--cyan)' }}>{items.length}</span>
          </div>
          <div style={{ fontSize: 10, color: 'var(--text3)', letterSpacing: 2 }}>
            DOUBLE CLICK TO OPEN VIEWER · SPACE IN VIEWER = SLIDESHOW
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {loading && <Spinner />}
          {!loading && items.length === 0 && <EmptyState icon="🖼" message="NO IMAGES FOUND" />}

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
              gap: 12,
            }}
          >
            {items.map((item, index) => {
              const isSelected = selectedIds.includes(item.item_id)
              return (
                <div
                  key={item.item_id}
                  className={`nh-card ${isSelected ? 'active' : ''}`}
                  style={{ padding: 8, cursor: 'pointer' }}
                  onDoubleClick={() => openViewer(index)}
                >
                  <div style={{ position: 'relative', marginBottom: 8 }}>
                    <img
                      src={`/api/images/thumb/${item.item_id}?size=320`}
                      alt={item.file_name}
                      style={{ width: '100%', aspectRatio: '1 / 1', objectFit: 'cover', display: 'block', background: 'var(--bg2)' }}
                      onClick={() => openViewer(index)}
                    />
                    <label
                      style={{
                        position: 'absolute',
                        top: 8,
                        left: 8,
                        background: 'rgba(5,10,15,0.88)',
                        border: '1px solid var(--border)',
                        padding: '3px 5px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        fontSize: 9,
                        color: 'var(--text2)',
                      }}
                      onClick={e => e.stopPropagation()}
                    >
                      <input type="checkbox" checked={isSelected} onChange={() => toggleSelect(item.item_id)} />
                      SEL
                    </label>
                    {item.gps_lat != null && item.gps_lon != null && (
                      <span style={{ position: 'absolute', top: 8, right: 8, background: 'rgba(0,229,255,0.15)', color: 'var(--cyan)', border: '1px solid var(--cyan)', padding: '2px 5px', fontSize: 9 }}>
                        GPS
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: 11, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={item.file_name}>
                    {item.file_name}
                  </div>
                  <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.width && item.height ? `${item.width}×${item.height}` : '—'} · {formatSize(item.size_bytes)}
                  </div>
                  <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 3 }}>
                    {formatDate(item.taken_ts || item.sort_time_ts || item.modified_ts)}
                  </div>
                  <div style={{ fontSize: 9, color: 'var(--text2)', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={item.full_path}>
                    {item.full_path}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      <ImageViewerModal
        isOpen={viewerOpen}
        items={viewerItems}
        currentIndex={viewerIndex}
        onClose={() => setViewerOpen(false)}
        onNavigate={(nextIndex) => {
          const safeIndex = Math.min(Math.max(nextIndex, 0), Math.max(viewerItems.length - 1, 0))
          setViewerIndex(safeIndex)
          const target = viewerItems[safeIndex]
          if (target && !target.meta && !target.gps_text) {
            getImageItem(target.item_id)
              .then(detail => {
                setViewerItems(prev => prev.map((it, idx) => idx === safeIndex ? { ...it, ...detail } : it))
                setItems(prev => prev.map((it, idx) => idx === safeIndex ? { ...it, ...detail } : it))
              })
              .catch(() => undefined)
          }
        }}
        selectedIds={selectedIds}
        onToggleSelect={toggleSelect}
        onOpenFile={handleOpenFile}
      />
    </div>
  )
}
