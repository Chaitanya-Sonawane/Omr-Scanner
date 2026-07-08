import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import styles from './SheetUploadZone.module.css'

const MAX_PX = 1400   // max dimension — enough for OMR detection, small enough to upload fast
const JPEG_Q = 0.82   // JPEG quality

/**
 * Compress an image File to at most MAX_PX on the longest side.
 * PDFs are returned unchanged (server handles them).
 */
function compressImage(file) {
  if (file.type === 'application/pdf') return Promise.resolve(file)
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      let { width, height } = img
      // Skip if already small
      if (width <= MAX_PX && height <= MAX_PX && file.size < 400 * 1024) {
        return resolve(file)
      }
      const scale = Math.min(1, MAX_PX / Math.max(width, height))
      width  = Math.round(width  * scale)
      height = Math.round(height * scale)
      const canvas = document.createElement('canvas')
      canvas.width  = width
      canvas.height = height
      canvas.getContext('2d').drawImage(img, 0, 0, width, height)
      canvas.toBlob(
        (blob) => {
          resolve(new File([blob], file.name.replace(/\.[^.]+$/, '.jpg'), {
            type: 'image/jpeg',
            lastModified: file.lastModified,
          }))
        },
        'image/jpeg',
        JPEG_Q
      )
    }
    img.onerror = () => { URL.revokeObjectURL(url); resolve(file) }
    img.src = url
  })
}

export default function SheetUploadZone({ disabled, onProcess }) {
  const [files, setFiles] = useState([])
  const [names, setNames] = useState([])
  const [showNames, setShowNames] = useState(false)
  const [compressing, setCompressing] = useState(false)

  const onDrop = useCallback(async (accepted) => {
    setCompressing(true)
    const compressed = await Promise.all(accepted.map(compressImage))
    setCompressing(false)
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      const novel = compressed.filter(f => !existing.has(f.name))
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
    disabled: disabled || compressing,
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
        className={`${styles.dropzone} ${isDragActive ? styles.active : ''} ${(disabled || compressing) ? styles.disabled : ''}`}
      >
        <input {...getInputProps()} />
        {compressing
          ? <p>Compressing images…</p>
          : isDragActive
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
              disabled={disabled || compressing || files.length === 0}
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
