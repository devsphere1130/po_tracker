import { useState } from 'react'
import Modal from '../../components/Modal'
import { Field, Input, Select, TextArea } from '../../components/FormControls'
import { supplyApi } from '../../api/supply'
import { errorMessage, fieldErrors } from '../../api/client'
import { useToast } from '../../components/Toast'
import { qty, todayIso, uomLabel } from '../../utils/format'

/**
 * Record (or edit) a supply entry against a PO. `po` is the full PO detail (with items).
 * The server enforces: positive quantity, no oversupply, no supply on cancelled POs.
 */
export default function SupplyEntryForm({ po, entry, defaultItemId, onClose, onSaved }) {
  const toast = useToast()
  const openItems = po.items.filter((i) => Number(i.pending_quantity) > 0 || (entry && i.id === entry.item))
  const [form, setForm] = useState({
    item: entry?.item ?? defaultItemId ?? openItems[0]?.id ?? '',
    quantity: entry?.quantity ?? '',
    supply_date: entry?.supply_date ?? todayIso(),
    challan_number: entry?.challan_number ?? '',
    remarks: entry?.remarks ?? '',
  })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const item = po.items.find((i) => i.id === Number(form.item))
  // when editing the same line, its own quantity is available again
  const maxQty = item ? Number(item.pending_quantity) + (entry && entry.item === item.id ? Number(entry.quantity) : 0) : 0

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    setFormError('')
    try {
      const body = { ...form, item: Number(form.item), po: po.id }
      const saved = entry ? await supplyApi.update(entry.id, body) : await supplyApi.create(body)
      toast.success(entry ? 'Supply entry updated.' : 'Supply recorded.')
      onSaved(saved)
    } catch (err) {
      setErrors(fieldErrors(err))
      setFormError(errorMessage(err))
      setBusy(false)
    }
  }

  return (
    <Modal title={`${entry ? 'Edit supply' : 'Record supply'} — PO ${po.po_number}`} onClose={onClose}
      footer={<>
        <button className="btn" onClick={onClose} disabled={busy}>Cancel</button>
        <button className="btn btn-primary" form="supply-form" disabled={busy || !item}>{busy ? 'Saving…' : 'Save supply'}</button>
      </>}>
      {openItems.length === 0 && !entry ? <div className="alert alert-info">Every line of this PO is fully supplied.</div> : (
        <form id="supply-form" className="stack" onSubmit={submit}>
          {formError && <div className="alert alert-error" role="alert">{formError}</div>}
          <div className="form-grid">
            <Field label="Material line" required className="full" error={errors.item}>
              <Select value={form.item} onChange={set('item')} invalid={!!errors.item} disabled={!!entry && false}>
                {(entry ? po.items : openItems).map((i) => (
                  <option key={i.id} value={i.id}>{i.material_name} — ordered {qty(i.ordered_quantity)}, pending {qty(i.pending_quantity)} {uomLabel(i.uom)}</option>
                ))}
              </Select>
            </Field>
            <Field label={`Supplied quantity${item ? ` (${uomLabel(item.uom)})` : ''}`} required error={errors.quantity} hint={item ? `Maximum ${qty(maxQty)} (pending balance)` : undefined}>
              <Input type="number" step="0.001" min="0.001" max={maxQty || undefined} value={form.quantity} onChange={set('quantity')} invalid={!!errors.quantity} required autoFocus />
            </Field>
            <Field label="Supply date" required error={errors.supply_date}><Input type="date" min={po.po_date} value={form.supply_date} onChange={set('supply_date')} invalid={!!errors.supply_date} required /></Field>
            <Field label="Delivery challan no." error={errors.challan_number}><Input value={form.challan_number} onChange={set('challan_number')} maxLength={60} /></Field>
            <Field label="Remarks" className="full"><TextArea rows={2} value={form.remarks} onChange={set('remarks')} /></Field>
          </div>
        </form>
      )}
    </Modal>
  )
}
