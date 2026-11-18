import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import PageHeader from '../../components/PageHeader'
import { Field, Input, OptionSelect, TextArea } from '../../components/FormControls'
import { ErrorBanner, Loading } from '../../components/DataTable'
import LineItemsEditor, { blankItem, itemsPayload } from '../../components/LineItemsEditor'
import { useToast } from '../../components/Toast'
import { useCustomers, useMaterials } from '../../hooks/useOptions'
import { purchaseOrdersApi } from '../../api/purchaseOrders'
import { errorMessage, fieldErrors } from '../../api/client'
import { todayIso } from '../../utils/format'

/** Create (/purchase-orders/new) or edit (/purchase-orders/:id/edit) a purchase order. */
export default function PurchaseOrderForm() {
  const { id } = useParams()
  const [sp] = useSearchParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [customers] = useCustomers(true)
  const [materials] = useMaterials(true)
  const [header, setHeader] = useState({ po_number: '', customer: sp.get('customer') || '', po_date: todayIso(), delivery_date: '', notes: '' })
  const [items, setItems] = useState([blankItem()])
  const [loading, setLoading] = useState(!!id)
  const [loadError, setLoadError] = useState('')
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)
  const [file, setFile] = useState(null)
  const [existing, setExisting] = useState(null)
  const fileRef = useRef()

  useEffect(() => {
    if (!id) return
    purchaseOrdersApi.get(id).then((po) => {
      setExisting(po)
      setHeader({ po_number: po.po_number, customer: po.customer, po_date: po.po_date, delivery_date: po.delivery_date || '', notes: po.notes })
      setItems(po.items.map((i) => ({ ...i, material: i.material })))
    }).catch((e) => setLoadError(errorMessage(e))).finally(() => setLoading(false))
  }, [id])

  // include the PO's current customer/materials even if they were later deactivated
  const customerOptions = existing && !customers.some((c) => c.id === existing.customer) ? [...customers, { id: existing.customer, name: existing.customer_name }] : customers
  const materialOptions = [...materials]
  items.forEach((i) => { if (i.material && !materialOptions.some((m) => m.id === Number(i.material))) materialOptions.push({ id: Number(i.material), material_code: i.material_code, name: i.material_name, uom: i.uom, default_rate: i.unit_price }) })

  const set = (k) => (e) => setHeader({ ...header, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    setFormError('')
    try {
      const body = { ...header, customer: Number(header.customer) || null, delivery_date: header.delivery_date || null, items: itemsPayload(items) }
      let po = id ? await purchaseOrdersApi.update(id, body) : await purchaseOrdersApi.create({ ...body, source: 'manual' })
      if (file) po = await purchaseOrdersApi.uploadAttachment(po.id, file)
      toast.success(id ? 'Purchase order updated.' : 'Purchase order created.')
      navigate(`/purchase-orders/${po.id}`)
    } catch (err) {
      setErrors(fieldErrors(err))
      setFormError(errorMessage(err))
      setBusy(false)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  if (loading) return <Loading />
  if (loadError) return <ErrorBanner message={loadError} />

  return (
    <form onSubmit={submit}>
      <PageHeader title={id ? `Edit PO ${existing?.po_number}` : 'New purchase order'}
        subtitle={id ? 'Ordered quantities cannot go below what has already been supplied.' : 'Record a purchase order received from a customer'}
        actions={<>
          <Link className="btn" to={id ? `/purchase-orders/${id}` : '/purchase-orders'}>Cancel</Link>
          <button className="btn btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Save purchase order'}</button>
        </>} />
      {formError && <div className="alert alert-error" style={{ marginBottom: 14 }} role="alert">{formError}</div>}
      <div className="stack">
        <div className="card card-pad">
          <div className="form-grid">
            <Field label="Customer" required error={errors.customer}>
              <OptionSelect value={header.customer} onChange={(v) => setHeader({ ...header, customer: v })} options={customerOptions} placeholder="Select customer…" invalid={!!errors.customer} />
            </Field>
            <Field label="PO number" required error={errors.po_number}><Input value={header.po_number} onChange={set('po_number')} invalid={!!errors.po_number} required maxLength={60} /></Field>
            <Field label="PO date" required error={errors.po_date}><Input type="date" value={header.po_date} onChange={set('po_date')} required /></Field>
            <Field label="Delivery date" error={errors.delivery_date}><Input type="date" value={header.delivery_date} min={header.po_date} onChange={set('delivery_date')} invalid={!!errors.delivery_date} /></Field>
            <Field label="Notes" className="full"><TextArea rows={2} value={header.notes} onChange={set('notes')} /></Field>
            <Field label="Original attachment (PDF / image)" className="full" hint={existing?.attachment_name ? `Current: ${existing.attachment_name} (choose a file to replace)` : undefined}>
              <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(e) => setFile(e.target.files[0] || null)} />
            </Field>
          </div>
        </div>
        <div className="card">
          <div className="card-head"><h3>Line items</h3><span className="small muted">Line amount = quantity × unit price (calculated on the server)</span></div>
          <div className="card-pad"><LineItemsEditor items={items} onChange={setItems} materials={materialOptions} /></div>
        </div>
      </div>
    </form>
  )
}
