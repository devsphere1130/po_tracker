import { useCallback, useEffect, useState } from 'react'
import { Field, Input } from '../../components/FormControls'
import { ErrorBanner, Loading } from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import { inboxApi } from '../../api/inbox'
import { errorMessage } from '../../api/client'
import { fmtDateTime } from '../../utils/format'

const HELP = {
  demo: 'Simulated emails stored in PostgreSQL. Always available in demo mode; no external mailbox is contacted.',
  gmail: 'Gmail (read-only): imports inbox emails from the last 30 days that have a PDF/PNG/JPG attachment. Requires GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET in backend/.env and Google consent.',
  microsoft: 'Microsoft Graph: requires an Azure app registration (MS_GRAPH_CLIENT_ID / _SECRET / _TENANT_ID in backend/.env) and Mail.Read consent.',
}

function Connection({ conn, oauth, canEdit, onChange }) {
  const toast = useToast()
  const [form, setForm] = useState({ account_email: conn.account_email, folder: conn.folder })
  const live = conn.provider !== 'demo'
  const save = async () => { try { await inboxApi.updateConnection(conn.id, form); toast.success('Saved.'); onChange() } catch (e) { toast.error(errorMessage(e)) } }
  const connect = async () => {
    try { const r = await inboxApi.connect(conn.id); window.location.href = r.authorization_url } catch (e) { toast.info(errorMessage(e)) }
  }
  const disconnect = async () => { try { await inboxApi.disconnect(conn.id); toast.success('Disconnected.'); onChange() } catch (e) { toast.error(errorMessage(e)) } }
  const connected = conn.state === 'connected'
  return (
    <div className="card card-pad stack" style={{ gap: 10 }}>
      <div className="flex-between"><h3>{conn.provider_display}</h3><StatusBadge status={conn.state} label={conn.state_display} /></div>
      <div className="muted small">{HELP[conn.provider]}</div>
      {live && <div className="small">OAuth credentials in environment: <strong>{oauth[conn.provider] ? 'present' : 'not configured'}</strong></div>}
      {live && connected && <div className="alert alert-ok small">Connected as <strong>{conn.account_email}</strong>. Use “Sync now” in the Inbox to import emails.</div>}
      {live && (
        <>
          <Field label="Mailbox address (informational)"><Input type="email" value={form.account_email} onChange={(e) => setForm({ ...form, account_email: e.target.value })} disabled={!canEdit} placeholder="orders@yourcompany.com" /></Field>
          <Field label="Folder / label"><Input value={form.folder} onChange={(e) => setForm({ ...form, folder: e.target.value })} disabled={!canEdit} /></Field>
        </>
      )}
      <div className="small muted">Last sync: {fmtDateTime(conn.last_synced_at)}</div>
      {live && (
        <div className="flex">
          <button className="btn" disabled={!canEdit} onClick={save}>Save settings</button>
          {connected
            ? <button className="btn btn-danger" disabled={!canEdit} onClick={disconnect}>Disconnect</button>
            : <button className="btn btn-primary" disabled={!canEdit} onClick={connect}>Connect (OAuth)</button>}
        </div>
      )}
    </div>
  )
}

export default function InboxIntegration() {
  const { isAdmin } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const toast = useToast()
  useEffect(() => {
    const sp = new URLSearchParams(window.location.search)
    if (sp.get('gmail') === 'connected') toast.success(`Gmail connected${sp.get('msg') ? ` as ${sp.get('msg')}` : ''}.`)
    else if (sp.get('gmail') === 'error') toast.error(sp.get('msg') || 'Gmail connection failed.')
    if (sp.get('gmail')) window.history.replaceState({}, '', window.location.pathname)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  const load = useCallback(() => inboxApi.connections().then(setData).catch((e) => setError(errorMessage(e))), [])
  useEffect(() => { load() }, [load])
  if (error) return <ErrorBanner message={error} onRetry={load} />
  if (!data) return <Loading />
  return (
    <div className="stack">
      <div className={`alert ${data.mode === 'demo' ? 'alert-warn' : 'alert-info'}`}>
        <strong>{data.mode_label}.</strong>{' '}
        {data.mode === 'demo'
          ? 'The Inbox uses simulated emails. No real mailbox is connected.'
          : 'Live mode: a mailbox shows Connected only after Google has issued a valid token. Gmail is supported; Microsoft Graph is not implemented yet.'}
        {' '}Mode is set by INBOX_MODE in backend/.env.
      </div>
      <div className="grid grid-3">
        {data.connections.map((c) => <Connection key={c.id} conn={c} oauth={data.oauth_configured} canEdit={isAdmin} onChange={load} />)}
      </div>
    </div>
  )
}
