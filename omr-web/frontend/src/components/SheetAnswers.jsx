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

      <div className={styles.grid}>
        {questions.map(q => {
          const isMulti  = q.marked === 'MULTI'
          const isBlank  = !q.marked || q.marked === ''
          const cellClass = isMulti
            ? styles.multi
            : q.is_correct ? styles.correct : styles.wrong   // blank = wrong (red)
          return (
            <div key={q.q_no} className={`${styles.cell} ${cellClass}`}>
              <span className={styles.qno}>Q{q.q_no}</span>
              <span className={styles.marked}>{isBlank ? '—' : q.marked}</span>
              {isMulti && <span className={styles.hint}>MULTI</span>}
              {/* show correct answer for wrong OR blank questions */}
              {!isMulti && !q.is_correct && (
                <span className={styles.hint}>✓{q.correct}</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
