import { useEffect, useMemo, useState } from 'react'
import { formatDateTime, formatSize } from '../../utils/helpers'

type ImageItem = any

interface Props {
  isOpen: boolean
  items: ImageItem[]
  currentIndex: number
  onClose: () => void
  onNavigate: (nextIndex: number) => void
  selectedIds: number[]
  onToggleSelect: (itemId: number) => void
  onOpenFile: (itemId: number) => void
}

const SLIDE_OPTIONS = [2, 3, 5, 8]

export default function ImageViewerModal({
  isOpen,
  items,
  currentIndex,
  onClose,
  onNavigate,
  selectedIds,
  onToggleSelect,
  onOpenFile,
}: Props) {
  const [zoom, setZoom] = useState(1)
  const [fitMode, setFitMode] = useState<'contain' | 'cover' | 'original'>('contain')
  const [slideshow, setSlideshow] = useState(false)
  const [slideSeconds, setSlideSeconds] = useState(3)
  const [showInfo, setShowInfo] = useState(true)

  const item = items[currentIndex]
  const parsedMeta = useMemo(() => {
    if (!item?.meta_json) return item?.meta || {}
    try {
      return JSON.parse(item.meta_json)
    } catch {
      return item?.meta || {}
    }
  }, [item])

  useEffect(() => {
    if (!isOpen) {
      setSlideshow(false)
      setZoom(1)
      return
    }

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowRight') onNavigate(Math.min(items.length - 1, currentIndex + 1))
      if (e.key === 'ArrowLeft') onNavigate(Math.max(0, currentIndex - 1))
      if (e.key === ' ') {
        e.preventDefault()
        setSlideshow(v => !v)
      }
      if (e.key === '+') setZoom(z => Math.min(4, Number((z + 0.2).toFixed(2))))
      if (e.key === '-') setZoom(z => Math.max(0.4, Number((z - 0.2).toFixed(2))))
      if (e.key.toLowerCase() === 'i') setShowInfo(v => !v)
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [isOpen, onClose, onNavigate, currentIndex, items.length])

  useEffect(() => {
    if (!isOpen || !slideshow || items.length <= 1) return
    const timer = window.setInterval(() => {
      onNavigate(currentIndex >= items.length - 1 ? 0 : currentIndex + 1)
    }, slideSeconds * 1000)
    return () => window.clearInterval(timer)
  }, [isOpen, slideshow, slideSeconds, items.length, currentIndex, onNavigate])

  useEffect(() => {
    setZoom(1)
  }, [currentIndex])

  if (!isOpen || !item) return null

  const isSelected = selectedIds.includes(item.item_id)
  const objectFit = fitMode === 'original' ? 'none' : fitMode
  const gpsText = item.gps_text || parsedMeta.gps_text
  const gpsLat = item.gps_lat ?? parsedMeta.gps_lat
  const gpsLon = item.gps_lon ?? parsedMeta.gps_lon

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(4, 10, 16, 0.92)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 1200,
      }}
      onClick={onClose}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderBottom: '1px solid var(--border)',
          background: 'rgba(8, 14, 22, 0.96)',
          gap: 12,
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontSize: 13, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {item.file_name}
          </div>
          <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 2 }}>
            {currentIndex + 1} / {items.length} · {formatSize(item.size_bytes)}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <button className="nh-btn" style={{ padding: '4px 8px', fontSize: 9 }} onClick={() => setShowInfo(v => !v)}>
            {showInfo ? 'HIDE INFO' : 'SHOW INFO'}
          </button>
          <button className="nh-btn" style={{ padding: '4px 8px', fontSize: 9 }} onClick={() => setZoom(z => Math.max(0.4, Number((z - 0.2).toFixed(2))))}>-</button>
          <button className="nh-btn" style={{ padding: '4px 8px', fontSize: 9 }} onClick={() => setZoom(1)}>100%</button>
          <button className="nh-btn" style={{ padding: '4px 8px', fontSize: 9 }} onClick={() => setZoom(z => Math.min(4, Number((z + 0.2).toFixed(2))))}>+</button>
          <button className={`nh-btn ${fitMode === 'contain' ? 'primary' : ''}`} style={{ padding: '4px 8px', fontSize: 9 }} onClick={() => setFitMode('contain')}>FIT</button>
          <button className={`nh-btn ${fitMode === 'cover' ? 'primary' : ''}`} style={{ padding: '4px 8px', fontSize: 9 }} onClick={() => setFitMode('cover')}>FILL</button>
          <button className={`nh-btn ${fitMode === 'original' ? 'primary' : ''}`} style={{ padding: '4px 8px', fontSize: 9 }} onClick={() => setFitMode('original')}>1:1</button>
          <button className={`nh-btn ${slideshow ? 'primary' : ''}`} style={{ padding: '4px 8px', fontSize: 9 }} onClick={() => setSlideshow(v => !v)}>
            {slideshow ? 'STOP' : 'PLAY'}
          </button>
          <select
            className="nh-input"
            style={{ width: 74, padding: '4px 6px', fontSize: 10 }}
            value={slideSeconds}
            onChange={e => setSlideSeconds(Number(e.target.value))}
          >
            {SLIDE_OPTIONS.map(sec => (
              <option key={sec} value={sec}>{sec}s</option>
            ))}
          </select>
          <button className={`nh-btn ${isSelected ? 'primary' : ''}`} style={{ padding: '4px 8px', fontSize: 9 }} onClick={() => onToggleSelect(item.item_id)}>
            {isSelected ? 'SELECTED' : 'SELECT'}
          </button>
          <button className="nh-btn primary" style={{ padding: '4px 8px', fontSize: 9 }} onClick={() => onOpenFile(item.item_id)}>
            OPEN
          </button>
          <button className="nh-btn" style={{ padding: '4px 8px', fontSize: 9 }} onClick={onClose}>CLOSE</button>
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, minHeight: 0 }} onClick={e => e.stopPropagation()}>
        <div style={{ flex: 1, minWidth: 0, position: 'relative', background: 'rgba(5, 10, 15, 0.82)' }}>
          <button
            className="nh-btn"
            style={{ position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)', zIndex: 2 }}
            onClick={() => onNavigate(Math.max(0, currentIndex - 1))}
            disabled={currentIndex <= 0}
          >
            ◀
          </button>

          <div style={{ position: 'absolute', inset: 0, overflow: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
            <img
              src={`/api/images/preview/${item.item_id}?max_edge=2200`}
              alt={item.file_name}
              style={{
                maxWidth: fitMode === 'original' ? 'none' : '100%',
                maxHeight: fitMode === 'original' ? 'none' : '100%',
                objectFit,
                transform: `scale(${zoom})`,
                transformOrigin: 'center center',
                transition: 'transform 0.15s ease',
                boxShadow: '0 0 20px rgba(0,0,0,0.35)',
                background: 'var(--bg1)',
              }}
            />
          </div>

          <button
            className="nh-btn"
            style={{ position: 'absolute', right: 16, top: '50%', transform: 'translateY(-50%)', zIndex: 2 }}
            onClick={() => onNavigate(Math.min(items.length - 1, currentIndex + 1))}
            disabled={currentIndex >= items.length - 1}
          >
            ▶
          </button>
        </div>

        {showInfo && (
          <aside style={{ width: 320, borderLeft: '1px solid var(--border)', background: 'rgba(8, 14, 22, 0.98)', padding: 14, overflowY: 'auto', flexShrink: 0 }}>
            <div className="nh-card" style={{ padding: 12, marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: 'var(--text3)', letterSpacing: 2, marginBottom: 8 }}>DETAILS</div>
              <MetaRow label="PATH" value={item.full_path} mono />
              <MetaRow label="SIZE" value={formatSize(item.size_bytes)} />
              <MetaRow label="DIMENSIONS" value={item.width && item.height ? `${item.width} × ${item.height}` : '—'} />
              <MetaRow label="TAKEN" value={formatDateTime(item.taken_ts || item.best_time_ts)} />
              <MetaRow label="MODIFIED" value={formatDateTime(item.modified_ts)} />
              <MetaRow label="CAMERA" value={item.camera_model || parsedMeta.camera_model || parsedMeta.Model || '—'} />
              <MetaRow label="GPS" value={gpsText || '—'} mono />
              {(gpsLat != null && gpsLon != null) && (
                <a
                  href={`https://maps.google.com/?q=${gpsLat},${gpsLon}`}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: 'var(--cyan)', fontSize: 10, textDecoration: 'none', display: 'inline-block', marginTop: 8 }}
                >
                  OPEN MAP ↗
                </a>
              )}
            </div>

            <div className="nh-card" style={{ padding: 12 }}>
              <div style={{ fontSize: 10, color: 'var(--text3)', letterSpacing: 2, marginBottom: 8 }}>EXIF</div>
              {Object.keys(parsedMeta || {}).length === 0 ? (
                <div style={{ fontSize: 10, color: 'var(--text3)' }}>No EXIF data</div>
              ) : (
                Object.entries(parsedMeta).map(([key, value]) => (
                  <MetaRow key={key} label={key.toUpperCase()} value={typeof value === 'object' ? JSON.stringify(value) : String(value)} mono />
                ))
              )}
            </div>
          </aside>
        )}
      </div>

      <div
        style={{
          borderTop: '1px solid var(--border)',
          background: 'rgba(8, 14, 22, 0.98)',
          padding: '10px 16px',
          display: 'flex',
          gap: 10,
          overflowX: 'auto',
        }}
        onClick={e => e.stopPropagation()}
      >
        {items.map((thumbItem, index) => (
          <button
            key={thumbItem.item_id}
            onClick={() => onNavigate(index)}
            style={{
              border: index === currentIndex ? '1px solid var(--cyan)' : '1px solid var(--border)',
              background: 'var(--bg1)',
              padding: 2,
              width: 86,
              height: 72,
              flexShrink: 0,
              cursor: 'pointer',
              position: 'relative',
            }}
          >
            <img
              src={`/api/images/thumb/${thumbItem.item_id}?size=160`}
              alt={thumbItem.file_name}
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            />
            {selectedIds.includes(thumbItem.item_id) && (
              <span style={{ position: 'absolute', top: 4, right: 4, background: 'var(--cyan)', color: '#041018', fontSize: 9, padding: '1px 4px' }}>SEL</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

function MetaRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, borderBottom: '1px solid var(--bg3)', padding: '5px 0' }}>
      <div style={{ fontSize: 9, color: 'var(--text3)', flexShrink: 0 }}>{label}</div>
      <div style={{ fontSize: 10, color: 'var(--text2)', textAlign: 'right', wordBreak: 'break-word', fontFamily: mono ? '"IBM Plex Mono", monospace' : undefined }}>
        {value || '—'}
      </div>
    </div>
  )
}
