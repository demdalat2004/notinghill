import { useEffect } from 'react'
import { useStore } from '../../store'

const NAV_ITEMS = [
  { id: 'dashboard', icon: '▣', labelKey: 'nav_dashboard' },
  { id: 'search', icon: '◎', labelKey: 'nav_search' },
  { id: 'images', icon: '🖼', labelKey: 'nav_images' },
  { id: 'multimedia', icon: '▶', labelKey: 'nav_multimedia' },
  { id: 'timeline', icon: '◈', labelKey: 'nav_timeline' },
  { id: 'duplicates', icon: '⊛', labelKey: 'nav_duplicates' },
  { id: 'indexing', icon: '⊞', labelKey: 'nav_indexing' },
  { id: 'settings', icon: '⚙', labelKey: 'nav_settings' },
]

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const { theme, lang, activeTab, setTheme, setLang, setActiveTab, t, dashData } = useStore()

  useEffect(() => {
    document.documentElement.classList.toggle('light', theme === 'light')
  }, [theme])

  const isIndexing = (dashData?.active_jobs?.length ?? 0) > 0

  return (
    <div className="app-shell">
      <div className="grid-bg" />
      <div className="scanline" />

      <header className="topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, minWidth: 0 }}>
          <div className="nh-card" style={{ width: 52, height: 52, borderRadius: 18, display: 'grid', placeItems: 'center', padding: 0, flexShrink: 0 }}>
            <div style={{ position: 'relative', width: 26, height: 26 }}>
              <div style={{ position: 'absolute', inset: 0, border: '1.5px solid var(--cyan)', transform: 'rotate(45deg)', borderRadius: 6 }} />
              <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', width: 8, height: 8, borderRadius: 999, background: 'linear-gradient(135deg, var(--cyan), var(--purple))', boxShadow: '0 0 18px rgba(103,232,249,0.55)' }} />
            </div>
          </div>

          <div style={{ minWidth: 0 }}>
            <div className="font-display" style={{ fontSize: 18, fontWeight: 800, color: 'var(--text)', letterSpacing: 4, lineHeight: 1 }}>
              NOTINGHILL
            </div>
            <div style={{ fontSize: 10, color: 'var(--text3)', letterSpacing: 2.8, marginTop: 6, textTransform: 'uppercase', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {t('app_subtitle')}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <div className="topbar-chip">
            <span className={`status-dot ${isIndexing ? 'running' : 'active'}`} />
            <span style={{ color: isIndexing ? 'var(--amber)' : 'var(--green)' }}>
              {isIndexing ? t('status_indexing') : t('status_online')}
            </span>
          </div>

          <button className="nh-btn ghost" style={{ padding: '9px 14px', fontSize: 10 }} onClick={() => setLang(lang === 'en' ? 'vi' : 'en')}>
            {lang === 'en' ? 'VI' : 'EN'}
          </button>

          <button className="nh-btn ghost" style={{ padding: '9px 14px', fontSize: 14 }} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? '☀' : '◑'}
          </button>
        </div>
      </header>

      <div className="shell-content">
        <nav className="sidebar">
          {NAV_ITEMS.map((item) => {
            const active = activeTab === item.id
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                title={t(item.labelKey)}
                className={`nav-btn-shell ${active ? 'active' : ''}`}
              >
                <span style={{ fontSize: 18, lineHeight: 1 }}>{item.icon}</span>
                <span style={{ fontSize: 8, letterSpacing: 1.2, fontFamily: '"IBM Plex Mono", monospace', textTransform: 'uppercase' }}>
                  {t(item.labelKey).slice(0, 4)}
                </span>
              </button>
            )
          })}
        </nav>

        <main className="main-content">{children}</main>
      </div>
    </div>
  )
}
