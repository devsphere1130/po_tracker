import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Ban, FileText, Pencil, Plus, RotateCcw, Trash2, Truck } from 'lucide-react'
import PageHeader from '../../components/PageHeader'
import { ErrorBanner, Loading } from '../../components/DataTable'
import { PoStatus, Progress } from '../../components/StatusBadge'
import ConfirmDialog from '../../components/ConfirmDialog'
import { TextArea } from '../../components/FormControls'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import { purchaseOrdersApi } from '../../api/purchaseOrders'
import { supplyApi } from '../../api/supply'
import useCached from '../../hooks/useCached'
import { fmtDate, money, qty, uomLabel } from '../../utils/format'
import SupplyEntryForm from '../supply_tracking/SupplyEntryForm'

export default function PurchaseOrderDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { isAdmin } = useAuth()
  const { data: po, error, reload: load, setData: setPo } = useCached(`po:${id}`, () => purchaseOrdersApi.get(id))
  const [modal, setModal] = useState(null)
  const [reason, setReason] = useState('')

  if (error) return <ErrorBanner message={error} onRetry={load} />
  if (!po) return <Loading />

  const cancelled = po.status === 'cancelled'
  const canSupply = !cancelled && po.status !== 'fulfilled'
  const totalSuppliedValue = po.items.reduce((s, i) => s + Number(i.supplied_quantity) * Number(i.unit_price), 0)

  return (
    <>
      <PageHeader
        title={<span className="flex">PO {po.po_number} <PoStatus po={po} /></span>}
        subtitle={<>{po.customer_name} · PO date {fmtDate(po.po_date)} · Delivery {fmtDate(po.delivery_date)} · Source: <span style={{ textTransform: 'capitalize' }}>{po.source}</span></>}
        actions={<>
          <Link className="btn" to="/purchase-orders">Back</Link>
          {canSupply && <button className="btn btn-primary" onClick={() => setModal({ type: 'supply' })}><Truck size={16} /> Record supply</button>}
          {!cancelled && <Link className="btn" to={`/purchase-orders/${po.id}/edit`}><Pencil size={15} /> Edit</Link>}
          {cancelled
            ? <button className="btn" onClick={() => setModal({ type: 'reopen' })}><RotateCcw size={15} /> Reopen</button>
            : po.status !== 'fulfilled' && <button className="btn btn-danger" onClick={() => setModal({ type: 'cancel' })}><Ban size={15} /> Cancel PO</button>}
          {isAdmin && <button className="btn btn-danger" onClick={() => setModal({ type: 'delete' })}><Trash2 size={15} /> Delete</button>}
        </>}
      />
      {cancelled && <div className="alert alert-warn" style={{ marginBottom: 14 }}>This PO was cancelled{po.cancel_reason ? `: ${po.cancel_reason}` : '.'} Supply entries and edits are blocked until it is reopened.</div>}

      <div className="grid grid-4" style={{ marginBottom: 16 }}>
        <div className="card stat stat-accent"><span className="label">Order total</span><span className="value">{money(po.order_total)}</span><span className="sub">{po.items.length} line item(s)</span></div>
        <div className="card stat"><span className="label">Supplied value</span><span className="value">{money(totalSuppliedValue)}</span><span className="sub">At ordered unit prices</span></div>
        <div className="card stat"><span className="label">Progress</span><span className="value">{po.progress_percent}%</span><Progress value={po.progress_percent} /></div>
        <div className="card stat"><span className="label">Delivery</span><span className="value" style={{ fontSize: 18 }}>{fmtDate(po.delivery_date)}</span><span className="sub">{po.is_overdue ? 'Overdue' : 'On schedule'}</span></div>
      </div>

      <div className="stack">
        <div className="card">
          <div className="card-head"><h3>Line items — ordered, supplied and pending</h3></div>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>#</th><th>Material</th><th>Original description</th><th className="num">Ordered</th><th className="num">Supplied</th><th className="num">Pending</th><th>UOM</th><th className="num">Unit price</th><th className="num">Line amount</th><th style={{ minWidth: 130 }}>Progress</th><th /></tr></thead>
              <tbody>
                {po.items.map((i, n) => (
                  <tr key={i.id}>
                    <td className="muted">{n + 1}</td>
                    <td><strong>{i.material_name}</strong><div className="small muted">{i.material_code}</div></td>
                    <td>{i.original_description || '—'}</td>
                    <td className="num">{qty(i.ordered_quantity)}</td>
                    <td className="num">{qty(i.supplied_quantity)}</td>
                    <td className="num"><strong>{qty(i.pending_quantity)}</strong></td>
                    <td>{uomLabel(i.uom)}</td>
                    <td className="num">{money(i.unit_price)}</td>
                    <td className="num">{money(i.line_amount)}</td>
                    <td><Progress value={i.progress_percent} /></td>
                    <td>{canSupply && Number(i.pending_quantity) > 0 && <button className="btn btn-sm" onClick={() => setModal({ type: 'supply', itemId: i.id })}><Plus size={13} /> Supply</button>}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot><tr><td colSpan={8} className="right">Order total</td><td className="num">{money(po.order_total)}</td><td colSpan={2} /></tr></tfoot>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-head"><h3>Supply history</h3><span className="small muted">{po.supply_entries.length} entr{po.supply_entries.length === 1 ? 'y' : 'ies'}</span></div>
          {po.supply_entries.length === 0 ? <div className="empty">No material has been supplied against this PO yet.</div> : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Date</th><th>Material</th><th className="num">Quantity</th><th>Challan no.</th><th>Remarks</th><th /></tr></thead>
              <tbody>
                {po.supply_entries.map((s) => (
                  <tr key={s.id}>
                    <td>{fmtDate(s.supply_date)}</td><td>{s.material_name}</td>
                    <td className="num">{qty(s.quantity)} {uomLabel(s.uom)}</td><td>{s.challan_number || '—'}</td><td>{s.remarks || '—'}</td>
                    <td><div className="actions">
                      {!cancelled && <button className="btn btn-sm btn-icon" title="Edit" onClick={() => setModal({ type: 'supply', entry: s })}><Pencil size={14} /></button>}
                      {!cancelled && isAdmin && <button className="btn btn-sm btn-icon btn-danger" title="Delete" onClick={() => setModal({ type: 'delSupply', entry: s })}><Trash2 size={14} /></button>}
                    </div></td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
        </div>

        <div className="grid grid-2">
          <div className="card card-pad">
            <h3 style={{ marginBottom: 8 }}>Customer</h3>
            <dl className="kv">
              <dt>Name</dt><dd>{po.customer_detail.name}</dd><dt>Code</dt><dd>{po.customer_detail.customer_code}</dd>
              <dt>GST</dt><dd>{po.customer_detail.gst_number || '—'}</dd><dt>Contact</dt><dd>{po.customer_detail.email || po.customer_detail.mobile || '—'}</dd>
              <dt>Shipping</dt><dd style={{ whiteSpace: 'pre-wrap' }}>{po.customer_detail.shipping_address || '—'}</dd>
            </dl>
          </div>
          <div className="card card-pad">
            <h3 style={{ marginBottom: 8 }}>Notes & attachment</h3>
            <p style={{ marginTop: 0, whiteSpace: 'pre-wrap' }}>{po.notes || <span className="muted">No notes.</span>}</p>
            {po.attachment_url
              ? <a className="btn btn-sm" href={po.attachment_url} target="_blank" rel="noreferrer"><FileText size={14} /> {po.attachment_name}</a>
              : <span className="muted small">No original attachment stored.</span>}
          </div>
        </div>
      </div>

      {modal?.type === 'supply' && (
        <SupplyEntryForm po={po} entry={modal.entry} defaultItemId={modal.itemId} onClose={() => setModal(null)} onSaved={() => { setModal(null); load() }} />
      )}
      {modal?.type === 'delSupply' && (
        <ConfirmDialog title="Delete supply entry" onClose={() => setModal(null)}
          message={`Delete the supply of ${qty(modal.entry.quantity)} ${uomLabel(modal.entry.uom)} of ${modal.entry.material_name} on ${fmtDate(modal.entry.supply_date)}? Pending quantity and PO status will be recalculated.`}
          onConfirm={async () => { await supplyApi.remove(modal.entry.id); toast.success('Supply entry deleted.'); load() }} />
      )}
      {modal?.type === 'cancel' && (
        <ConfirmDialog title="Cancel purchase order" confirmLabel="Cancel PO" onClose={() => setModal(null)}
          message="Cancel this PO? No further supply can be recorded until it is reopened. Existing supply history is kept."
          onConfirm={async () => { setPo(await purchaseOrdersApi.cancel(po.id, reason)); toast.success('Purchase order cancelled.') }}>
          <TextArea rows={2} placeholder="Reason (optional)" value={reason} onChange={(e) => setReason(e.target.value)} />
        </ConfirmDialog>
      )}
      {modal?.type === 'reopen' && (
        <ConfirmDialog title="Reopen purchase order" confirmLabel="Reopen" danger={false} onClose={() => setModal(null)}
          message="Reopen this PO? Its status will be recalculated from the supply history."
          onConfirm={async () => { setPo(await purchaseOrdersApi.reopen(po.id)); toast.success('Purchase order reopened.') }} />
      )}
      {modal?.type === 'delete' && (
        <ConfirmDialog title="Delete purchase order" onClose={() => setModal(null)}
          message={`Permanently delete PO ${po.po_number}? This cannot be undone. A PO with supply history cannot be deleted — cancel it instead.`}
          onConfirm={async () => { await purchaseOrdersApi.remove(po.id); toast.success('Purchase order deleted.'); navigate('/purchase-orders') }} />
      )}
    </>
  )
}
