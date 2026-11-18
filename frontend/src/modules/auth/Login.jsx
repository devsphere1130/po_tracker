import { useState } from 'react'
import { ClipboardList } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { errorMessage } from '../../api/client'
import { Field, Input } from '../../components/FormControls'

export default function Login() {
  const { login } = useAuth()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(form.username, form.password)
    } catch (err) {
      setError(errorMessage(err))
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card stack" onSubmit={submit}>
        <div>
          <span style={{ width: 38, height: 38, display: 'grid', placeItems: 'center', background: 'var(--primary)', color: '#fff', borderRadius: 9 }}><ClipboardList size={22} /></span>
          <h1>PO Tracker</h1>
          <div className="muted">Sign in to manage purchase orders</div>
        </div>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <Field label="Username" required><Input autoFocus autoComplete="username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required /></Field>
        <Field label="Password" required><Input type="password" autoComplete="current-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /></Field>
        <button className="btn btn-primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      </form>
    </div>
  )
}
