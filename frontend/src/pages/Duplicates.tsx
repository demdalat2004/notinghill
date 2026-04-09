// NotingHill — pages/Duplicates.tsx
import { useEffect, useCallback } from 'react'
import { useStore } from '../store'
import { getExactDuplicates, getSimilarText, getSimilarImages, getDupStats, markReviewed } from '../api/client'
import { SectionHeader, EmptyState, Panel, StatCard } from '../components/ui'
import { formatSize, formatDate, truncate } from '../utils/helpers'

type DupTab = 'exact' | 'similar_text' | 'similar_image'

export default function Duplicates() {
  const { t, dupTab, setDupTab, dupGroups, setDupGroups, dupStats, setDupStats } = useStore()

  const loadStats = useCallback(async () => {
    try { setDupStats(await getDupStats()) } catch {}
  }, [])

  const loadGroups = useCallback(async (tab: DupTab) => {
    try {
      let data: any
      if (tab === 'exact') data = await getExactDuplicates()
      else if (tab === 'similar_text') data = await getSimilarText()
      else data = await getSimilarImages()
      setDupGroups(data.groups || [])
    } catch { setDupGroups([]) }
  }, [])

  useEffect(() => {
    loadStats()
    loadGroups(dupTab)
  }, [dupTab])

  const handleMarkReviewed = async (groupItemId: number) => {
    await markReviewed(groupItemId)
    loadGroups(dupTab)
  }

  const tabs: { id: DupTab; labelKey: string }[] = [
    { id: 'exact',        labelKey: 'dup_exact' },
    { id: 'similar_text', labelKey: 'dup_similar_text' },
    { id: 'similar_image',labelKey: 'dup_similar_image' },
  ]

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }} className="animate-fade-in">

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
        <StatCard
          label={t('dup_total_groups')}
          value={dupStats?.groups ?? 0}
          accent="var(--amber)"
        />
        <StatCard
          label={t('dup_wasted')}
          value={formatSize(dupStats?.wasted_bytes)}
          sub={t('dup_reclaimable')}
          accent="var(--red)"
        />
      </div>

      {/* Tabs */}
      <div style={{
        display: 'flex', gap: 2,
        borderBottom: '1px solid var(--border)',
        marginBottom: 20,
      }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setDupTab(tab.id)}
            style={{
              background: 'transparent',
              border: 'none',
              borderBottom: dupTab === tab.id ? '2px solid var(--cyan)' : '2px solid transparent',
              color: dupTab === tab.id ? 'var(--cyan)' : 'var(--text3)',
              fontFamily: '"IBM Plex Mono",monospace',
              fontSize: 11,
              letterSpacing: 2,
              padding: '10px 20px',
              cursor: 'pointer',
              marginBottom: -1,
              transition: 'all 0.15s',
            }}
          >
            {t(tab.labelKey as any)}
          </button>
        ))}
      </div>

      {/* Groups */}
      {dupGroups.length === 0 ? (
        <EmptyState icon="⊛" message={t('dup_no_groups')} />
      ) : (
        dupGroups.map((group: any) => (
          <DupGroupCard
            key={group.group_id}
            group={group}
            tab={dupTab}
            t={t}
            onMarkReviewed={handleMarkReviewed}
          />
        ))
      )}
    </div>
  )
}

function DupGroupCard({ group, tab, t, onMarkReviewed }: any) {
  const savings = group.total_size_bytes
    ? formatSize(group.total_size_bytes - (group.total_size_bytes / group.item_count))
    : '—'

  return (
    <div className="nh-card" style={{
      marginBottom: 12,
      border: '1px solid var(--border)',
      overflow: 'hidden',
    }}>
      {/* Group header */}
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg2)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{
            fontSize: 9, color: 'var(--amber)', letterSpacing: 2,
            border: '1px solid var(--amber)', padding: '2px 6px',
            fontFamily: '"Orbitron",monospace',
          }}>
            {t('dup_group')} #{group.group_id}
          </span>
          <span style={{ fontSize: 10, color: 'var(--text2)' }}>
            {group.item_count} files
          </span>
          <span style={{ fontSize: 10, color: 'var(--text3)' }}>
            {formatSize(group.total_size_bytes)} total
          </span>
        </div>
        <div style={{ fontSize: 9, color: 'var(--green)', letterSpacing: 1 }}>
          {savings} {t('dup_reclaimable')}
        </div>
      </div>

      {/* Items */}
      <div>
        {group.items?.map((item: any, idx: number) => (
          <div key={item.item_id} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '10px 16px',
            borderBottom: idx < group.items.length - 1 ? '1px solid var(--bg3)' : 'none',
            background: item.is_primary_candidate ? 'rgba(0,230,118,0.04)' : 'transparent',
          }}>
            {/* Primary indicator */}
            <div style={{ width: 4, alignSelf: 'stretch', flexShrink: 0 }}>
              {item.is_primary_candidate ? (
                <div style={{ width: 4, height: '100%', background: 'var(--green)' }} />
              ) : null}
            </div>

            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{
                fontSize: 11, color: 'var(--text)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {item.file_name}
              </div>
              <div style={{
                fontSize: 9, color: 'var(--text3)', marginTop: 2,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {item.full_path}
              </div>
            </div>

            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{ fontSize: 10, color: 'var(--text2)' }}>{formatSize(item.size_bytes)}</div>
              <div style={{ fontSize: 9, color: 'var(--text3)' }}>{formatDate(item.modified_ts)}</div>
            </div>

            {tab !== 'exact' && item.similarity_score != null && (
              <div style={{
                fontSize: 10, color: 'var(--purple)',
                width: 48, textAlign: 'right', flexShrink: 0,
                fontFamily: '"Orbitron",monospace',
              }}>
                {Math.round(item.similarity_score * 100)}%
              </div>
            )}

            <div style={{ flexShrink: 0 }}>
              {item.review_status === 'reviewed' ? (
                <span style={{ fontSize: 9, color: 'var(--green)', letterSpacing: 1 }}>✓ REVIEWED</span>
              ) : (
                <button
                  className="nh-btn"
                  style={{ fontSize: 9, padding: '3px 8px' }}
                  onClick={() => onMarkReviewed(item.group_item_id)}
                >
                  {t('dup_mark_reviewed')}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
