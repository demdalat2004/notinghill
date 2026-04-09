// NotingHill — pages/Settings.tsx
import { useEffect, useState } from 'react'
import { useStore } from '../store'
import { getSettings, getLlmSettings, testLlmConnection, updateLlmSettings, updateSetting } from '../api/client'
import { SectionHeader, Panel } from '../components/ui'

type LlmLocalState = {
  llm_enabled: string
  llm_provider: string
  llm_base_url: string
  llm_model: string
  llm_api_key: string
  llm_temperature: string
  llm_top_k: string
  llm_top_n_results: string
  llm_max_context_chars: string
  llm_system_prompt: string
  llm_search_mode: string
  llm_auto_summarize: string
}

const DEFAULT_LLM_STATE: LlmLocalState = {
  llm_enabled: '0',
  llm_provider: 'ollama',
  llm_base_url: 'http://127.0.0.1:11434',
  llm_model: 'gemma4:latest',
  llm_api_key: '',
  llm_temperature: '0.2',
  llm_top_k: '8',
  llm_top_n_results: '8',
  llm_max_context_chars: '16000',
  llm_system_prompt: 'You are a local file search assistant. Answer only from the retrieved file results and metadata. If the answer is uncertain, say so clearly.',
  llm_search_mode: 'fts_plus_llm',
  llm_auto_summarize: '1',
}

