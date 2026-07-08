import axios from 'axios'

const BASE = '/api'

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
 * Returns a close() function.
 */
export const openProgressStream = (sessionId, onEvent, onComplete) => {
  const es = new EventSource(`${BASE}/session/${sessionId}/progress`)
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
