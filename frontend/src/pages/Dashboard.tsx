// NotingHill — pages/Dashboard.tsx
import { useEffect, useCallback, useState, useRef } from 'react'
import { useStore } from '../store'
import { askSearch, getDashboard, getLlmSettings, openFile, revealFile } from '../api/client'
import type { AskSearchResponse } from '../api/client'
import { StatCard, SectionHeader, Panel, Spinner, EmptyState, ProgressBar, Badge } from '../components/ui'
import { formatSize, formatDateTime } from '../utils/helpers'

type ChatMessage = {
  role: 'user' | 'assistant'
  text: string
  ts: number
  results?: any[]
  model?: string
}

const isEnabledValue = (value: unknown) => {
  const normalized = `${value ?? ''}`.trim().toLowerCase()
  return normalized === '1' || normalized === 'true' || normalized === 'yes' || normalized === 'on'
}

// Adaptive poll: fast when jobs are active, slow/off when idle
const POLL_ACTIVE_MS = 3000
const POLL_IDLE_MS   = 15000

export default function Dashboard() {
  const { t, dashData, dashLoading, setDashData, setDashLoading, setActiveTab } = useStore()
  const [chatInput, setChatInput]     = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [llmEnabled, setLlmEnabled]   = useState(false)
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const load = useCallback(async () => {
    setDashLoading(true)
    try {
      const data = await getDashboard()
      setDashData(data)
      return data
    } catch (e) {
      console.error(e)
      return null
    } finally {
      setDashLoading(false)
    }
  }, [setDashData, setDashLoading])

  const loadLlmSettings = useCallback(async () => {
    try {
      const data = await getLlmSettings()
      setLlmEnabled(isEnabledValue(data?.llm_enabled))
    } catch {
      setLlmEnabled(false)
    }
  }, [])

  // Smart adaptive polling
  const scheduleNextPoll = useCallback((data: any) => {
    if (pollRef.current) clearTimeout(pollRef.current)
    const hasActiveJobs = (data?.active_jobs?.length ?? 0) > 0
    const delay = hasActiveJobs ? POLL_ACTIVE_MS : POLL_IDLE_MS
    pollRef.current = setTimeout(async () => {
      const next = await load()
      scheduleNextPoll(next)
    }, delay)
  }, [load])

  useEffect(() => {
    load().then(scheduleNextPoll)
    loadLlmSettings()
    return () => {
      if (pollRef.current) clearTimeout(pollRef.current)
    }
  }, [load, loadLlmSettings, scheduleNextPoll])

  useEffect(() => {
    const handleLlmUpdate = () => loadLlmSettings()
    window.addEventListener('llm-settings-updated', handleLlmUpdate)
    return () => window.removeEventListener('llm-settings-updated', handleLlmUpdate)
  }, [loadLlmSettings])

  const handleAsk = async () => {
    const q = chatInput.trim()
    if (!q || chatLoading || !llmEnabled) return

    setChatMessages(prev => [...prev, { role: 'user', text: q, ts: Date.now() }])
    setChatInput('')
    setChatLoading(true)

    try {
      const data: AskSearchResponse = await askSearch({ q, limit: 8 })

      // data.answer is now top-level (fixed response shape)
      const answer = data.answer || 'No answer returned.'
      const results = data.results || []

      setChatMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: answer,
          ts: Date.now(),
          results,
          model: data.model ? `${data.provider}/${data.model}` : undefined,
        },
      ])
    } catch (e: any) {
      const errText =
        e?.response?.data?.detail ||
        e?.message ||
        'Search assistant request failed.'
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', text: errText, ts: Date.now(), results: [] },
      ])
    } finally {
      setChatLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleAsk()
    }
  }

  const d = dashData
  if (dashLoading && !d) return <Spinner />

  const stats      = d?.stats ?? {}
  const dupStats   = d?.dup_stats ?? {}
  const recent     = d?.recent_files ?? []
  const activeJobs = d?.active_jobs ?? []
  const roots      = d?.roots ?? []
  const insights   = d?.insights ?? []

  return (
    <div className="layout-page animate-fade-in" style={{ maxWidth: 1280, margin: '0 auto' }}>
      <div className="stat-grid-responsive" style={{ marginBottom: 20 }}>
        <StatCard label={t('dash_total_files')} value={(stats.total_files ?? 0).toLocaleString()} sub={formatSize(stats.total_size)} accent="var(--cyan)" />
        <StatCard label={t('dash_total_size')} value={formatSize(stats.total_size)} sub={`${(stats.total_files ?? 0).toLocaleString()} files`} accent="var(--amber)" />
        <StatCard label={t('dash_duplicates')} value={dupStats.groups ?? 0} sub={formatSize(dupStats.wasted_bytes)} accent="var(--green)" onClick={() => setActiveTab('duplicates')} />
        <StatCard label={t('dash_errors')} value={stats.errors ?? 0} sub="index errors" accent={stats.errors > 0 ? 'var(--red)' : 'var(--text3)'} onClick={() => setActiveTab('indexing')} />
      </div>

      <Panel>
        <SectionHeader label="AI CHAT" accent="var(--purple)">
          <div style={{ fontSize: 10, color: llmEnabled ? 'var(--green)' : 'var(--amber)', letterSpacing: 1 }}>
            {llmEnabled ? 'LLM ENABLED' : 'LLM DISABLED'}
          </div>
        </SectionHeader>

        <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 0.9fr', gap: 16 }}>
          {/* Chat thread */}
          <div className="nh-card" style={{ padding: 16, minHeight: 360, background: 'rgba(255,255,255,0.03)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxHeight: 420, overflowY: 'auto', paddingRight: 4 }}>
              {chatMessages.length === 0 ? (
                <EmptyState
                  icon="✦"
                  message={
                    llmEnabled
                      ? 'Ask naturally about your indexed files, documents, images, audio, duplicates, or timeline.'
                      : 'Enable LLM in Settings first, then come back here to ask natural-language questions.'
                  }
                />
              ) : (
                chatMessages.map((msg, index) => (
                  <div
                    key={`${msg.ts}-${index}`}
                    style={{
                      alignSelf: msg.role === 'user' ? 'flex-end' : 'stretch',
                      maxWidth: msg.role === 'user' ? '82%' : '100%',
                      marginLeft: msg.role === 'user' ? 'auto' : 0,
                    }}
                  >
                    <div style={{ fontSize: 9, color: msg.role === 'user' ? 'var(--cyan)' : 'var(--purple)', letterSpacing: 2, marginBottom: 6 }}>
                      {msg.role === 'user' ? 'YOU' : `ASSISTANT${msg.model ? ` · ${msg.model}` : ''}`}
                    </div>
                    <div
                      className="nh-card"
                      style={{
                        padding: '14px 16px',
                        background: msg.role === 'user' ? 'rgba(103,232,249,0.08)' : 'rgba(167,139,250,0.07)',
                        borderColor: msg.role === 'user' ? 'rgba(103,232,249,0.22)' : 'rgba(167,139,250,0.22)',
                        borderRadius: 18,
                      }}
                    >
                      <div style={{ whiteSpace: 'pre-wrap', color: 'var(--text2)', fontSize: 12, lineHeight: 1.7 }}>{msg.text}</div>

                      {msg.role === 'assistant' && msg.results && msg.results.length > 0 && (
                        <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {msg.results.slice(0, 5).map((item: any) => (
                            <div
                              key={item.item_id}
                              style={{
                                padding: '10px 12px',
                                borderRadius: 14,
                                background: 'rgba(255,255,255,0.03)',
                                border: '1px solid var(--border)',
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', marginBottom: 6 }}>
                                <div style={{ fontSize: 11, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                  {item.file_name || item.title || item.full_path || `Item #${item.item_id}`}
                                </div>
                                <Badge group={item.file_type_group || 'other'} />
                              </div>
                              <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {item.full_path || item.path || ''}
                              </div>
                              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                <button className="nh-btn" style={{ fontSize: 9, padding: '7px 12px' }} onClick={() => openFile(item.item_id)}>OPEN</button>
                                <button className="nh-btn" style={{ fontSize: 9, padding: '7px 12px' }} onClick={() => revealFile(item.item_id)}>SHOW IN FOLDER</button>
                                <button className="nh-btn" style={{ fontSize: 9, padding: '7px 12px' }} onClick={() => setActiveTab('search')}>GO TO SEARCH</button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Input panel */}
          <div className="nh-card" style={{ padding: 16, background: 'rgba(255,255,255,0.03)' }}>
            <div style={{ fontSize: 10, color: 'var(--text3)', letterSpacing: 2, marginBottom: 10 }}>QUICK PROMPTS</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[
                'Find PDF files about contracts from February.',
                'Show recent images taken in Da Lat.',
                'Which MP3 files are duplicates?',
                'Summarize files indexed this week.',
                'Find spreadsheets mentioning invoice or payment.',
              ].map(prompt => (
                <button
                  key={prompt}
                  className="nh-btn"
                  style={{ textAlign: 'left', justifyContent: 'flex-start', textTransform: 'none', letterSpacing: 0.4, fontSize: 11, borderRadius: 16 }}
                  onClick={() => setChatInput(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>

            <div style={{ fontSize: 10, color: 'var(--text3)', letterSpacing: 2, margin: '18px 0 10px' }}>ASK</div>
            <textarea
              className="nh-input"
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about files, content, metadata, duplicates, timeline…  (Ctrl+Enter to send)"
              style={{ width: '100%', minHeight: 148, resize: 'vertical' }}
            />

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, marginTop: 12, flexWrap: 'wrap' }}>
              <div style={{ fontSize: 10, color: 'var(--text3)' }}>
                {llmEnabled
                  ? 'Searched from SQLite, then summarized by LLM. Ctrl+Enter to send.'
                  : 'LLM is off — enable it in Settings.'}
              </div>
              <button
                className="nh-btn primary"
                onClick={handleAsk}
                disabled={!chatInput.trim() || chatLoading || !llmEnabled}
              >
                {chatLoading ? 'ASKING…' : 'ASK AI'}
              </button>
            </div>
          </div>
        </div>
      </Panel>

      <div className="split-grid-2" style={{ marginBottom: 12 }}>
        <Panel>
          <SectionHeader label={t('dash_activity')}>
            <span style={{ fontSize: 9, color: 'var(--text3)' }}>
              {t('dash_queue')}: {d?.queue_size ?? 0}
            </span>
          </SectionHeader>

          {activeJobs.length === 0 ? (
            <div style={{ fontSize: 10, color: 'var(--text3)', padding: '12px 0', letterSpacing: 1 }}>— no active jobs —</div>
          ) : (
            activeJobs.map((job: any) => {
              const prog  = job.progress ?? {}
              const total = prog.queued ?? job.queued_count ?? 0
              const done  = prog.indexed ?? job.indexed_count ?? 0
              return (
                <div key={job.job_id} style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 10, color: 'var(--text)' }}>{job.root_label || job.root_path}</span>
                    <span style={{ fontSize: 9, color: 'var(--amber)', letterSpacing: 1 }}>
                      {done}/{total} {t('dash_files_indexed')}
                    </span>
                  </div>
                  <ProgressBar value={done} max={total || 1} />
                  {prog.current_file && (
                    <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      ▶ {prog.current_file}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </Panel>

        <Panel>
          <SectionHeader label={t('dash_insights')} />
          {insights.length === 0 ? (
            <div style={{ fontSize: 10, color: 'var(--green)', letterSpacing: 1, padding: '12px 0' }}>✓ All systems nominal</div>
          ) : (
            insights.map((ins: any, i: number) => (
              <div
                key={i}
                onClick={() => ins.action && setActiveTab(ins.action)}
                style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 0', borderBottom: '1px solid var(--border)', cursor: ins.action ? 'pointer' : 'default' }}
              >
                <span style={{ color: ins.type === 'error' ? 'var(--red)' : 'var(--amber)', fontSize: 14, flexShrink: 0 }}>{ins.icon}</span>
                <span style={{ fontSize: 10, color: 'var(--text2)', lineHeight: 1.5 }}>{ins.text}</span>
              </div>
            ))
          )}

          {stats.by_type && stats.by_type.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: 2, marginBottom: 10 }}>FILE TYPES</div>
              {stats.by_type.slice(0, 6).map((bt: any) => (
                <div key={bt.file_type_group} style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                    <span style={{ fontSize: 9, color: 'var(--text2)', letterSpacing: 1 }}>{(bt.file_type_group ?? 'other').toUpperCase()}</span>
                    <span style={{ fontSize: 9, color: 'var(--text3)' }}>{bt.cnt} · {formatSize(bt.sz)}</span>
                  </div>
                  <ProgressBar value={bt.cnt} max={stats.total_files || 1} />
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel>
        <SectionHeader label={t('dash_roots')}>
          <button className="nh-btn primary" style={{ fontSize: 9 }} onClick={() => setActiveTab('indexing')}>
            {t('btn_add_folder')}
          </button>
        </SectionHeader>
        {roots.length === 0 ? (
          <EmptyState icon="◎" message={t('dash_no_roots') + ' ' + t('dash_add_first')} />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))', gap: 8 }}>
            {roots.map((r: any) => (
              <div
                key={r.root_id}
                style={{
                  background: 'var(--bg2)', border: '1px solid var(--border)',
                  padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text)' }}>{r.root_label || r.root_path}</div>
                  <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 2 }}>{r.file_count} files</div>
                </div>
                <span className={`status-dot ${r.is_enabled ? 'active' : 'idle'}`} />
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel>
        <SectionHeader label={t('dash_recent')} />
        {recent.length === 0 ? (
          <EmptyState icon="📄" message="No files indexed yet" />
        ) : (
          recent.map((f: any) => (
            <div key={f.item_id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 0', borderBottom: '1px solid var(--bg3)' }}>
              <span style={{ fontSize: 9, color: 'var(--text3)', width: 120, flexShrink: 0, letterSpacing: 1 }}>{formatDateTime(f.last_indexed_ts)}</span>
              <span className="status-dot" style={{ background: 'var(--cyan)', opacity: 0.6 }} />
              <span style={{ flex: 1, fontSize: 11, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.file_name}</span>
              <span style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: 1 }}>{(f.file_type_group ?? 'other').toUpperCase()}</span>
            </div>
          ))
        )}
      </Panel>
    </div>
  )
}
