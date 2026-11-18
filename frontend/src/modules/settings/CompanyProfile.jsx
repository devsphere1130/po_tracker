import { useEffect, useState } from 'react'
import { Field, Input, TextArea } from '../../components/FormControls'
import { ErrorBanner, Loading } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import { getCompany, saveCompany } from '../../api/settings'
import { errorMessage, fieldErrors } from '../../api/client'

export default function CompanyProfile() {
  const toast = useToast()
  const { isAdmin } = useAuth()
  const [form, setForm] = useState(null)
  const [error, setError] = useState('')
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  useEffect(() => { getCompany().then(setForm).catch((e) => setError(errorMessage(e))) }, [])
  if (error) return <ErrorBanner message={error} />
  if (!form) return <Loading />
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setErrors({})
    try { setForm(await saveCompany(form)); toast.success('Company profile saved.') } catch (err) { setErrors(fieldErrors(err)); toast.error(errorMessage(err)) } finally { setBusy(false) }
  }

  return (
    <form className="card card-pad" style={{ maxWidth: 760 }} onSubmit={submit}>
      <h3 style={{ marginBottom: 12 }}>Supplier company profile</h3>
      {!isAdmin && <div className="alert alert-info" style={{ marginBottom: 12 }}>Only an Admin can edit the company profile.</div>}
      <fieldset disabled={!isAdmin} style={{ border: 0, padding: 0, margin: 0 }}>
        <div className="form-grid">
          <Field label="Company name" required error={errors.name}><Input value={form.name} onChange={set('name')} required /></Field>
          <Field label="GST number" error={errors.gst_number}><Input value={form.gst_number} onChange={set('gst_number')} maxLength={15} /></Field>
          <Field label="Email" error={errors.email}><Input type="email" value={form.email} onChange={set('email')} /></Field>
          <Field label="Phone"><Input value={form.phone} onChange={set('phone')} /></Field>
          <Field label="Address" className="full"><TextArea rows={3} value={form.address} onChange={set('address')} /></Field>
        </div>
      </fieldset>
      {isAdmin && <div style={{ marginTop: 14 }}><button className="btn btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Save profile'}</button></div>}
    </form>
  )
}
