import React, { useEffect, useRef, useState } from 'react'
import styles from './MobileCapture.module.css'

export default function MobileCapture({ onBack, sessionId }) {
  const iframeRef = useRef(null)
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    // Post message listener to receive scan results from mobile iframe
    const handleMessage = (event) => {
      if (event.data.type === 'OMR_SCAN_COMPLETE') {
        // Handle scan completion - could trigger sheet upload
        console.log('Scan complete:', event.data)
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [])

  const handleLoad = () => {
    setIsLoaded(true)
  }

  return (
    <div className={styles.mobileCapture}>
      <div className={styles.header}>
        <button onClick={onBack} className={styles.backBtn}>
          ← Back to Desktop View
        </button>
        <h2>Mobile Camera Capture</h2>
      </div>
      
      {!isLoaded && (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          Loading mobile capture interface...
        </div>
      )}
      
      <iframe
        ref={iframeRef}
        src="/mobile/"
        className={styles.iframe}
        onLoad={handleLoad}
        title="OMR Mobile Capture"
        allow="camera; microphone"
      />
    </div>
  )
}
