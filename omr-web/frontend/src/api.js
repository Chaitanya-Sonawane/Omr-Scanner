import axios from 'axios'

// Regular API calls go through the Netlify /api proxy (see netlify.toml)
const BASE = '/api'

// SSE (EventSource) cannot follow Netlify redirects, so it hits Render directly.
// VITE_API_URL is set in Netlify env vars to https://omr-scanner-1-cmbe.onrender.com
const SSE_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : BASE

export const createSession = () =>
  axios.post(`${BASE}/session`).then(r => r.data.session_id)

export const uploadAnswerKey = (sessionId, file) => {
  const fd = new FormData()
  fd.append('file', file)
  return axios.post(`${BASE}/session/${sessionId}/answer-key`, fd).then(r => r.data)
}

export const submitManualAnswerKey = (sessionId, answers) =>
  axios.post(`${BASE}/session/${sessionId}/answer-key/manual`, { answers }).then(r => r.data)

export const getAnswerKey = (sessionId) =>
  axios.get(`${BASE}/session/${sessionId}/answer-key`).then(r => r.data)

export const uploadSheets = (sessionId, files, names = []) => {
  const fd = new FormData()
  files.forEach(f => fd.append('files', f))
  if (names.some(n => n)) fd.append('names', names.join(','))
  return axios.post(`${BASE}/session/${sessionId}/sheets`, fd).then(r => r.data)
}

export const getStatus = (sessionId) =>
  axios.get(`${BASE}/session/${sessionId}/status`).then(r => r.data)

export const getResults = (sessionId) =>
  axios.get(`${BASE}/session/${sessionId}/results`).then(r => r.data)

export const getReportUrl = (sessionId) =>
  `${BASE}/session/${sessionId}/export/pdf`

export const getSummaryReportUrl = () =>
  `${BASE}/export/all-students/pdf`

export const getExcelExportUrl = (sessionId) =>
  sessionId ? `${BASE}/session/${sessionId}/export/excel` : null

export const useSavedAnswerKey = (sessionId) =>
  axios.post(`${BASE}/session/${sessionId}/answer-key/use-saved`).then(r => r.data)

export const hasSavedAnswerKey = () =>
  axios.get(`${BASE}/answer-key`).then(() => true).catch(() => false)

export const getRawDetection = (sessionId, sheetId) =>
  axios.get(`${BASE}/session/${sessionId}/sheet/${sheetId}/raw`).then(r => r.data)

/**
 * Open an SSE connection for live sheet processing updates.
 * Uses SSE_BASE (direct Render URL) since EventSource can't follow redirects.
 * Returns a close() function.
 */
export const openProgressStream = (sessionId, onEvent, onComplete) => {
  const es = new EventSource(`${SSE_BASE}/session/${sessionId}/progress`)
  es.onmessage = e => {
    const data = JSON.parse(e.data)
    if (data.type === 'BATCH_COMPLETE') {
      onComplete?.()
      es.close()
    } else if (data.type !== 'KEEPALIVE') {
      onEvent(data)
    }
  }
  es.onerror = () => es.close()
  return () => es.close()
}
