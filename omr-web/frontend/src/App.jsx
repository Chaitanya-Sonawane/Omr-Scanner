import React, { useEffect, useRef, useState } from 'react'
import { createSession, openProgressStream, uploadSheets, submitManualAnswerKey } from './api.js'
import AnswerKeyZone from './components/AnswerKeyZone.jsx'
import QueuePanel from './components/QueuePanel.jsx'
import ResultsView from './components/ResultsView.jsx'
import SheetUploadZone from './components/SheetUploadZone.jsx'
import styles from './App.module.css'

export default function App() {
  const [sessionId, setSessionId] = useState(null)
  const [answerKey, setAnswerKey] = useState(null)
  const [sheets, setSheets] = useState([])
  const [processing, setProcessing] = useState(false)
  const [batchDone, setBatchDone] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const closeSSE = useRef(null)
  const answerKeyRef = useRef(null)
  const activeSessionRef = useRef(null)

  useEffect(() => { answerKeyRef.current = answerKey }, [answerKey])

  const initSession = async () => {
    const id = await createSession()
    setSessionId(id)
    activeSessionRef.current = id
    return id
  }

  useEffect(() => {
    initSession()
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

    let res, uploadSessionId

    try {
      res = await uploadSheets(sessionId, files, names)
      uploadSessionId = sessionId
    } catch (e) {
      if (e.response?.status === 404) {
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
    setSheets(files.map((f, i) => ({
      sheet_id: sheetIds[i],
      filename: f.name,
      status: 'QUEUED',
      student_id: names[i] || null,
      score: null,
      confidence: null,
      error: null,
    })))

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

  // Start a new session: create fresh session ID, carry over the answer key,
  // clear all sheet/result state so the user can scan the next batch.
  const handleNewSession = async () => {
    closeSSE.current?.()
    closeSSE.current = null
    setSheets([])
    setBatchDone(false)
    setUploadError(null)
    setProcessing(false)

    const newId = await initSession()

    // Re-apply the saved answer key to the new session automatically
    if (answerKeyRef.current) {
      try {
        // Use the globally saved key (POST use-saved) so no re-scan needed
        await fetch(`/api/session/${newId}/answer-key/use-saved`, { method: 'POST' })
        // answerKey state stays the same — user sees it still filled in
      } catch (_) {
        // Fallback: apply manually entered key
        await submitManualAnswerKey(newId, answerKeyRef.current).catch(() => {})
      }
    }
  }

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
        <span className={styles.sessionTag}>{sessionId.slice(0, 8)}</span>
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
            onNewSession={handleNewSession}
          />
        )}
      </main>
    </div>
  )
}
