import React, { useEffect, useRef, useState } from 'react'
import { createSession, openProgressStream, uploadSheets } from './api.js'
import AnswerKeyZone from './components/AnswerKeyZone.jsx'
import QueuePanel from './components/QueuePanel.jsx'
import ResultsView from './components/ResultsView.jsx'
import SheetUploadZone from './components/SheetUploadZone.jsx'
import styles from './App.module.css'

export default function App() {
  const [sessionId, setSessionId] = useState(null)
  const [answerKey, setAnswerKey] = useState(null)
  const [sheets, setSheets] = useState([])           // live queue state
  const [processing, setProcessing] = useState(false)
  const [batchDone, setBatchDone] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const closeSSE = useRef(null)

  // Create session on mount
  useEffect(() => {
    createSession().then(setSessionId)
    return () => closeSSE.current?.()
  }, [])

  const handleKeyReady = (key) => {
    setAnswerKey(key)
    setSheets([])
    setBatchDone(false)
  }

  const handleProcess = async (files, names = []) => {
    setUploadError(null)
    setProcessing(true)
    setBatchDone(false)

    // Upload first and use the sheet_ids the backend actually assigns.
    // Previously this built local ids like "001", "002" *before* uploading
    // and never looked at the response — those ids only ever coincided
    // with the backend's own numbering for a session's first batch, so
    // SSE events for any later batch matched no row and sheets sat stuck
    // on QUEUED forever.
    let sheetIds
    try {
      const res = await uploadSheets(sessionId, files, names)
      sheetIds = res.sheet_ids
    } catch (e) {
      setUploadError(e.response?.data?.detail || 'Upload failed')
      setProcessing(false)
      return
    }

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

    // Subscribe to SSE progress
    closeSSE.current = openProgressStream(
      sessionId,
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

  if (!sessionId) {
    return <div className={styles.loading}>Initialising session…</div>
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>OMR Evaluator</h1>
        <span className={styles.sessionTag}>Session: {sessionId.slice(0, 8)}</span>
      </header>

      <main className={styles.main}>
        {/* Upload section */}
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

        {/* Queue */}
        {sheets.length > 0 && (
          <QueuePanel sheets={sheets} />
        )}

        {/* Results */}
        {batchDone && (
          <ResultsView sessionId={sessionId} sheets={sheets} />
        )}
      </main>
    </div>
  )
}
