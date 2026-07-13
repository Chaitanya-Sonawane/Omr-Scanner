import React from 'react'
import styles from './QueuePanel.module.css'

function StatusBadge({ status }) {
  return <span className={`badge badge-${status?.toLowerCase() ?? 'queued'}`}>{status ?? 'QUEUED'}</span>
}

function ConfidenceBar({ value }) {
  if (value == null) return null
  const pct = Math.round(value * 100)
  const color = value >= 0.75 ? '#16a34a' : value >= 0.60 ? '#d97706' : '#dc2626'
  return (
    <div className={styles.confBar} title={`Confidence: ${pct}%`}>
      <div className={styles.confFill} style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

export default function QueuePanel({ sheets }) {
  if (!sheets.length) return null

  const done = sheets.filter(s => s.status === 'DONE').length
  const errors = sheets.filter(s => s.status === 'ERROR').length

  return (
    <div className={styles.card}>
      <div className={styles.headingRow}>
        <h2 className={styles.heading}>Processing Queue</h2>
        <span className={styles.counter}>
          {done}/{sheets.length} done {errors > 0 && `· ${errors} errors`}
        </span>
      </div>
      <div className={styles.list}>
        {sheets.map((sh, i) => (
          <div key={sh.sheet_id} className={styles.row}>
            <span className={styles.idx}>{i + 1}</span>
            <div className={styles.info}>
              <span className={styles.filename}>{sh.student_id || sh.filename}</span>
              {sh.student_id && <span className={styles.studentId}>{sh.filename}</span>}
              {sh.status === 'ERROR' && <span className={styles.errMsg}>{sh.error}</span>}
            </div>
            <div className={styles.right}>
              {sh.score != null && sh.status === 'DONE' && (
                <span className={styles.score}>{sh.score.correct ?? sh.score.total ?? sh.score}/40</span>
              )}
              <ConfidenceBar value={sh.confidence} />
              <StatusBadge status={sh.status} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
