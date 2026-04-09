// NotingHill — components/ui/index.tsx
import { formatSize, formatDate, getBadgeClass, getTypeIcon } from '../../utils/helpers'

export function SectionHeader({ label, accent = 'var(--cyan)', children }: {
  label: string
  accent?: string
  children?: React.ReactNode
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <span style={{ display: 'block', width: 18, height: 3, background: `linear-gradient(90deg, ${accent}, transparent)`, borderRadius: 999, boxShadow: `0 0 18px ${accent}` }} />
        <span className="font-display" style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2.5, color: 'var(--text2)', textTransform: 'uppercase' }}>
          {label}
        </span>
      </div>
      {children}
    </div>
  )
}

export function StatCard({ label, value, sub, accent = 'var(--cyan)', onClick }: {
  label: string
  value: string | number
  sub?: string
  accent?: string
  onClick?: () => void
}) {
  return (
    <div
      className="nh-card animate-rise-in"
      onClick={onClick}
      style={{
        padding: '20px 20px 18px',
        cursor: onClick ? 'pointer' : 'default',
        overflow: 'hidden',
      }}
    >
      <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(circle at top right, ${accent}18, transparent 34%)`, pointerEvents: 'none' }} />
      <div style={{ position: 'relative', zIndex: 1 }}>
        <div style={{ fontSize: 10, color: 'var(--text3)', letterSpacing: 2.2, marginBottom: 12, textTransform: 'uppercase' }}>
          {label}
        </div>

        <div className="font-display" style={{ fontSize: 28, color: accent, fontWeight: 800, lineHeight: 1, textShadow: `0 0 24px ${accent}22` }}>
          {value}
        </div>

        {sub && (
          <div style={{ fontSize: 10, color: 'var(--text2)', marginTop: 10, letterSpacing: 1.1 }}>
            {sub}
          </div>
        )}
      </div>
    </div>
  )
}

export function Badge({ group }: { group: string }) {
  return (
    <span className={`badge ${getBadgeClass(group)}`}>
      <span>{getTypeIcon(group)}</span>
      <span>{group.toUpperCase()}</span>
    </span>
  )
}

export function FileRow({
  item,
  selected,
  onClick,
}: {
  item: any
  selected?: boolean
  onClick?: () => void
}) {
  return (
    <div
      className={`nh-card ${selected ? 'active' : ''} animate-rise-in`}
      onClick={onClick}
      style={{
        padding: '14px 16px',
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        cursor: 'pointer',
        marginBottom: 8,
        background: selected ? 'linear-gradient(180deg, rgba(103,232,249,0.10), rgba(103,232,249,0.04))' : undefined,
      }}
    >
      <div className="nh-card" style={{ width: 42, height: 42, minWidth: 42, borderRadius: 16, display: 'grid', placeItems: 'center', padding: 0, background: 'rgba(255,255,255,0.04)', boxShadow: 'none' }}>
        <span style={{ fontSize: 18, lineHeight: 1 }}>{getTypeIcon(item.file_type_group)}</span>
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {item.file_name}
        </div>

        <div style={{ fontSize: 10, color: 'var(--text3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: 4 }}>
          {item.full_path}
        </div>

        {item.snippet && (
          <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} dangerouslySetInnerHTML={{ __html: item.snippet }} />
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 7, flexShrink: 0 }}>
        <Badge group={item.file_type_group || 'other'} />
        <span style={{ fontSize: 10, color: 'var(--text3)' }}>{formatSize(item.size_bytes)}</span>
        <span style={{ fontSize: 10, color: 'var(--text3)' }}>{formatDate(item.modified_ts || item.best_time_ts)}</span>
      </div>
    </div>
  )
}

export function ProgressBar({ value, max, label }: { value: number; max: number; label?: string }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0

  return (
    <div>
      {label && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 10, color: 'var(--text2)', letterSpacing: 1 }}>{label}</span>
          <span className="font-display" style={{ fontSize: 11, color: 'var(--cyan)', fontWeight: 700 }}>{pct}%</span>
        </div>
      )}

      <div className="nh-progress">
        <div className="nh-progress-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export function Spinner() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60, color: 'var(--text2)', fontSize: 12, letterSpacing: 2, flexDirection: 'column', gap: 16 }}>
      <div style={{ width: 38, height: 38, border: '2px solid rgba(255,255,255,0.12)', borderTop: '2px solid var(--cyan)', borderRight: '2px solid var(--purple)', borderRadius: '50%', animation: 'spin 0.85s linear infinite' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <span className="font-display">LOADING...</span>
    </div>
  )
}

export function EmptyState({ icon = '◎', message }: { icon?: string; message: string }) {
  return (
    <div className="nh-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '54px 22px', color: 'var(--text3)', gap: 14, background: 'rgba(255,255,255,0.03)' }}>
      <div style={{ fontSize: 38, opacity: 0.5 }}>{icon}</div>
      <div style={{ fontSize: 12, letterSpacing: 1.2, textAlign: 'center', color: 'var(--text2)' }}>{message}</div>
    </div>
  )
}

export function Panel({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div className="nh-card" style={{ padding: '20px 22px', marginBottom: 16, ...style }}>
      <div style={{ position: 'relative', zIndex: 1 }}>{children}</div>
    </div>
  )
}
