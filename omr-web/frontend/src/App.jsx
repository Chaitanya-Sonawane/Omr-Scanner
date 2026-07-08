import React, { useEffect, useRef, useState } from 'react'
import { createSession, openProgressStream, uploadSheets, submitManualAnswerKey } from './api.js'
import AnswerKeyZone from './components/AnswerKeyZone.jsx'
import QueuePanel from './components/QueuePanel.jsx'
import ResultsView from './components/ResultsView.jsx'
import SheetUploadZone from './components/SheetUploadZone.jsx'
import styles from './App.module.css'

// ── LocalStorage helpers ──────────────────────────────────────────────────────
const STORAGE_KEY = 'omr_session_state'

function persistState(sessionId, answerKey, sheets, batchDone) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ sessionId, answerKey, sheets, batchDone }))
  } catch (_) { /* quota exceeded or private mode */ }
}

function loadPersistedState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch (_) {
    return null
  }
}

function clearPersistedState() {
  try { localStorage.removeItem(STORAGE_KEY) } catch (_) {}
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function App() {
  // Hydrate from localStorage on first render
  const saved = loadPersistedState()

  const [sessionId, setSessionId]   = useState(saved?.sessionId ?? null)
  const [answerKey, setAnswerKey]   = useState(saved?.answerKey ?? null)
  const [sheets, setSheets]         = useState(saved?.sheets ?? [])
  const [batchDone, setBatchDone]   = useState(saved?.batchDone ?? false)
  const [processing, setProcessing] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const closeSSE      = useRef(null)
  const answerKeyRef  = useRef(answerKey)
  const activeSessionRef = useRef(sessionId)

  // Keep refs in sync
  useEffect(() => { answerKeyRef.current = answerKey }, [answerKey])

  // Persist whenever relevant state changes
  useEffect(() => {
    if (sessionId) {
      persistState(sessionId, answerKey, sheets, batchDone)
    }
  }, [sessionId, answerKey, sheets, batchDone])

  // ── Session init ────────────────────────────────────────────────────────────
  const initSession = async () => {
    const id = await createSession()
    setSessionId(id)
    activeSessionRef.current = id
    return id
  }

  useEffect(() => {
    // If we restored a session from storage, verify it still exists on the
    // backend. If not (server restarted), create a fresh one.
    if (saved?.sessionId) {
      fetch(`/api/session/${saved.sessionId}/status`)
        .then(r => {
          if (!r.ok) throw new Error('gone')
          // Session still alive — nothing to do
        })
        .catch(() => {
          // Server restarted — create a new session but keep cached results
          initSession()
        })
    } else {
      initSession()
    }
    return () => closeSSE.current?.()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Answer key ──────────────────────────────────────────────────────────────
  const handleKeyReady = (key) => {
    setAnswerKey(key)
    setSheets([])
    setBatchDone(false)
  }

  // ── Sheet processing ────────────────────────────────────────────────────────
  const handleProcess = async (files, names = []) => {
    setUploadError(null)
    setProcessing(true)
    setBatchDone(false)

    let res, uploadSessionId

    try {
      res = await uploadSheets(sessionId, files, names)
      uploadSessionId = sessionId
    } catch (e) {
      if (e.response?.status === 404) {
        // Session expired — recreate and re-apply answer key
        try {
          const newId = await initSession()
          if (answerKeyRef.current) {
            await submitManualAnswerKey(newId, answerKeyRef.current).catch(() => {})
          }
          res = await uploadSheets(newId, files, names)
          uploadSessionId = newId
        } catch (e2) {
          setUploadError(e2.response?.data?.detail || 'Upload failed after recovery')
          setProcessing(false)
          return
        }
      } else {
        setUploadError(e.response?.data?.detail || 'Upload failed')
        setProcessing(false)
        return
      }
    }

    activeSessionRef.current = uploadSessionId

    const sheetIds = res.sheet_ids
    const initial = files.map((f, i) => ({
      sheet_id: sheetIds[i],
      filename: f.name,
      status: 'QUEUED',
      student_id: names[i] || null,
      score: null,
      confidence: null,
      error: null,
    }))
    setSheets(initial)

    closeSSE.current = openProgressStream(
      uploadSessionId,
      (event) => {
        setSheets(prev => prev.map(sh =>
          sh.sheet_id === event.sheet_id ? { ...sh, ...event } : sh
        ))
      },
      () => {
        setProcessing(false)
        setBatchDone(true)
        closeSSE.current = null
      }
    )
  }

  // ── New session ─────────────────────────────────────────────────────────────
  const handleNewSession = async () => {
    closeSSE.current?.()
    closeSSE.current = null

    // Clear all state and storage
    clearPersistedState()
    setSheets([])
    setBatchDone(false)
    setUploadError(null)
    setProcessing(false)
    setAnswerKey(null)
    answerKeyRef.current = null

    await initSession()
  }

  // ── Loading screen ──────────────────────────────────────────────────────────
  if (!sessionId) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
        Initialising session…
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}>📋</span>
          <span className={styles.title}>OMR Evaluator</span>
        </div>

        <div className={styles.headerRight}>
          <span className={styles.sessionTag}>
            Session: {sessionId.slice(0, 8)}
          </span>
          <button
            className={styles.newSessionBtn}
            onClick={handleNewSession}
            title="Clear all data and start a brand-new session"
          >
            + New Session
          </button>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.uploadRow}>
          <AnswerKeyZone sessionId={sessionId} onKeyReady={handleKeyReady} />
          <SheetUploadZone
            disabled={!answerKey || processing}
            onProcess={handleProcess}
          />
        </div>

        {uploadError && (
          <div className={styles.errorBanner}>⚠ {uploadError}</div>
        )}

        {sheets.length > 0 && (
          <QueuePanel sheets={sheets} />
        )}

        {batchDone && (
          <ResultsView
            sessionId={activeSessionRef.current}
            sheets={sheets}
          />
        )}
      </main>
    </div>
  )
}
