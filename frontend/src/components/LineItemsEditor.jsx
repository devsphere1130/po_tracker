import { Plus, Trash2 } from 'lucide-react'
import { Select } from './FormControls'
import { lineAmount, money, qty as fmtQty, UOMS, uomLabel } from '../utils/format'

export const blankItem = () => ({ material: '', original_description: '', ordered_quantity: '', uom: 'NOS', unit_price: '' })

/** Strip display-only fields before sending to the API. */
export const itemsPayload = (items) =>
  items.map((i) => ({
    ...(i.id ? { id: i.id } : {}),
    material: i.material ? Number(i.material) : null,
    original_description: i.original_description || '',
    ordered_quantity: i.ordered_quantity,
    uom: i.uom,
    unit_price: i.unit_price === '' ? '0' : i.unit_price,
  }))

/**
 * Editable PO line items with dynamic totals.
 * flags: optional per-row array of {material?:'missing'|'uncertain', quantity?, unit_price?, ...} used for OCR highlighting.
 * Rows with `supplied_quantity` cannot be reduced below it and cannot be removed.
 */
export default function LineItemsEditor({ items, onChange, materials, flags = [], onCreateMaterial }) {
  const update = (idx, patch) => onChange(items.map((it, i) => (i === idx ? { ...it, ...patch } : it)))
  const pickMaterial = (idx, id) => {
    const m = materials.find((x) => String(x.id) === String(id))
    const cur = items[idx]
    update(idx, {
      material: id,
      ...(m ? { uom: m.uom, unit_price: cur.unit_price === '' ? m.default_rate : cur.unit_price, original_description: cur.original_description || m.name } : {}),
    })
  }
  const total = items.reduce((s, i) => s + lineAmount(i.ordered_quantity, i.unit_price), 0)
  const cls = (idx, key) => (flags[idx]?.[key] ? flags[idx][key] : '')

  return (
    <div>
      <div className="table-wrap">
        <table className="table line-items">
          <thead>
            <tr>
              <th>#</th><th style={{ minWidth: 190 }}>Material</th><th style={{ minWidth: 170 }}>Original description</th>
              <th className="num">Ordered qty</th><th>UOM</th><th className="num">Unit price (₹)</th><th className="num">Line amount</th>
              <th className="num">Supplied</th><th className="num">Pending</th><th />
            </tr>
          </thead>
          <tbody>
            {items.map((it, idx) => {
              const supplied = Number(it.supplied_quantity || 0)
              const pending = (Number(it.ordered_quantity) || 0) - supplied
              return (
                <tr key={it.id || `n${idx}`}>
                  <td className="muted">{idx + 1}</td>
                  <td>
                    <Select className={cls(idx, 'material')} value={it.material ?? ''} onChange={(e) => pickMaterial(idx, e.target.value)} disabled={supplied > 0} aria-label="Material">
                      <option value="">Select material…</option>
                      {materials.map((m) => <option key={m.id} value={m.id}>{m.material_code} — {m.name}</option>)}
                    </Select>
                    {onCreateMaterial && !it.material && (
                      <button type="button" className="btn btn-sm btn-ghost" style={{ padding: '2px 0', color: 'var(--primary)' }} onClick={() => onCreateMaterial(idx)}>+ Create new material</button>
                    )}
                  </td>
                  <td><input className="input" value={it.original_description || ''} onChange={(e) => update(idx, { original_description: e.target.value })} placeholder="As written by customer" aria-label="Original description" /></td>
                  <td style={{ width: 110 }}><input className={`input ${cls(idx, 'quantity')}`} type="number" min={supplied || 0} step="0.001" value={it.ordered_quantity} onChange={(e) => update(idx, { ordered_quantity: e.target.value })} aria-label="Ordered quantity" /></td>
                  <td style={{ width: 88 }}>
                    <Select className={cls(idx, 'uom')} value={it.uom} onChange={(e) => update(idx, { uom: e.target.value })} aria-label="UOM">
                      {UOMS.map((u) => <option key={u} value={u}>{uomLabel(u)}</option>)}
                    </Select>
                  </td>
                  <td style={{ width: 120 }}><input className={`input ${cls(idx, 'unit_price')}`} type="number" min="0" step="0.01" value={it.unit_price} onChange={(e) => update(idx, { unit_price: e.target.value })} aria-label="Unit price" /></td>
                  <td className={`num ${cls(idx, 'line_total') ? 'uncertain' : ''}`}>{money(lineAmount(it.ordered_quantity, it.unit_price))}</td>
                  <td className="num">{fmtQty(supplied)}</td>
                  <td className="num">{fmtQty(pending)}</td>
                  <td>
                    <button type="button" className="btn btn-sm btn-icon btn-danger" disabled={supplied > 0 || items.length === 1}
                      title={supplied > 0 ? 'Has supply history — cannot remove' : 'Remove line'} onClick={() => onChange(items.filter((_, i) => i !== idx))} aria-label="Remove line"><Trash2 size={14} /></button>
                  </td>
                </tr>
              )
            })}
          </tbody>
          <tfoot>
            <tr><td colSpan={6} className="right">Order total</td><td className="num">{money(total)}</td><td colSpan={3} /></tr>
          </tfoot>
        </table>
      </div>
      <div style={{ marginTop: 10 }}>
        <button type="button" className="btn btn-sm" onClick={() => onChange([...items, blankItem()])}><Plus size={14} /> Add line item</button>
      </div>
    </div>
  )
}
