import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import styles from './SheetUploadZone.module.css'

export default function SheetUploadZone({ disabled, onProcess }) {
  const [files, setFiles] = useState([])
  const [names, setNames] = useState([])   // parallel array: names[i] = student name for files[i]
  const [showNames, setShowNames] = useState(false)

  const onDrop = useCallback((accepted) => {
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      const novel = accepted.filter(f => !existing.has(f.name))
      const next = [...prev, ...novel].slice(0, 50)
      setNames(n => {
        const extended = [...n]
        while (extended.length < next.length) extended.push('')
        return extended.slice(0, next.length)
      })
      return next
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.png', '.jpg', '.jpeg'], 'application/pdf': ['.pdf'] },
    multiple: true,
    disabled,
  })

  const remove = (idx) => {
    setFiles(f => f.filter((_, i) => i !== idx))
    setNames(n => n.filter((_, i) => i !== idx))
  }

  const setName = (idx, val) => {
    setNames(n => { const copy = [...n]; copy[idx] = val; return copy })
  }

  const handleProcess = () => {
    onProcess(files, names.map(n => n.trim()))
  }

  return (
    <div className={styles.card}>
      <h2 className={styles.heading}>② Student OMR Sheets</h2>
      <p className={styles.sub}>Upload up to 50 scanned/photographed sheets. Processed sequentially.</p>

      <div
        {...getRootProps()}
        className={`${styles.dropzone} ${isDragActive ? styles.active : ''} ${disabled ? styles.disabled : ''}`}
      >
        <input {...getInputProps()} />
        {isDragActive
          ? <p>Drop sheets here</p>
          : <p>Drag &amp; drop up to 50 sheets or <strong>click to browse</strong><br /><span className={styles.hint}>PNG · JPG · PDF &nbsp;|&nbsp; max 50 files</span></p>
        }
      </div>

      {files.length > 0 && (
        <>
          <div className={styles.namesToggle}>
            <button
              className={styles.toggleBtn}
              onClick={() => setShowNames(v => !v)}
              disabled={disabled}
            >
              {showNames ? '▲ Hide student names' : '▼ Enter student names (optional)'}
            </button>
          </div>

          <div className={styles.fileList}>
            {files.map((f, i) => (
              <div key={f.name} className={styles.fileRow}>
                <span className={styles.idx}>{i + 1}</span>
                <span className={styles.name}>{f.name}</span>
                {showNames && (
                  <input
                    className={styles.nameInput}
                    placeholder={`Student ${i + 1} name`}
                    value={names[i] || ''}
                    onChange={e => setName(i, e.target.value)}
                    disabled={disabled}
                  />
                )}
                <span className={styles.size}>{(f.size / 1024).toFixed(0)} KB</span>
                <button
                  className={styles.remove}
                  onClick={() => remove(i)}
                  disabled={disabled}
                  aria-label={`Remove ${f.name}`}
                >✕</button>
              </div>
            ))}
          </div>

          <div className={styles.footer}>
            <span className={styles.count}>{files.length} / 50 files</span>
            <button
              className="btn-success"
              disabled={disabled || files.length === 0}
              onClick={handleProcess}
            >
              Process Sheets →
            </button>
          </div>
        </>
      )}
    </div>
  )
}
