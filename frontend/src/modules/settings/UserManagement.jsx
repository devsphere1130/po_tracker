import { useState } from 'react'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import DataTable, { Pagination } from '../../components/DataTable'
import { Field, Input, Select } from '../../components/FormControls'
import StatusBadge from '../../components/StatusBadge'
import Modal from '../../components/Modal'
import ConfirmDialog from '../../components/ConfirmDialog'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import useList from '../../hooks/useList'
import { usersApi } from '../../api/settings'
import { errorMessage, fieldErrors } from '../../api/client'
import { fmtDateTime } from '../../utils/format'

function UserForm({ initial, onClose, onSaved }) {
  const toast = useToast()
  const [form, setForm] = useState({ username: '', first_name: '', last_name: '', email: '', role: 'staff', is_active: true, ...(initial || {}), password: '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErrors({}); setFormError('')
    try {
      const body = { ...form }
      if (!body.password) delete body.password
      delete body.id; delete body.date_joined; delete body.last_login
      if (initial) await usersApi.update(initial.id, body)
      else await usersApi.create(body)
      toast.success(initial ? 'User updated.' : 'User created.')
      onSaved()
    } catch (err) { setErrors(fieldErrors(err)); setFormError(errorMessage(err)); setBusy(false) }
  }
  return (
    <Modal title={initial ? `Edit user — ${initial.username}` : 'Add user'} onClose={onClose}
      footer={<><button className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" form="user-form" disabled={busy}>{busy ? 'Saving…' : 'Save user'}</button></>}>
      <form id="user-form" className="stack" onSubmit={submit}>
        {formError && <div className="alert alert-error">{formError}</div>}
        <div className="form-grid">
          <Field label="Username" required error={errors.username}><Input value={form.username} onChange={set('username')} required disabled={!!initial} /></Field>
          <Field label="Role" required><Select value={form.role} onChange={set('role')}><option value="staff">Staff</option><option value="admin">Admin</option></Select></Field>
          <Field label="First name"><Input value={form.first_name} onChange={set('first_name')} /></Field>
          <Field label="Last name"><Input value={form.last_name} onChange={set('last_name')} /></Field>
          <Field label="Email" error={errors.email}><Input type="email" value={form.email} onChange={set('email')} /></Field>
          <Field label={initial ? 'New password (leave blank to keep)' : 'Password'} required={!initial} error={errors.password} hint="Min. 8 characters; not common or all-numeric">
            <Input type="password" autoComplete="new-password" value={form.password} onChange={set('password')} required={!initial} invalid={!!errors.password} />
          </Field>
          <label className="check full"><input type="checkbox" checked={form.is_active} onChange={set('is_active')} /> Active (can sign in)</label>
        </div>
      </form>
    </Modal>
  )
}

export default function UserManagement() {
  const toast = useToast()
  const { user: me } = useAuth()
  const list = useList(usersApi.list)
  const [modal, setModal] = useState(null)
  const columns = [
    { key: 'username', header: 'Username', render: (u) => <strong>{u.username}</strong> },
    { key: 'name', header: 'Name', render: (u) => `${u.first_name} ${u.last_name}`.trim() || '—' },
    { key: 'email', header: 'Email', render: (u) => u.email || '—' },
    { key: 'role', header: 'Role', render: (u) => <span style={{ textTransform: 'capitalize' }}>{u.role}</span> },
    { key: 'is_active', header: 'Status', render: (u) => <StatusBadge status={u.is_active ? 'active' : 'inactive'} /> },
    { key: 'last_login', header: 'Last login', render: (u) => fmtDateTime(u.last_login) },
    { key: 'a', header: '', render: (u) => (
      <div className="actions">
        <button className="btn btn-sm btn-icon" onClick={() => setModal({ type: 'form', user: u })} title="Edit"><Pencil size={14} /></button>
        {u.id !== me.id && <button className="btn btn-sm btn-icon btn-danger" onClick={() => setModal({ type: 'del', user: u })} title="Delete"><Trash2 size={14} /></button>}
      </div>) },
  ]
  return (
    <div className="card">
      <div className="card-head"><h3>Users</h3><button className="btn btn-primary btn-sm" onClick={() => setModal({ type: 'form' })}><Plus size={14} /> Add user</button></div>
      <DataTable columns={columns} rows={list.rows} loading={list.loading} error={list.error} onRetry={list.reload} emptyTitle="No users" />
      <Pagination page={list.params.page} pageSize={list.params.page_size} count={list.count} onPage={list.setPage} />
      {modal?.type === 'form' && <UserForm initial={modal.user} onClose={() => setModal(null)} onSaved={() => { setModal(null); list.reload() }} />}
      {modal?.type === 'del' && <ConfirmDialog title="Delete user" onClose={() => setModal(null)} message={`Delete user "${modal.user.username}"? Consider deactivating instead to keep the audit trail.`}
        onConfirm={async () => { await usersApi.remove(modal.user.id); toast.success('User deleted.'); list.reload() }} />}
    </div>
  )
}
