import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Copy, Eye, FileScan, Mail, RefreshCw, RotateCcw, ScanText, Send, XCircle } from 'lucide-react'
import PageHeader from '../../components/PageHeader'
import DataTable, { Pagination } from '../../components/DataTable'
import { Field, SearchInput, Select } from '../../components/FormControls'
import StatusBadge from '../../components/StatusBadge'
import Modal from '../../components/Modal'
import AttachmentPreview from '../../components/AttachmentPreview'
import { useToast } from '../../components/Toast'
import useList from '../../hooks/useList'
import { inboxApi } from '../../api/inbox'
import { errorMessage } from '../../api/client'
import { fmtDateTime } from '../../utils/format'

const typeLabel = (ct) => (ct === 'application/pdf' ? 'PDF' : ct.replace('image/', '').toUpperCase())

export default function Inbox() {
  const toast = useToast()
  const navigate = useNavigate()
  const list = useList(inboxApi.list, { ordering: '-received_at' })
  const [busy, setBusy] = useState('')
  const [preview, setPreview] = useState(null)

  const run = async (key, fn, ok) => {
    setBusy(key)
    try { const r = await fn(); if (ok) toast.success(ok(r)); list.reload(); return r } catch (e) { toast.error(errorMessage(e)) } finally { setBusy('') }
  }

  const scan = async (m) => {
    const ex = await run(`scan${m.id}`, () => inboxApi.scan(m.id))
    if (ex) { if (ex.status === 'failed') toast.error(ex.error_message); navigate(`/ocr/${ex.id}`) }
  }

  const columns = [
    { key: 'received_at', header: 'Received', render: (m) => <span className="nowrap">{fmtDateTime(m.received_at)}</span> },
    { key: 'sender', header: 'Sender', render: (m) => <div><strong>{m.sender_name || '—'}</strong><div className="small muted">{m.sender_email}</div></div> },
    { key: 'subject', header: 'Subject', render: (m) => <div>{m.subject}{m.is_demo && <> <span className="badge badge-demo" title="Simulated email">Demo</span></>}{m.status_note && <div className="small muted">{m.status_note}</div>}</div> },
    {
      key: 'attachment', header: 'Attachment', render: (m) => m.attachments.length === 0 ? <span className="muted">None</span> : m.attachments.map((a) => (
        <div key={a.id} className="flex" style={{ gap: 6 }}>
          <button className="btn btn-sm btn-ghost" style={{ padding: '1px 4px', color: 'var(--primary)' }} onClick={() => setPreview(a)} title="Preview original attachment"><Eye size={14} /> {a.filename}</button>
          <span className="badge badge-new">{typeLabel(a.content_type)}</span>
        </div>
      )),
    },
    { key: 'status', header: 'Status', render: (m) => <div><StatusBadge status={m.status} />{m.converted_po && <div className="small"><Link to={`/purchase-orders/${m.converted_po}`}>PO {m.converted_po_number}</Link></div>}</div> },
    {
      key: 'actions', header: '', render: (m) => {
        const ex = m.attachments[0]?.extraction
        const closed = m.status === 'duplicate' || m.status === 'rejected'
        return (
          <div className="actions" style={{ flexWrap: 'wrap', minWidth: 190 }}>
            {m.status === 'converted' && <Link className="btn btn-sm" to={`/purchase-orders/${m.converted_po}`}>View PO</Link>}
            {!closed && m.status !== 'converted' && m.attachments.length > 0 && (
              ex && ex.status !== 'failed' && ex.status !== 'pending'
                ? <Link className="btn btn-sm btn-primary" to={`/ocr/${ex.id}`}><FileScan size={14} /> Verify & convert</Link>
                : <button className="btn btn-sm btn-primary" disabled={busy === `scan${m.id}`} onClick={() => scan(m)}><ScanText size={14} /> {busy === `scan${m.id}` ? 'Scanning…' : ex?.status === 'failed' ? 'Retry OCR' : 'Scan with OCR'}</button>
            )}
            {!closed && m.status !== 'converted' && (
              <>
                <button className="btn btn-sm btn-icon" title="Mark as duplicate" onClick={() => run(`d${m.id}`, () => inboxApi.mark(m.id, 'duplicate', 'Marked duplicate by user'), () => 'Marked as duplicate.')}><Copy size={14} /></button>
                <button className="btn btn-sm btn-icon btn-danger" title="Reject" onClick={() => run(`r${m.id}`, () => inboxApi.mark(m.id, 'rejected', 'Rejected by user'), () => 'Email rejected.')}><XCircle size={14} /></button>
              </>
            )}
            {closed && <button className="btn btn-sm" onClick={() => run(`x${m.id}`, () => inboxApi.mark(m.id, 'restore'), () => 'Email restored.')}><RotateCcw size={14} /> Restore</button>}
          </div>
        )
      },
    },
  ]

  return (
    <>
      <PageHeader title="Inbox" subtitle="Purchase order emails received from customers"
        actions={<>
          <button className="btn" disabled={busy === 'simulate'} onClick={() => run('simulate', inboxApi.simulate, (m) => `Simulated email received: ${m.subject}`)}><Send size={15} /> Simulate incoming email</button>
          <button className="btn btn-primary" disabled={busy === 'sync'} onClick={() => run('sync', () => inboxApi.sync('demo'), (r) => (r.imported ? `Demo sync complete: ${r.imported} new email(s) imported.` : 'Demo sync complete: no new emails.'))}>
            <RefreshCw size={15} className={busy === 'sync' ? 'spin' : ''} /> {busy === 'sync' ? 'Syncing…' : 'Sync now'}
          </button>
        </>} />
      <div className="alert alert-warn flex" style={{ marginBottom: 14 }}>
        <Mail size={16} />
        <span><strong>Demo mode.</strong> This inbox contains simulated emails stored in PostgreSQL. No real Gmail or Microsoft mailbox is connected — configure it in <Link to="/settings">Settings</Link> once OAuth credentials exist.</span>
      </div>
      <div className="card">
        <div className="toolbar">
          <SearchInput value={list.params.search} onChange={(v) => list.setFilter('search', v)} placeholder="Search sender, subject, attachment…" />
          <Field label="Status">
            <Select value={list.params.status ?? ''} onChange={(e) => list.setFilter('status', e.target.value)}>
              <option value="">All</option><option value="new">New</option><option value="scanned">Scanned</option><option value="verified">Verified</option>
              <option value="converted">Converted to PO</option><option value="duplicate">Duplicate</option><option value="rejected">Rejected</option>
            </Select>
          </Field>
          <button className="btn" onClick={list.reset}>Clear</button>
        </div>
        <DataTable columns={columns} rows={list.rows} loading={list.loading} error={list.error} onRetry={list.reload}
          emptyTitle="Inbox is empty" emptyHint="Click “Sync now” to import the simulated demo emails." />
        <Pagination page={list.params.page} pageSize={list.params.page_size} count={list.count} onPage={list.setPage} onPageSize={list.setPageSize} />
      </div>
      {preview && (
        <Modal wide title={preview.filename} onClose={() => setPreview(null)} footer={<a className="btn" href={preview.file_url} target="_blank" rel="noreferrer">Open in new tab</a>}>
          <div className="preview" style={{ position: 'static', height: '65vh' }}><AttachmentPreview url={preview.file_url} contentType={preview.content_type} filename={preview.filename} /></div>
        </Modal>
      )}
    </>
  )
}
