import { useState } from 'react'
import Modal from './Modal'
import { errorMessage } from '../api/client'

/** Confirmation for destructive actions. onConfirm may be async; errors are shown inline. */
export default function ConfirmDialog({ title, message, confirmLabel = 'Delete', danger = true, onConfirm, onClose, children }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    setBusy(true)
    setError('')
    try {
      await onConfirm()
      onClose()
    } catch (e) {
      setError(errorMessage(e))
      setBusy(false)
    }
  }

  return (
    <Modal
      title={title}
      onClose={busy ? undefined : onClose}
      footer={
        <>
          <button className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button className={`btn ${danger ? 'btn-solid-danger' : 'btn-primary'}`} onClick={run} disabled={busy}>
            {busy ? 'Working…' : confirmLabel}
          </button>
        </>
      }
    >
      <p style={{ marginTop: 0 }}>{message}</p>
      {children}
      {error && <div className="alert alert-error" style={{ marginTop: 12 }}>{error}</div>}
    </Modal>
  )
}
