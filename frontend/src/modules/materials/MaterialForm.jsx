import { useState } from 'react'
import Modal from '../../components/Modal'
import { Field, Input, Select, TextArea } from '../../components/FormControls'
import { materialsApi } from '../../api/materials'
import { errorMessage, fieldErrors } from '../../api/client'
import { useToast } from '../../components/Toast'
import { UOMS, uomLabel } from '../../utils/format'

const EMPTY = { material_code: '', name: '', description: '', category: '', uom: 'NOS', default_rate: '0.00', is_active: true }

export default function MaterialForm({ initial, onClose, onSaved, presetName, presetUom }) {
  const toast = useToast()
  const [form, setForm] = useState(initial ? { ...EMPTY, ...initial } : { ...EMPTY, name: presetName || '', uom: presetUom || 'NOS' })
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
      delete payload.usage_count
      delete payload.uom_display
      const saved = initial ? await materialsApi.update(initial.id, payload) : await materialsApi.create(payload)
      toast.success(initial ? 'Material updated.' : 'Material added.')
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
      title={initial ? `Edit material — ${initial.name}` : 'Add material'}
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button className="btn btn-primary" form="material-form" disabled={busy}>{busy ? 'Saving…' : 'Save material'}</button>
        </>
      }
    >
      <form id="material-form" onSubmit={submit} className="stack">
        {formError && <div className="alert alert-error">{formError}</div>}
        <div className="form-grid">
          <Field label="Material code" required error={errors.material_code}><Input value={form.material_code} onChange={set('material_code')} invalid={!!errors.material_code} required maxLength={30} /></Field>
          <Field label="Material name" required error={errors.name}><Input value={form.name} onChange={set('name')} invalid={!!errors.name} required maxLength={200} /></Field>
          <Field label="Category" error={errors.category}><Input value={form.category} onChange={set('category')} /></Field>
          <Field label="Unit of measurement" required error={errors.uom}>
            <Select value={form.uom} onChange={set('uom')}>{UOMS.map((u) => <option key={u} value={u}>{uomLabel(u)}</option>)}</Select>
          </Field>
          <Field label="Default rate (₹)" error={errors.default_rate}><Input type="number" min="0" step="0.01" value={form.default_rate} onChange={set('default_rate')} invalid={!!errors.default_rate} /></Field>
          <label className="check" style={{ alignSelf: 'end' }}><input type="checkbox" checked={form.is_active} onChange={set('is_active')} /> Active</label>
          <Field label="Description" className="full"><TextArea rows={2} value={form.description} onChange={set('description')} /></Field>
        </div>
      </form>
    </Modal>
  )
}
