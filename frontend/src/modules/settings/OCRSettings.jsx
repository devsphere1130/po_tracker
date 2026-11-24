import { useEffect, useState } from 'react'
import { ErrorBanner, Loading } from '../../components/DataTable'
import { ocrApi } from '../../api/ocr'
import { errorMessage } from '../../api/client'

export default function OCRSettings() {
  const [info, setInfo] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { ocrApi.engineStatus().then(setInfo).catch((e) => setError(errorMessage(e))) }, [])
  if (error) return <ErrorBanner message={error} />
  if (!info) return <Loading />
  return (
    <div className="card card-pad stack" style={{ maxWidth: 760 }}>
      <h3>OCR configuration</h3>
      <dl className="kv">
        <dt>Tesseract OCR</dt><dd><span className={`badge ${info.available ? 'badge-connected' : 'badge-failed'}`}>{info.available ? 'Available' : 'Not available'}</span></dd>
        <dt>Version</dt><dd>{info.version || '—'}</dd>
        <dt>Binary path</dt><dd className="mono">{info.path || 'not set (searching PATH)'}</dd>
        <dt>Digital PDFs</dt><dd>Text layer is read directly with pypdf (no OCR)</dd>
        <dt>Scanned PDFs / images</dt><dd>Tesseract via pytesseract + Pillow (PNG, JPG, JPEG)</dd>
        <dt>Paid APIs</dt><dd>None — everything runs locally</dd>
      </dl>
      {info.error && <div className="alert alert-error">{info.error}</div>}
      <div className="small muted">To change the Tesseract location set <code>TESSERACT_CMD</code> in <code>backend/.env</code> and restart the backend. Install on Windows: <code>winget install UB-Mannheim.TesseractOCR</code>.</div>
    </div>
  )
}
