import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, RefreshCw, Save } from 'lucide-react'
import PageHeader from '../../components/PageHeader'
import { ErrorBanner, Loading } from '../../components/DataTable'
import { Field, Input, OptionSelect, TextArea } from '../../components/FormControls'
import StatusBadge from '../../components/StatusBadge'
import AttachmentPreview from '../../components/AttachmentPreview'
import LineItemsEditor, { blankItem, itemsPayload } from '../../components/LineItemsEditor'
import { useToast } from '../../components/Toast'
import { useCustomers, useMaterials } from '../../hooks/useOptions'
import { ocrApi } from '../../api/ocr'
import { errorMessage } from '../../api/client'
import { lineAmount, money } from '../../utils/format'
import CustomerForm from '../customers/CustomerForm'
import MaterialForm from '../materials/MaterialForm'

function toForm(data) {
  const d = data || {}
  return {
    customer: d.customer ?? '', po_number: d.po_number || '', po_date: d.po_date || '', delivery_date: d.delivery_date || '', notes: d.notes || '',
    items: (d.items?.length ? d.items : [blankItem()]).map((i) => ({ material: i.material ?? '', original_description: i.original_description || '', ordered_quantity: i.ordered_quantity ?? '', uom: i.uom || 'NOS', unit_price: i.unit_price ?? '' })),
  }
}

