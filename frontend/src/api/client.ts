import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// ── Dashboard ──────────────────────────────────────────────────────────────
export const getDashboard = () => api.get('/dashboard').then(r => r.data)

// ── Search ─────────────────────────────────────────────────────────────────
export const searchFiles = (params: Record<string, any>) =>
  api.get('/search', { params }).then(r => r.data)

export const getItem = (id: number) =>
  api.get(`/search/item/${id}`).then(r => r.data)

export const openFile = (id: number) =>
  api.post(`/search/open/${id}`).then(r => r.data)

export const revealFile = (id: number) =>
  api.post(`/search/reveal/${id}`).then(r => r.data)

export const getItemRawUrl = (id: number, download = false) =>
  `/api/search/raw/${id}${download ? '?download=1' : ''}`

export const getItemTextUrl = (id: number, maxChars = 50000) =>
  `/api/search/text/${id}?max_chars=${maxChars}`

export interface AskSearchParams {
  q: string
  file_type?: string      // maps to AskRequest.file_type on BE
  extension?: string
  root_id?: number
  min_size?: number
  max_size?: number
  since_ts?: number
  until_ts?: number
  order_by?: string
  limit?: number
  offset?: number
}

export interface AskSearchResponse {
  query: string
  count: number
  results: any[]
  // Top-level answer (promoted from llm.answer for easy access)
  answer: string
  mode: string
  used_result_count: number
  context_chars: number
  provider: string
  model: string
  // Also available nested for advanced consumers
  llm: {
    answer: string
    mode: string
    used_result_count: number
    context_chars: number
    provider: string
    model: string
  }
}

export const askSearch = (data: AskSearchParams): Promise<AskSearchResponse> =>
  api.post('/search/ask', data).then(r => r.data)

// ── Images ─────────────────────────────────────────────────────────────────
export const listImages = (params: Record<string, any>) =>
  api.get('/images', { params }).then(r => r.data)

export const getImageItem = (id: number) =>
  api.get(`/images/item/${id}`).then(r => r.data)

// ── Timeline ───────────────────────────────────────────────────────────────
export const getTimelineBuckets = (params: Record<string, any>) =>
  api.get('/timeline/buckets', { params }).then(r => r.data)

export const getBucketItems = (bucket: string, params: Record<string, any>) =>
  api.get(`/timeline/items/${encodeURIComponent(bucket)}`, { params }).then(r => r.data)

// ── Duplicates ─────────────────────────────────────────────────────────────
export const getExactDuplicates = (params?: any) =>
  api.get('/duplicates/exact', { params }).then(r => r.data)

export const getSimilarText = (params?: any) =>
  api.get('/duplicates/similar-text', { params }).then(r => r.data)

export const getSimilarImages = (params?: any) =>
  api.get('/duplicates/similar-images', { params }).then(r => r.data)

export const markReviewed = (groupItemId: number, status = 'reviewed') =>
  api.post(`/duplicates/review/${groupItemId}`, null, { params: { status } }).then(r => r.data)

export const getDupStats = () =>
  api.get('/duplicates/stats').then(r => r.data)

// ── Indexing ───────────────────────────────────────────────────────────────
export const listRoots = () =>
  api.get('/index/roots').then(r => r.data)

export const pickFolder = () =>
  api.get('/index/pick-folder').then(r => r.data)

export const addRoot = (data: { root_path: string; label?: string; start_now?: boolean }) =>
  api.post('/index/roots', data).then(r => r.data)

export const removeRoot = (rootId: number) =>
  api.delete(`/index/roots/${rootId}`).then(r => r.data)

export const reindexRoot = (rootId: number, full_rescan = false) =>
  api.post(`/index/roots/${rootId}/reindex`, { full_rescan }).then(r => r.data)

export const getJobs = () =>
  api.get('/index/jobs').then(r => r.data)

export const getJobProgress = (jobId: number) =>
  api.get(`/index/jobs/${jobId}/progress`).then(r => r.data)

// ── Settings ───────────────────────────────────────────────────────────────
export const getSettings = () =>
  api.get('/settings').then(r => r.data)

export const updateSetting = (key: string, value: string) =>
  api.post('/settings', { key, value }).then(r => r.data)

export const getLlmSettings = () =>
  api.get('/settings/llm').then(r => r.data)

export const updateLlmSettings = (data: Record<string, any>) =>
  api.post('/settings/llm', data).then(r => r.data)

export const testLlmConnection = () =>
  api.post('/settings/llm/test').then(r => r.data)

export default api
