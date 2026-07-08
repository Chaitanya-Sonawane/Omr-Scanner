import React from 'react'
import { getReportUrl, getSummaryReportUrl, getExcelExportUrl } from '../api.js'
import styles from './ResultsView.module.css'
import SheetAnswers from './SheetAnswers.jsx'

export default function ResultsView({ sessionId, sheets, onNewSession }) {
  const processed = sheets.filter(s => s.status === 'DONE' || s.status === 'FLAGGED')
  const errors = sheets.filter(s => s.status === 'ERROR')

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.titleBlock}>
          <h2 className={styles.heading}>Scan Results</h2>
          <p className={styles.sub}>
            {processed.length} scanned · {sheets.length} total
            {errors.length > 0 && <span className={styles.err}> · {errors.length} errors</span>}
          </p>
        </div>
        <div className={styles.exportBtns}>
          <a href={getReportUrl(sessionId)} target="_blank" rel="noreferrer">
            <button className="btn-download">⬇ Session PDF</button>
          </a>
          <a href={getSummaryReportUrl()} target="_blank" rel="noreferrer">
            <button className="btn-download" style={{background:'var(--purple)'}}>⬇ All Students PDF</button>
          </a>
          <a href={getExcelExportUrl(sessionId)} target="_blank" rel="noreferrer">
            <button className="btn-download" style={{background:'var(--green)'}}>⬇ Excel</button>
          </a>
          {onNewSession && (
            <button
              className={styles.newSessionBtn}
              onClick={onNewSession}
              title="Keep the answer key and start scanning a new batch"
            >
              ＋ New Session
            </button>
          )}
        </div>
      </div>

      {errors.map(sh => (
        <div key={sh.sheet_id} className={styles.errorRow}>
          ⚠ {sh.filename}: {sh.error}
        </div>
      ))}

      {processed.map(sheet => (
        <SheetAnswers key={sheet.sheet_id} sessionId={sessionId} sheet={sheet} />
      ))}

      {processed.length === 0 && (
        <p className={styles.empty}>No sheets processed yet</p>
      )}
    </div>
  )
}