export default function Settings() {
  const { t, theme, setTheme, lang, setLang, settings, setSettings } = useStore()
  const [local, setLocal] = useState<Record<string, string>>({})
  const [llmLocal, setLlmLocal] = useState<LlmLocalState>(DEFAULT_LLM_STATE)
  const [saved, setSaved] = useState(false)
  const [llmSaved, setLlmSaved] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    getSettings().then((s) => {
      setSettings(s)
      setLocal(s)
    })

    getLlmSettings()
      .then((s) => {
        const merged = { ...DEFAULT_LLM_STATE, ...(s || {}) }
        setLlmLocal(Object.fromEntries(Object.entries(merged).map(([k, v]) => [k, `${v ?? ''}`])) as LlmLocalState)
      })
      .catch(() => {
        setLlmLocal(DEFAULT_LLM_STATE)
      })
  }, [setSettings])

  const handleSave = async () => {
    const keys = ['ocr_enabled', 'max_extract_size_mb', 'ignored_extensions', 'ignored_paths', 'auto_rescan_minutes']
    for (const key of keys) {
      if (local[key] !== undefined) {
        await updateSetting(key, local[key])
      }
    }
    setSettings({ ...settings, ...local })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleSaveLlm = async () => {
    await updateLlmSettings({ ...llmLocal, llm_enabled: llmLocal.llm_enabled === '1' })
    window.dispatchEvent(new CustomEvent('llm-settings-updated'))
    setLlmSaved(true)
    setTimeout(() => setLlmSaved(false), 2000)
  }

  const handleTestLlm = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      await updateLlmSettings({ ...llmLocal, llm_enabled: llmLocal.llm_enabled === '1' })
      window.dispatchEvent(new CustomEvent('llm-settings-updated'))
      const res = await testLlmConnection()
      setTestResult({ ok: !!res?.ok, text: res?.message || res?.detail || 'Connection test finished.' })
    } catch (e: any) {
      setTestResult({ ok: false, text: e?.response?.data?.detail || e?.message || 'Connection test failed.' })
    }
    setTesting(false)
  }

  return (
    <div className="layout-page animate-fade-in" style={{ maxWidth: 900, margin: '0 auto' }}>
      <Panel>
        <SectionHeader label={t('set_title')} />

        <SettingRow label={t('set_theme')}>
          <div style={{ display: 'flex', gap: 6 }}>
            {(['dark', 'light'] as const).map((th) => (
              <button
                key={th}
                className={`nh-btn ${theme === th ? 'primary' : ''}`}
                style={{ fontSize: 10 }}
                onClick={() => setTheme(th)}
              >
                {th === 'dark' ? t('set_dark') : t('set_light')}
              </button>
            ))}
          </div>
        </SettingRow>

        <SettingRow label={t('set_language')}>
          <div style={{ display: 'flex', gap: 6 }}>
            {(['en', 'vi'] as const).map((l) => (
              <button
                key={l}
                className={`nh-btn ${lang === l ? 'primary' : ''}`}
                style={{ fontSize: 10 }}
                onClick={() => setLang(l)}
              >
                {l === 'en' ? 'ENGLISH' : 'TIẾNG VIỆT'}
              </button>
            ))}
          </div>
        </SettingRow>
      </Panel>

      <Panel>
        <SectionHeader label="EXTRACTION" />

        <SettingRow label={t('set_ocr')} description={t('set_ocr_desc')}>
          <div style={{ display: 'flex', gap: 6 }}>
            {[['1', 'ON'], ['0', 'OFF']].map(([val, label]) => (
              <button
                key={val}
                className={`nh-btn ${local.ocr_enabled === val ? 'primary' : ''}`}
                style={{ fontSize: 10 }}
                onClick={() => setLocal((p) => ({ ...p, ocr_enabled: val }))}
              >
                {label}
              </button>
            ))}
          </div>
        </SettingRow>

        <SettingRow label={t('set_max_size')}>
          <input
            className="nh-input"
            type="number"
            style={{ width: 100 }}
            value={local.max_extract_size_mb || '50'}
            onChange={(e) => setLocal((p) => ({ ...p, max_extract_size_mb: e.target.value }))}
          />
        </SettingRow>
      </Panel>

      <Panel>
        <SectionHeader label="IGNORE RULES" />

        <SettingRow label={t('set_ignored_ext')} description="Comma-separated, e.g. .tmp,.lock">
          <input
            className="nh-input"
            style={{ width: 320 }}
            value={local.ignored_extensions || ''}
            onChange={(e) => setLocal((p) => ({ ...p, ignored_extensions: e.target.value }))}
          />
        </SettingRow>

        <SettingRow label={t('set_ignored_paths')} description="Comma-separated path fragments">
          <input
            className="nh-input"
            style={{ width: 320 }}
            value={local.ignored_paths || ''}
            onChange={(e) => setLocal((p) => ({ ...p, ignored_paths: e.target.value }))}
          />
        </SettingRow>

        <SettingRow label={t('set_rescan')}>
          <input
            className="nh-input"
            type="number"
            style={{ width: 100 }}
            value={local.auto_rescan_minutes || '60'}
            onChange={(e) => setLocal((p) => ({ ...p, auto_rescan_minutes: e.target.value }))}
          />
        </SettingRow>
      </Panel>

      <Panel>
        <SectionHeader label="LLM" />

        <SettingRow label="ENABLE LLM" description="Turn local AI search assistant on or off.">
          <div style={{ display: 'flex', gap: 6 }}>
            {[['1', 'ON'], ['0', 'OFF']].map(([val, label]) => (
              <button
                key={val}
                className={`nh-btn ${llmLocal.llm_enabled === val ? 'primary' : ''}`}
                style={{ fontSize: 10 }}
                onClick={() => setLlmLocal((p) => ({ ...p, llm_enabled: val }))}
              >
                {label}
              </button>
            ))}
          </div>
        </SettingRow>

        <SettingRow label="PROVIDER" description="Example: ollama, openai, lmstudio">
          <input className="nh-input" style={{ width: 220 }} value={llmLocal.llm_provider} onChange={(e) => setLlmLocal((p) => ({ ...p, llm_provider: e.target.value }))} />
        </SettingRow>

        <SettingRow label="BASE URL" description="Local runtime endpoint or API base URL.">
          <input className="nh-input" style={{ width: 320 }} value={llmLocal.llm_base_url} onChange={(e) => setLlmLocal((p) => ({ ...p, llm_base_url: e.target.value }))} />
        </SettingRow>

        <SettingRow label="MODEL" description="Example: gemma4:latest">
          <input className="nh-input" style={{ width: 220 }} value={llmLocal.llm_model} onChange={(e) => setLlmLocal((p) => ({ ...p, llm_model: e.target.value }))} />
        </SettingRow>

        <SettingRow label="API KEY" description="Leave empty for local Ollama if not needed.">
          <input className="nh-input" type="password" style={{ width: 320 }} value={llmLocal.llm_api_key} onChange={(e) => setLlmLocal((p) => ({ ...p, llm_api_key: e.target.value }))} />
        </SettingRow>

        <SettingRow label="SEARCH MODE" description="fts_only, fts_plus_llm, llm_rerank">
          <input className="nh-input" style={{ width: 220 }} value={llmLocal.llm_search_mode} onChange={(e) => setLlmLocal((p) => ({ ...p, llm_search_mode: e.target.value }))} />
        </SettingRow>

        <SettingRow label="TEMPERATURE">
          <input className="nh-input" style={{ width: 100 }} value={llmLocal.llm_temperature} onChange={(e) => setLlmLocal((p) => ({ ...p, llm_temperature: e.target.value }))} />
        </SettingRow>

        <SettingRow label="TOP K">
          <input className="nh-input" style={{ width: 100 }} value={llmLocal.llm_top_k} onChange={(e) => setLlmLocal((p) => ({ ...p, llm_top_k: e.target.value }))} />
        </SettingRow>

        <SettingRow label="TOP RESULTS INTO CONTEXT">
          <input className="nh-input" style={{ width: 100 }} value={llmLocal.llm_top_n_results} onChange={(e) => setLlmLocal((p) => ({ ...p, llm_top_n_results: e.target.value }))} />
        </SettingRow>

        <SettingRow label="MAX CONTEXT CHARS">
          <input className="nh-input" style={{ width: 120 }} value={llmLocal.llm_max_context_chars} onChange={(e) => setLlmLocal((p) => ({ ...p, llm_max_context_chars: e.target.value }))} />
        </SettingRow>

        <SettingRow label="AUTO SUMMARIZE">
          <div style={{ display: 'flex', gap: 6 }}>
            {[['1', 'ON'], ['0', 'OFF']].map(([val, label]) => (
              <button
                key={val}
                className={`nh-btn ${llmLocal.llm_auto_summarize === val ? 'primary' : ''}`}
                style={{ fontSize: 10 }}
                onClick={() => setLlmLocal((p) => ({ ...p, llm_auto_summarize: val }))}
              >
                {label}
              </button>
            ))}
          </div>
        </SettingRow>

        <SettingRow label="SYSTEM PROMPT" description="This prompt is sent with the retrieved file results.">
          <textarea
            className="nh-input"
            style={{ width: 420, minHeight: 140, resize: 'vertical' }}
            value={llmLocal.llm_system_prompt}
            onChange={(e) => setLlmLocal((p) => ({ ...p, llm_system_prompt: e.target.value }))}
          />
        </SettingRow>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginTop: 16 }}>
          <div style={{ fontSize: 10, color: testResult ? (testResult.ok ? 'var(--green)' : 'var(--red)') : 'var(--text3)' }}>
            {testResult ? testResult.text : 'Save first, then test the current LLM connection.'}
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            {llmSaved && (
              <span style={{ fontSize: 10, color: 'var(--green)', letterSpacing: 2, alignSelf: 'center' }}>
                ✓ LLM SAVED
              </span>
            )}
            <button className="nh-btn" onClick={handleTestLlm} disabled={testing}>
              {testing ? 'TESTING...' : 'TEST CONNECTION'}
            </button>
            <button className="nh-btn primary" onClick={handleSaveLlm}>
              SAVE LLM
            </button>
          </div>
        </div>
      </Panel>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
        {saved && (
          <span style={{ fontSize: 10, color: 'var(--green)', letterSpacing: 2, alignSelf: 'center' }}>
            ✓ {t('set_saved')}
          </span>
        )}
        <button className="nh-btn primary" style={{ padding: '8px 24px' }} onClick={handleSave}>
          {t('set_save')}
        </button>
      </div>
    </div>
  )
}

function SettingRow({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 20,
        padding: '14px 0',
        borderBottom: '1px solid var(--bg3)',
      }}
    >
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 10, color: 'var(--text)', letterSpacing: 1 }}>{label}</div>
        {description && <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 3, lineHeight: 1.5 }}>{description}</div>}
      </div>
      <div style={{ flexShrink: 0 }}>{children}</div>
    </div>
  )
}
