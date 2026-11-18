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
  gmail: 'Gmail API: requires a Google Cloud OAuth client (GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET in backend/.env) and completed user consent (gmail.readonly).',
  microsoft: 'Microsoft Graph: requires an Azure app registration (MS_GRAPH_CLIENT_ID / _SECRET / _TENANT_ID in backend/.env) and Mail.Read consent.',
}

function Connection({ conn, oauth, canEdit, onChange }) {
  const toast = useToast()
  const [form, setForm] = useState({ account_email: conn.account_email, folder: conn.folder })
  const live = conn.provider !== 'demo'
  const save = async () => { try { await inboxApi.updateConnection(conn.id, form); toast.success('Saved.'); onChange() } catch (e) { toast.error(errorMessage(e)) } }
  const connect = async () => { try { await inboxApi.connect(conn.id) } catch (e) { toast.info(errorMessage(e)) } }
  return (
    <div className="card card-pad stack" style={{ gap: 10 }}>
      <div className="flex-between"><h3>{conn.provider_display}</h3><StatusBadge status={conn.state} label={conn.state_display} /></div>
      <div className="muted small">{HELP[conn.provider]}</div>
      {live && <div className="small">OAuth credentials in environment: <strong>{oauth[conn.provider] ? 'present' : 'not configured'}</strong></div>}
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
          <button className="btn btn-primary" disabled={!canEdit} onClick={connect}>Connect (OAuth)</button>
        </div>
      )}
    </div>
  )
}

export default function InboxIntegration() {
  const { isAdmin } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const load = useCallback(() => inboxApi.connections().then(setData).catch((e) => setError(errorMessage(e))), [])
  useEffect(() => { load() }, [load])
  if (error) return <ErrorBanner message={error} onRetry={load} />
  if (!data) return <Loading />
  return (
    <div className="stack">
      <div className={`alert ${data.mode === 'demo' ? 'alert-warn' : 'alert-info'}`}>
        <strong>{data.mode_label}.</strong>{' '}
        {data.mode === 'demo'
          ? 'The Inbox uses simulated emails. No real mailbox is connected and none will be until OAuth is configured and authorised.'
          : 'Live mode is enabled, but a provider only becomes Connected after its OAuth flow completes. That flow is not implemented yet, so all providers remain Disconnected.'}
        {' '}Mode is set by INBOX_MODE in backend/.env.
      </div>
      <div className="grid grid-3">
        {data.connections.map((c) => <Connection key={c.id} conn={c} oauth={data.oauth_configured} canEdit={isAdmin} onChange={load} />)}
      </div>
    </div>
  )
}
