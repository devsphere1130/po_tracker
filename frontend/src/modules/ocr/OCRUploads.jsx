import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Upload } from 'lucide-react'
import PageHeader from '../../components/PageHeader'
import DataTable, { Pagination } from '../../components/DataTable'
import { Field, Select } from '../../components/FormControls'
import StatusBadge from '../../components/StatusBadge'
import { useToast } from '../../components/Toast'
import useList from '../../hooks/useList'
import { ocrApi } from '../../api/ocr'
import { errorMessage } from '../../api/client'
import { fmtDateTime } from '../../utils/format'

export default function OCRUploads() {
  const toast = useToast()
  const navigate = useNavigate()
  const fileRef = useRef()
  const [busy, setBusy] = useState(false)
  const list = useList(ocrApi.list)

  const upload = async (file) => {
    if (!file) return
    setBusy(true)
    try {
      const ex = await ocrApi.upload(file)
      if (ex.status === 'failed') toast.error(ex.error_message || 'The document could not be read.')
      else toast.success(`Extraction complete (${ex.engine === 'tesseract' ? 'Tesseract OCR' : 'PDF text layer'}). Please review the fields.`)
      navigate(`/ocr/${ex.id}`)
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const columns = [
    { key: 'created_at', header: 'Uploaded', render: (e) => fmtDateTime(e.created_at) },
    { key: 'original_filename', header: 'Document', render: (e) => <Link to={`/ocr/${e.id}`}><strong>{e.original_filename}</strong></Link> },
    { key: 'origin', header: 'Origin', render: (e) => (e.message_id ? <span>Inbox email{e.is_demo && ' (demo)'}</span> : 'Direct upload') },
    { key: 'engine', header: 'Engine', render: (e) => (e.engine === 'tesseract' ? 'Tesseract OCR' : e.engine === 'pdf-text' ? 'PDF text layer' : '—') },
    { key: 'status', header: 'Status', render: (e) => <StatusBadge status={e.status} label={e.status_display} /> },
    { key: 'conf', header: 'Review', render: (e) => (e.status === 'failed' ? <span className="small" style={{ color: 'var(--danger)' }}>{e.error_message}</span> : e.low_confidence ? <span className="badge badge-pending">Needs attention</span> : e.status === 'processed' ? <span className="badge badge-fulfilled">High confidence</span> : '—') },
    { key: 'po', header: 'PO', render: (e) => (e.linked_po ? <Link to={`/purchase-orders/${e.linked_po}`}>{e.linked_po_number}</Link> : '—') },
  ]

  return (
    <>
      <PageHeader title="OCR Documents" subtitle="Extract purchase order data from PDF, PNG or JPG files using local, open-source OCR (no paid APIs)"
        actions={<>
          <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg" hidden onChange={(e) => upload(e.target.files[0])} />
          <button className="btn btn-primary" disabled={busy} onClick={() => fileRef.current.click()}><Upload size={16} /> {busy ? 'Extracting…' : 'Upload document'}</button>
        </>} />
      <div className="card">
        <div className="toolbar">
          <Field label="Status">
            <Select value={list.params.status ?? ''} onChange={(e) => list.setFilter('status', e.target.value)}>
              <option value="">All</option><option value="processed">Processed</option><option value="verified">Verified</option>
              <option value="converted">Converted</option><option value="failed">Failed</option>
            </Select>
          </Field>
        </div>
        <DataTable columns={columns} rows={list.rows} loading={list.loading} error={list.error} onRetry={list.reload}
          emptyTitle="No documents yet" emptyHint="Upload a PO document, or scan an attachment from the Inbox." />
        <Pagination page={list.params.page} pageSize={list.params.page_size} count={list.count} onPage={list.setPage} onPageSize={list.setPageSize} />
      </div>
    </>
  )
}
