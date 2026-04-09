// NotingHill — pages/Indexing.tsx
import { useEffect, useState, useCallback } from 'react'
import { useStore } from '../store'
import { listRoots, pickFolder, addRoot, removeRoot, reindexRoot, getJobs } from '../api/client'
import { SectionHeader, EmptyState, ProgressBar, Panel } from '../components/ui'
import { formatDuration } from '../utils/helpers'

export default function Indexing() {
  const { t, roots, setRoots, jobs, setJobs, activeJobs, setActiveJobs, queueSize, setQueueSize } = useStore()
  const [newPath, setNewPath] = useState('')
  const [newLabel, setNewLabel] = useState('')
  const [adding, setAdding] = useState(false)
  const [browsing, setBrowsing] = useState(false)
  const [addError, setAddError] = useState('')

  const loadData = useCallback(async () => {
    try {
      const [rootsData, jobsData] = await Promise.all([listRoots(), getJobs()])
      setRoots(rootsData.roots || [])
      setJobs(jobsData.recent || [])
      setActiveJobs(jobsData.active || [])
      setQueueSize(jobsData.queue_size || 0)
    } catch (e) {
      console.error(e)
    }
  }, [setActiveJobs, setJobs, setQueueSize, setRoots])

  useEffect(() => {
    loadData()
    const iv = setInterval(loadData, 3000)
    return () => clearInterval(iv)
  }, [loadData])

  const handleBrowse = async () => {
    setBrowsing(true)
    setAddError('')
    try {
      const data = await pickFolder()
      if (data?.path) {
        setNewPath(data.path)
        if (!newLabel.trim()) {
          const clean = data.path.replace(/[\\/]+$/, '')
          const name = clean.split(/[\\/]/).pop() || ''
          setNewLabel(name)
        }
      }
    } catch (e: any) {
      setAddError(e?.response?.data?.detail || 'Error opening folder dialog')
    }
    setBrowsing(false)
  }

  const handleAdd = async () => {
    let pathToAdd = newPath.trim()
    if (!pathToAdd) {
      setBrowsing(true)
      setAddError('')
      try {
        const data = await pickFolder()
        pathToAdd = (data?.path || '').trim()
        if (pathToAdd) {
          setNewPath(pathToAdd)
          if (!newLabel.trim()) {
            const clean = pathToAdd.replace(/[\\/]+$/, '')
            const name = clean.split(/[\\/]/).pop() || ''
            setNewLabel(name)
          }
        }
      } catch (e: any) {
        setAddError(e?.response?.data?.detail || 'Error opening folder dialog')
      }
      setBrowsing(false)
    }

    if (!pathToAdd) return

    setAdding(true)
    setAddError('')
    try {
      await addRoot({ root_path: pathToAdd, label: newLabel.trim() || undefined, start_now: true })
      setNewPath('')
      setNewLabel('')
      await loadData()
    } catch (e: any) {
      setAddError(e?.response?.data?.detail || 'Error adding folder')
    }
    setAdding(false)
  }

  const handleRemove = async (rootId: number) => {
    if (!confirm('Remove this root? Files will be marked as deleted.')) return
    await removeRoot(rootId)
    loadData()
  }

  const handleReindex = async (rootId: number) => {
    await reindexRoot(rootId, false)
    loadData()
  }

  const statusColor = (status: string) => {
    if (status === 'running') return 'var(--amber)'
    if (status === 'done') return 'var(--green)'
    if (status === 'error') return 'var(--red)'
    return 'var(--text3)'
  }

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }} className="animate-fade-in">
      <Panel>
        <SectionHeader label={t('idx_add_root')} />
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input
            className="nh-input"
            style={{ flex: 2, minWidth: 200 }}
            placeholder={t('idx_path_label')}
            value={newPath}
            onChange={e => setNewPath(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
          />
          <button
            className="nh-btn"
            style={{ padding: '8px 14px', flexShrink: 0 }}
            onClick={handleBrowse}
            disabled={adding || browsing}
          >
            {browsing ? '...' : (t('idx_browse_btn') === 'idx_browse_btn' ? 'BROWSE...' : t('idx_browse_btn'))}
          </button>
          <input
            className="nh-input"
            style={{ flex: 1, minWidth: 120 }}
            placeholder={t('idx_label_label')}
            value={newLabel}
            onChange={e => setNewLabel(e.target.value)}
          />
          <button
            className="nh-btn primary"
            style={{ padding: '8px 20px', flexShrink: 0 }}
            onClick={handleAdd}
            disabled={adding || browsing}
          >
            {adding ? '...' : t('idx_add_btn')}
          </button>
        </div>
        {addError && (
          <div style={{ marginTop: 8, fontSize: 10, color: 'var(--red)', letterSpacing: 1 }}>
            ✕ {addError}
          </div>
        )}
      </Panel>

      <Panel>
        <SectionHeader label={t('idx_roots')}>
          <span style={{ fontSize: 9, color: 'var(--text3)' }}>
            {t('dash_queue')}: {queueSize}
          </span>
        </SectionHeader>

        {roots.length === 0 ? (
          <EmptyState icon="⊞" message={t('dash_no_roots')} />
        ) : (
          roots.map((root: any) => {
            const activeJob = activeJobs.find((j: any) => j.root_id === root.root_id)
            const prog = activeJob?.progress || {}

            return (
              <div key={root.root_id} style={{
                background: 'var(--bg2)',
                border: '1px solid var(--border)',
                padding: '14px 16px',
                marginBottom: 8,
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <div style={{ fontSize: 12, color: 'var(--text)', marginBottom: 4 }}>
                      {root.root_label || root.root_path}
                    </div>
                    <div style={{ fontSize: 9, color: 'var(--text3)', marginBottom: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {root.root_path}
                    </div>
                    <div style={{ fontSize: 9, color: 'var(--text2)', letterSpacing: 1 }}>
                      {root.file_count} {t('idx_files')}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 6, flexShrink: 0, alignItems: 'center' }}>
                    {activeJob ? (
                      <span style={{ fontSize: 9, color: 'var(--amber)', letterSpacing: 2, animation: 'pulse 1s infinite' }}>
                        ◉ {t('idx_running')}
                      </span>
                    ) : (
                      <span className="status-dot active" />
                    )}
                    <button
                      className="nh-btn"
                      style={{ fontSize: 9, padding: '4px 10px' }}
                      onClick={() => handleReindex(root.root_id)}
                      disabled={!!activeJob}
                    >
                      {t('idx_reindex')}
                    </button>
                    <button
                      className="nh-btn danger"
                      style={{ fontSize: 9, padding: '4px 10px' }}
                      onClick={() => handleRemove(root.root_id)}
                    >
                      {t('idx_remove')}
                    </button>
                  </div>
                </div>

                {activeJob && (
                  <div style={{ marginTop: 10 }}>
                    <ProgressBar
                      value={prog.indexed || 0}
                      max={prog.queued || 1}
                      label={prog.current_file ? `${t('idx_current_file')}: ${prog.current_file.split('/').pop()?.split('\\').pop()}` : t('idx_running')}
                    />
                  </div>
                )}
              </div>
            )
          })
        )}
      </Panel>

      <Panel>
        <SectionHeader label={t('idx_jobs')} />
        {jobs.length === 0 ? (
          <div style={{ fontSize: 10, color: 'var(--text3)', padding: '12px 0' }}>{t('idx_no_jobs')}</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['#', t('idx_status'), t('idx_scanned'), t('idx_indexed'), t('idx_errors'), t('idx_duration'), 'ROOT'].map(h => (
                    <th key={h} style={{
                      padding: '6px 10px',
                      textAlign: 'left',
                      color: 'var(--text3)',
                      letterSpacing: 2,
                      fontSize: 9,
                      fontWeight: 400,
                    }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {jobs.map((job: any) => (
                  <tr key={job.job_id} style={{ borderBottom: '1px solid var(--bg3)' }}>
                    <td style={{ padding: '8px 10px', color: 'var(--text3)', fontFamily: '"Orbitron",monospace' }}>
                      {job.job_id}
                    </td>
                    <td style={{ padding: '8px 10px' }}>
                      <span style={{ color: statusColor(job.status), letterSpacing: 1, fontSize: 9 }}>
                        {job.status.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '8px 10px', color: 'var(--text2)' }}>{job.scanned_count}</td>
                    <td style={{ padding: '8px 10px', color: 'var(--green)' }}>{job.indexed_count}</td>
                    <td style={{ padding: '8px 10px', color: job.error_count > 0 ? 'var(--red)' : 'var(--text3)' }}>
                      {job.error_count}
                    </td>
                    <td style={{ padding: '8px 10px', color: 'var(--text3)' }}>
                      {job.started_ts ? formatDuration(job.started_ts, job.finished_ts) : '—'}
                    </td>
                    <td style={{ padding: '8px 10px', color: 'var(--text2)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {job.root_label || job.root_path || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  )
}