export default function OCRVerification() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [customers, reloadCustomers] = useCustomers(true)
  const [materials, reloadMaterials] = useMaterials(true)
  const [ex, setEx] = useState(null)
  const [form, setForm] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [formError, setFormError] = useState('')
  const [dialog, setDialog] = useState(null)
  const [showText, setShowText] = useState(false)

  const apply = useCallback((e) => { setEx(e); setForm(toForm(e.working_data)) }, [])
  const load = useCallback(() => ocrApi.get(id).then(apply).catch((e) => setError(errorMessage(e))), [id, apply])
  useEffect(() => { load() }, [load])

  const extracted = ex?.extracted_data || {}
  const locked = ex?.status === 'converted'
  const hdr = extracted.header || {}
  const original = useMemo(() => toForm(extracted.form), [extracted.form])

  if (error) return <ErrorBanner message={error} onRetry={load} />
  if (!ex || !form) return <Loading />

  /** Highlight: empty -> missing (red); unchanged uncertain extraction -> uncertain (amber). */
  const hl = (field, value) => {
    if (locked) return ''
    if (value === '' || value === null || value === undefined) return 'missing'
    const f = hdr[field]
    const unchanged = String(original[field] ?? '') === String(value ?? '')
    return f && f.status !== 'ok' && unchanged ? 'uncertain' : ''
  }
  const itemFlags = form.items.map((it, idx) => {
    const src = extracted.items?.[idx]
    const out = {}
    if (!it.material) out.material = 'missing'
    else if (src?.flags?.includes('material_match_weak') && String(original.items[idx]?.material ?? '') !== String(it.material)) out.material = ''
    if (it.unit_price === '') out.unit_price = 'missing'
    if (src && Number(it.ordered_quantity) === Number(src.quantity) && src.confidence < 0.8) out.quantity = 'uncertain'
    if (src?.line_total && Math.abs(lineAmount(it.ordered_quantity, it.unit_price) - Number(src.line_total)) > 1) { out.line_total = 'uncertain'; out.quantity = 'uncertain'; out.unit_price = out.unit_price || 'uncertain' }
    return out
  })

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))
  const payload = () => ({
    customer: Number(form.customer) || null, po_number: form.po_number, po_date: form.po_date || null,
    delivery_date: form.delivery_date || null, notes: form.notes, items: itemsPayload(form.items),
  })
  const act = async (key, fn, ok) => {
    setBusy(key); setFormError('')
    try { const r = await fn(); if (ok) toast.success(ok); return r } catch (e) { setFormError(errorMessage(e)); window.scrollTo({ top: 0, behavior: 'smooth' }) } finally { setBusy('') }
  }
  const saveDraft = () => act('save', async () => { const e = await ocrApi.saveDraft(ex.id, payload()); setEx(e) }, 'Draft saved.')
  const rescan = () => act('scan', async () => apply(await ocrApi.scan(ex.id)), 'Document re-scanned; previous corrections were reset.')
  const verify = () => act('verify', async () => { await ocrApi.saveDraft(ex.id, payload()); const e = await ocrApi.verify(ex.id, payload()); setEx(e); return e }, 'Details verified.')
  const createPo = () => act('create', async () => {
    let cur = ex
    if (cur.status !== 'verified') { await ocrApi.saveDraft(ex.id, payload()); cur = await ocrApi.verify(ex.id, payload()) }
    const po = await ocrApi.createPo(cur.id)
    navigate(`/purchase-orders/${po.id}`)
  }, 'Purchase order created from verified OCR data.')

  const custMatch = hdr.customer_name
  const failed = ex.status === 'failed'

  return (
    <>
      <PageHeader
        title={<span className="flex">{ex.original_filename} <StatusBadge status={ex.status} label={ex.status_display} /></span>}
        subtitle={<>Engine: {ex.engine === 'tesseract' ? `Tesseract OCR${ex.ocr_confidence != null ? ` (avg. word confidence ${(ex.ocr_confidence * 100).toFixed(0)}%)` : ''}` : ex.engine === 'pdf-text' ? 'PDF text layer (no OCR needed)' : '—'}{ex.is_demo && ' · Demo document'}</>}
        actions={<>
          <Link className="btn" to={ex.message_id ? '/inbox' : '/ocr'}>Back</Link>
          {!locked && <button className="btn" disabled={!!busy} onClick={rescan}><RefreshCw size={15} /> Re-scan</button>}
          {!locked && !failed && <button className="btn" disabled={!!busy} onClick={saveDraft}><Save size={15} /> Save draft</button>}
          {!locked && !failed && <button className="btn" disabled={!!busy} onClick={verify}><CheckCircle2 size={15} /> {busy === 'verify' ? 'Verifying…' : 'Verify details'}</button>}
          {!locked && !failed && <button className="btn btn-primary" disabled={!!busy} onClick={createPo}>{busy === 'create' ? 'Creating…' : 'Verify & create PO'}</button>}
        </>} />

      {formError && <div className="alert alert-error" style={{ marginBottom: 12 }} role="alert">{formError}</div>}
      {locked && <div className="alert alert-ok" style={{ marginBottom: 12 }}>Converted to purchase order <Link to={`/purchase-orders/${ex.linked_po}`}><strong>{ex.linked_po_number}</strong></Link>. This record is now read-only.</div>}
      {failed && <div className="alert alert-error" style={{ marginBottom: 12 }}><strong>Extraction failed:</strong> {ex.error_message}<div className="small">You can still create the PO manually from the PO screen, or try Re-scan.</div></div>}
      {ex.status === 'verified' && <div className="alert alert-info" style={{ marginBottom: 12 }}>Details are verified. Any change requires verifying again before the PO is created.</div>}

      <div className="split">
        <div className="preview"><AttachmentPreview url={ex.file_url} contentType={ex.content_type} filename={ex.original_filename} /></div>
        <div className="stack">
          {!failed && (
            <div className="card card-pad stack" style={{ gap: 10 }}>
              <div className="legend">
                <span><span className="dot" style={{ background: '#e0a030' }} />Uncertain — check against the document</span>
                <span><span className="dot" style={{ background: 'var(--danger)' }} />Missing / required</span>
              </div>
              {(extracted.warnings || []).map((w, i) => <div key={i} className="alert alert-warn small">{w}</div>)}
              <div className="small muted">Values were extracted automatically and are never invented: anything the parser could not find is left blank. Review every field before creating the PO.</div>
            </div>
          )}
          {!failed && form && (
            <div className="card card-pad">
              <div className="form-grid">
                <Field label="Customer" required className="full"
                  hint={custMatch?.value ? `Extracted customer name: “${custMatch.value}”${custMatch.matched_customer_id ? '' : ' — no matching customer in master'}` : 'Customer name not found in document'}>
                  <OptionSelect value={form.customer} onChange={(v) => set('customer', v)} options={customers} placeholder="Select customer…" disabled={locked}
                    invalid={false} />
                  {!locked && !form.customer && <button type="button" className="btn btn-sm" style={{ alignSelf: 'flex-start' }} onClick={() => setDialog({ type: 'customer' })}>+ Create new customer{custMatch?.value ? ` “${custMatch.value}”` : ''}</button>}
                </Field>
                <Field label="PO number" required><Input className={hl('po_number', form.po_number)} value={form.po_number} onChange={(e) => set('po_number', e.target.value)} disabled={locked} /></Field>
                <Field label="PO date" required><Input type="date" className={hl('po_date', form.po_date)} value={form.po_date} onChange={(e) => set('po_date', e.target.value)} disabled={locked} /></Field>
                <Field label="Delivery date"><Input type="date" className={hl('delivery_date', form.delivery_date)} value={form.delivery_date} onChange={(e) => set('delivery_date', e.target.value)} disabled={locked} /></Field>
                <Field label="Stated PO total in document" hint={extracted.computed_total ? `Sum of extracted lines: ${money(extracted.computed_total)}` : undefined}>
                  <Input value={hdr.po_total?.value ? money(hdr.po_total.value) : '— not found —'} disabled />
                </Field>
                <Field label="Notes" className="full"><TextArea rows={2} value={form.notes} onChange={(e) => set('notes', e.target.value)} disabled={locked} /></Field>
              </div>
            </div>
          )}
          {!failed && (
            <div className="card">
              <div className="card-head"><h3>Line items</h3><span className="small muted">Edit, add or delete lines. Map each to a master material.</span></div>
              <div className="card-pad">
                <fieldset disabled={locked} style={{ border: 0, padding: 0, margin: 0 }}>
                  <LineItemsEditor items={form.items} onChange={(items) => set('items', items)} materials={materials} flags={itemFlags}
                    onCreateMaterial={(idx) => setDialog({ type: 'material', idx })} />
                </fieldset>
                <div className="small muted" style={{ marginTop: 8 }}>Saving the PO remembers each original description → material mapping for future documents.</div>
              </div>
            </div>
          )}
          <div className="card card-pad">
            <button className="btn btn-sm" onClick={() => setShowText((s) => !s)}>{showText ? 'Hide' : 'Show'} extracted raw text</button>
            {showText && <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, background: '#f6f8fb', padding: 10, borderRadius: 6, maxHeight: 280, overflow: 'auto' }}>{ex.raw_text || '(no text)'}</pre>}
          </div>
        </div>
      </div>

      {dialog?.type === 'customer' && (
        <CustomerForm presetName={custMatch?.value} onClose={() => setDialog(null)}
          onSaved={(c) => { reloadCustomers(); set('customer', c.id); setDialog(null) }} />
      )}
      {dialog?.type === 'material' && (
        <MaterialForm presetName={form.items[dialog.idx]?.original_description} presetUom={form.items[dialog.idx]?.uom} onClose={() => setDialog(null)}
          onSaved={(m) => { reloadMaterials(); set('items', form.items.map((it, i) => (i === dialog.idx ? { ...it, material: m.id, uom: m.uom } : it))); setDialog(null) }} />
      )}
    </>
  )
}
