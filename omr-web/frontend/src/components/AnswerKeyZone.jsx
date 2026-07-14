import React, { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { uploadAnswerKey, submitManualAnswerKey, useSavedAnswerKey, hasSavedAnswerKey } from '../api.js'
import styles from './AnswerKeyZone.module.css'

const SECTIONS = [
  { label: 'Intelligence Test', range: [1, 10] },
  { label: 'Science', range: [11, 20] },
  { label: 'Social Science', range: [21, 30] },
  { label: 'Mathematics', range: [31, 40] },
]
const OPTIONS = ['A', 'B', 'C', 'D']

function emptyKey() {
  const k = {}
  for (let i = 1; i <= 40; i++) k[`q${i}`] = ''
  return k
}

// Normalize answer key to always use q-prefixed keys: {"q1": "A", ...}
function normalizeAnswers(raw) {
  const out = {}
  for (const [k, v] of Object.entries(raw)) {
    const key = k.startsWith('q') ? k : `q${k}`
    out[key] = v
  }
  return out
}

export default function AnswerKeyZone({ sessionId, onKeyReady }) {
  const [mode, setMode] = useState('manual') // 'manual' | 'scan'
  const [answers, setAnswers] = useState(emptyKey())
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [scanMeta, setScanMeta] = useState(null)
  const [hasSaved, setHasSaved] = useState(false)

  useEffect(() => {
    // Check if there's a saved answer key and auto-load it
    hasSavedAnswerKey().then(exists => {
      setHasSaved(exists)
      if (exists) {
        // Auto-load the saved key
        fetch('/api/answer-key')
          .then(r => r.ok ? r.json() : null)
          .then(data => {
            if (data?.answers) {
              const normalized = normalizeAnswers(data.answers)
              setAnswers(normalized)
              setSaved(true)
              onKeyReady(normalized)
            }
          })
          .catch(() => {}) // Silently fail
      }
    })
  }, [])

  const handleUseSaved = async () => {
    setLoading(true); setError(null)
    try {
      const result = await useSavedAnswerKey(sessionId)
      setAnswers(result.answers)
      setSaved(true)
      onKeyReady(result.answers)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load saved key')
    } finally {
      setLoading(false)
    }
  }

  // ── Manual entry ──────────────────────────────────────────────────────────
  const setAnswer = (q, val) => {
    setSaved(false)
    setAnswers(prev => ({ ...prev, [`q${q}`]: val }))
  }

  const allFilled = Object.values(answers).every(v => OPTIONS.includes(v))

  const handleSaveManual = async () => {
    if (!allFilled) return
    setLoading(true)
    setError(null)
    try {
      await submitManualAnswerKey(sessionId, answers)
      // Also save to persistent store via backend
      await fetch('/api/answer-key/save-manual', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({answers})
      })
      setSaved(true)
      setHasSaved(true)
      onKeyReady(answers)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to save answer key')
    } finally {
      setLoading(false)
    }
  }

  // ── Scan upload ───────────────────────────────────────────────────────────
  const onDrop = useCallback(async (accepted) => {
    if (!accepted.length) return
    setLoading(true)
    setError(null)
    setScanMeta(null)
    try {
      const result = await uploadAnswerKey(sessionId, accepted[0])
      const normalized = normalizeAnswers(result.answers)
      setAnswers(normalized)
      setSaved(true)
      setHasSaved(true)  // Mark as globally saved
      setScanMeta({
        confidence: result.confidence,
        flagged: result.flagged,
        lowConfidenceQuestions: result.low_confidence_questions || [],
      })
      onKeyReady(normalized)
    } catch (e) {
      setError(e.response?.data?.detail || 'Scan failed')
    } finally {
      setLoading(false)
    }
  }, [sessionId, onKeyReady])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.png', '.jpg', '.jpeg'], 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: loading,
  })

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className={styles.card}>
      <div className={styles.topRow}>
        <div>
          <h2 className={styles.heading}>① Answer Key</h2>
          <p className={styles.sub}>Enter or scan the correct answers for all 40 questions.</p>
        </div>
        <div style={{display:'flex', gap:'8px', flexWrap:'wrap', alignItems:'center'}}>
          {hasSaved && (
            <button className="btn-success" onClick={handleUseSaved} disabled={loading} style={{fontSize:'12px', padding:'7px 12px'}}>
              ⚡ Use Saved
            </button>
          )}
          <div className={styles.tabs}>
            <button className={mode === 'manual' ? styles.tabActive : styles.tab}
              onClick={() => { setMode('manual'); setSaved(false); setError(null) }}>Manual</button>
            <button className={mode === 'scan' ? styles.tabActive : styles.tab}
              onClick={() => { setMode('scan'); setSaved(false); setError(null) }}>Scan</button>
          </div>
        </div>
      </div>

      {/* ── Manual Entry Grid ── */}
      {mode === 'manual' && (
        <>
          <div className={styles.keyGrid}>
            {SECTIONS.map(sec => (
              <div key={sec.label} className={styles.section}>
                <p className={styles.sectionLabel}>{sec.label}</p>
                <table className={styles.table}>
                  <thead><tr><th>Q</th>{OPTIONS.map(o => <th key={o}>{o}</th>)}</tr></thead>
                  <tbody>
                    {Array.from({ length: sec.range[1] - sec.range[0] + 1 }, (_, i) => {
                      const q = sec.range[0] + i
                      const cur = answers[`q${q}`]
                      return (
                        <tr key={q}>
                          <td className={styles.qNum}>{q}</td>
                          {OPTIONS.map(opt => (
                            <td key={opt} className={styles.optCell}>
                              <button
                                className={`${styles.optBtn} ${cur === opt ? styles.optSelected : ''}`}
                                onClick={() => setAnswer(q, opt)}
                                aria-label={`Q${q} option ${opt}`}
                                aria-pressed={cur === opt}
                              >{opt}</button>
                            </td>
                          ))}
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ))}
          </div>

          <div className={styles.footer}>
            <span className={styles.progress}>
              {Object.values(answers).filter(v => OPTIONS.includes(v)).length} / 40 filled
            </span>
            {error && <span className={styles.error}>{error}</span>}
            {saved && <span className={styles.saved}>✓ Answer key saved</span>}
            <button
              className="btn-success"
              disabled={!allFilled || loading}
              onClick={handleSaveManual}
            >
              {loading ? 'Saving…' : saved ? '✓ Update Key' : 'Save Answer Key'}
            </button>
          </div>
        </>
      )}

      {/* ── Scan Upload ── */}
      {mode === 'scan' && (
        <>
          <p className={styles.scanNote}>
            ⚠ Scan accuracy depends on sheet quality and layout alignment. Verify the detected answers after upload.
          </p>
          <div
            {...getRootProps()}
            className={`${styles.dropzone} ${isDragActive ? styles.active : ''} ${loading ? styles.disabled : ''}`}
          >
            <input {...getInputProps()} />
            {loading
              ? <p>Scanning…</p>
              : isDragActive
              ? <p>Drop it here</p>
              : <p>Drag &amp; drop or <strong>click to browse</strong><br /><span className={styles.hint}>PNG · JPG · PDF</span></p>
            }
          </div>
          {error && <p className={styles.error}>{error}</p>}

          {saved && (
            <>
              <p className={styles.saved} style={{ marginTop: 10 }}>
                ✓ Scan complete (confidence: {scanMeta ? Math.round(scanMeta.confidence * 100) : '?'}%)
                {scanMeta?.lowConfidenceQuestions?.length > 0 && (
                  <span className={styles.warn}>
                    {' '} — {scanMeta.lowConfidenceQuestions.length} question(s) flagged for review
                  </span>
                )}
              </p>
              {scanMeta?.lowConfidenceQuestions?.length > 0 && (
                <div className={styles.warningBox}>
                  <strong>⚠ Low confidence detected for:</strong>{' '}
                  Q{scanMeta.lowConfidenceQuestions.map(q => q.q_no).join(', Q')}
                  <br />
                  <small>Switch to Manual Entry to verify and correct these answers.</small>
                </div>
              )}
              <div className={styles.keyGrid} style={{ marginTop: 12 }}>
                {SECTIONS.map(sec => (
                  <div key={sec.label} className={styles.section}>
                    <p className={styles.sectionLabel}>{sec.label}</p>
                    <table className={styles.table}>
                      <thead><tr><th>Q</th><th>Ans</th></tr></thead>
                      <tbody>
                        {Array.from({ length: sec.range[1] - sec.range[0] + 1 }, (_, i) => {
                          const q = sec.range[0] + i
                          const flagged = scanMeta?.lowConfidenceQuestions?.some(lc => lc.q_no === q)
                          return (
                            <tr key={q} className={flagged ? styles.lowConfRow : ''}>
                              <td className={styles.qNum}>{q}{flagged ? ' ⚠' : ''}</td>
                              <td className={styles.ans}>{answers[`q${q}`] || '?'}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
