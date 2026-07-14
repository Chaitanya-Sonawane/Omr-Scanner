import React, { useState, useEffect } from 'react'
import styles from './SheetAnswers.module.css'

export default function SheetAnswers({ sessionId, sheet }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/session/${sessionId}/detection/${sheet.sheet_id}`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [sessionId, sheet.sheet_id])

  if (loading) return <div className={styles.loading}>Loading…</div>
  if (error)   return <div className={styles.error}>Error: {error}</div>
  if (!data)   return null

  const questions = data.questions || []
  const correct = questions.filter(q => q.is_correct).length

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.title}>📄 {data.student_id || sheet.filename}</span>
        <span className={styles.score}>Score: {data.total_score ?? correct} / {data.out_of ?? 40}</span>
      </div>

      {data.omr_meta && (
        <div className={styles.metaBar}>
          <span>Threshold: <strong>{data.omr_meta.threshold?.toFixed(1)}</strong></span>
          <span>Fill range: <strong>{data.omr_meta.score_min?.toFixed(1)} – {data.omr_meta.score_max?.toFixed(1)}</strong></span>
          {questions.filter(q => q.status === 'REVIEW').length > 0 && (
            <span className={styles.metaWarn}>
              ⚠ {questions.filter(q => q.status === 'REVIEW').length} REVIEW
            </span>
          )}
          {questions.filter(q => q.status === 'MULTI').length > 0 && (
            <span className={styles.metaMulti}>
              ✕ {questions.filter(q => q.status === 'MULTI').length} MULTI
            </span>
          )}
        </div>
      )}

      <div className={styles.grid}>
        {questions.map(q => {
          const status    = q.status   // OK | BLANK | MULTI | REVIEW (backend-2)
          const isMulti   = status === 'MULTI'  || q.marked === 'MULTI'  || q.flag === 'multi_mark'
          const isReview  = status === 'REVIEW' || q.flag === 'review'
          const isBlank   = status === 'BLANK'  || (!q.marked || q.marked === '')
          const cellClass = isMulti
            ? styles.multi
            : isReview
            ? styles.review
            : q.is_correct ? styles.correct : styles.wrong

          return (
            <div key={q.q_no} className={`${styles.cell} ${cellClass}`}>
              <span className={styles.qno}>Q{q.q_no}</span>
              <span className={styles.marked}>
                {isMulti ? '✕' : isBlank ? '—' : q.marked}
              </span>
              {isMulti  && <span className={styles.hintMulti}>MULTI</span>}
              {isReview && !isMulti && <span className={styles.hintReview}>REVIEW</span>}
              {!isMulti && !q.is_correct && q.correct && (
                <span className={styles.hint}>✓{q.correct}</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
