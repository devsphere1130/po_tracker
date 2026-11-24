import { useState } from 'react'
import Modal from '../../components/Modal'
import { Field, Input, TextArea } from '../../components/FormControls'
import { customersApi } from '../../api/customers'
import { errorMessage, fieldErrors } from '../../api/client'
import { useToast } from '../../components/Toast'

const EMPTY = {
  customer_code: '', name: '', contact_person: '', email: '', mobile: '', gst_number: '',
  billing_address: '', shipping_address: '', is_active: true,
}

/** Add / edit a customer. `initial` null = create. onSaved(customer) receives the saved record. */
export default function CustomerForm({ initial, onClose, onSaved, presetName }) {
  const toast = useToast()
  const [form, setForm] = useState(initial ? { ...EMPTY, ...initial } : { ...EMPTY, name: presetName || '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    setFormError('')
    try {
      const payload = { ...form }
      delete payload.po_count
      const saved = initial ? await customersApi.update(initial.id, payload) : await customersApi.create(payload)
      toast.success(initial ? 'Customer updated.' : 'Customer added.')
      onSaved(saved)
    } catch (err) {
      const fe = fieldErrors(err)
      setErrors(fe)
      setFormError(Object.keys(fe).length ? 'Please fix the highlighted fields.' : errorMessage(err))
      setBusy(false)
    }
  }

  return (
    <Modal
      title={initial ? `Edit customer — ${initial.name}` : 'Add customer'}
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button className="btn btn-primary" form="customer-form" disabled={busy}>{busy ? 'Saving…' : 'Save customer'}</button>
        </>
      }
    >
      <form id="customer-form" onSubmit={submit} className="stack">
        {formError && <div className="alert alert-error">{formError}</div>}
        <div className="form-grid">
          <Field label="Customer code" required error={errors.customer_code}><Input value={form.customer_code} onChange={set('customer_code')} invalid={!!errors.customer_code} required maxLength={30} /></Field>
          <Field label="Customer name" required error={errors.name}><Input value={form.name} onChange={set('name')} invalid={!!errors.name} required maxLength={200} /></Field>
          <Field label="Contact person" error={errors.contact_person}><Input value={form.contact_person} onChange={set('contact_person')} /></Field>
          <Field label="Email" error={errors.email}><Input type="email" value={form.email} onChange={set('email')} invalid={!!errors.email} /></Field>
          <Field label="Mobile" error={errors.mobile}><Input value={form.mobile} onChange={set('mobile')} invalid={!!errors.mobile} /></Field>
          <Field label="GST number" error={errors.gst_number} hint="15 characters, e.g. 27AABCA1234F1Z5"><Input value={form.gst_number} onChange={set('gst_number')} invalid={!!errors.gst_number} maxLength={15} /></Field>
          <Field label="Billing address" className="full"><TextArea rows={2} value={form.billing_address} onChange={set('billing_address')} /></Field>
          <Field label="Shipping address" className="full"><TextArea rows={2} value={form.shipping_address} onChange={set('shipping_address')} /></Field>
          <label className="check full"><input type="checkbox" checked={form.is_active} onChange={set('is_active')} /> Active (available for new purchase orders)</label>
        </div>
      </form>
    </Modal>
  )
}
