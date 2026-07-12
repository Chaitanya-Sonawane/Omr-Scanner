import React, { useCallback, useEffect, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { calibrateTemplate, getTemplateInfo } from '../api.js'
import styles from './CalibrateZone.module.css'

export default function CalibrateZone({ onCalibrated }) {
  const [info, setInfo] = useState(null)       // existing template metadata
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    getTemplateInfo().then(data => {
      if (data) {
        setInfo(data)
        setCollapsed(true)       // template already loaded — collapse by default
        onCalibrated?.()
      }
    })
  }, [])

  const onDrop = useCallback(async (accepted) => {
    if (!accepted.length) return
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const result = await calibrateTemplate(accepted[0])
      setInfo(result)
      setSuccess(`Template built — ${result.bubbles} bubbles, radius ${result.radius}px`)
      setCollapsed(true)
      onCalibrated?.()
    } catch (e) {
      setError(e.response?.data?.detail || 'Calibration failed. Check the reference sheet and try again.')
    } finally {
      setLoading(false)
    }
  }, [onCalibrated])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.png', '.jpg', '.jpeg'] },
    maxFiles: 1,
    disabled: loading,
  })

  return (
    <div className={styles.card}>
      <div className={styles.topRow} onClick={() => setCollapsed(c => !c)} role="button" tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && setCollapsed(c => !c)}
        aria-expanded={!collapsed}>
        <div>
          <h2 className={styles.heading}>
            <span className={styles.step}>⓪</span> Calibrate Template
            {info && <span className={styles.badge}>✓ loaded — {info.n_bubbles} bubbles</span>}
          </h2>
          <p className={styles.sub}>
            {info
              ? 'Template is ready. Re-upload only if the sheet layout changes.'
              : 'Upload one clean reference sheet once to build the bubble coordinate map.'}
          </p>
        </div>
        <span className={styles.chevron} aria-hidden="true">{collapsed ? '▶' : '▼'}</span>
      </div>

      {!collapsed && (
        <div className={styles.body}>
          <div className={styles.infoBox}>
            <strong>Run this once</strong> per sheet layout. After calibration every scan uses
            the fixed template — no circle detection per sheet. Re-run only if you print on a
            different layout or printer.
          </div>

          <div
            {...getRootProps()}
            className={`${styles.dropzone} ${isDragActive ? styles.active : ''} ${loading ? styles.disabled : ''}`}
          >
            <input {...getInputProps()} />
            {loading
              ? <><span className={styles.spinner} /> Calibrating…</>
              : isDragActive
              ? <p>Drop the reference sheet here</p>
              : <p>Drag &amp; drop your <strong>cleanest reference sheet</strong><br />
                  <span className={styles.hint}>PNG · JPG — one image only</span></p>
            }
          </div>

          {error   && <p className={styles.error}>⚠ {error}</p>}
          {success && <p className={styles.success}>✓ {success}</p>}

          {info && (
            <div className={styles.metaRow}>
              <span>Bubbles: <strong>{info.n_bubbles ?? info.bubbles}</strong></span>
              <span>Canvas: <strong>{info.canon_w ?? 1400} × {info.canon_h ?? 2200}</strong></span>
              <span>Radius: <strong>{info.radius}px</strong></span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
