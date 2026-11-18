import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Pencil, Trash2, Truck } from 'lucide-react'
import PageHeader from '../../components/PageHeader'
import DataTable, { Pagination } from '../../components/DataTable'
import { Field, Input, OptionSelect, SearchInput } from '../../components/FormControls'
import { PoStatus, Progress } from '../../components/StatusBadge'
import ConfirmDialog from '../../components/ConfirmDialog'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import useList from '../../hooks/useList'
import { useCustomers, useMaterials } from '../../hooks/useOptions'
import { purchaseOrdersApi } from '../../api/purchaseOrders'
import { supplyApi } from '../../api/supply'
import { errorMessage } from '../../api/client'
import { fmtDate, money, qty, uomLabel } from '../../utils/format'
import SupplyEntryForm from './SupplyEntryForm'

function OpenOrders({ onRecord }) {
  const [customers] = useCustomers()
  const list = useList(purchaseOrdersApi.list, { status: ['pending', 'partial'], ordering: 'delivery_date' })
  const columns = [
    { key: 'po_number', header: 'PO number', render: (p) => <Link to={`/purchase-orders/${p.id}`}><strong>{p.po_number}</strong></Link> },
    { key: 'customer_name', header: 'Customer' },
    { key: 'delivery_date', header: 'Delivery', render: (p) => fmtDate(p.delivery_date) },
    { key: 'status', header: 'Status', render: (p) => <PoStatus po={p} /> },
    { key: 'progress', header: 'Supplied (by quantity)', render: (p) => <div style={{ minWidth: 140 }}><Progress value={p.progress_percent} /></div> },
    { key: 'order_total', header: 'Order total', num: true, render: (p) => money(p.order_total) },
    { key: 'a', header: '', render: (p) => <button className="btn btn-sm btn-primary" onClick={() => onRecord(p.id)}><Truck size={14} /> Record supply</button> },
  ]
  return (
    <div className="card">
      <div className="toolbar">
        <SearchInput value={list.params.search} onChange={(v) => list.setFilter('search', v)} placeholder="Search PO or customer…" />
        <Field label="Customer"><OptionSelect value={list.params.customer} onChange={(v) => list.setFilter('customer', v)} options={customers} /></Field>
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.loading} error={list.error} onRetry={list.reload}
        emptyTitle="No open purchase orders" emptyHint="Everything received has been fully supplied (or cancelled)." />
      <Pagination page={list.params.page} pageSize={list.params.page_size} count={list.count} onPage={list.setPage} onPageSize={list.setPageSize} />
    </div>
  )
}

function History({ onEdit, refreshKey }) {
  const toast = useToast()
  const { isAdmin } = useAuth()
  const [customers] = useCustomers()
  const [materials] = useMaterials()
  const list = useList(supplyApi.list, { ordering: '-supply_date' })
  const [del, setDel] = useState(null)
  const columns = [
    { key: 'supply_date', header: 'Date', render: (s) => fmtDate(s.supply_date) },
    { key: 'po_number', header: 'PO', render: (s) => <Link to={`/purchase-orders/${s.po}`}>{s.po_number}</Link> },
    { key: 'customer_name', header: 'Customer' },
    { key: 'material_name', header: 'Material' },
    { key: 'quantity', header: 'Quantity', num: true, render: (s) => `${qty(s.quantity)} ${uomLabel(s.uom)}` },
    { key: 'challan_number', header: 'Challan', render: (s) => s.challan_number || '—' },
    { key: 'remarks', header: 'Remarks', render: (s) => s.remarks || '—' },
    {
      key: 'a', header: '', render: (s) => (
        <div className="actions">
          {s.po_status !== 'cancelled' && <button className="btn btn-sm btn-icon" title="Edit" onClick={() => onEdit(s)}><Pencil size={14} /></button>}
          {s.po_status !== 'cancelled' && isAdmin && <button className="btn btn-sm btn-icon btn-danger" title="Delete" onClick={() => setDel(s)}><Trash2 size={14} /></button>}
        </div>
      ),
    },
  ]
  // refreshKey forces a reload after a change made elsewhere on the page
  const key = refreshKey
  return (
    <div className="card" key={key}>
      <div className="toolbar">
        <SearchInput value={list.params.search} onChange={(v) => list.setFilter('search', v)} placeholder="Search PO, challan, material…" />
        <Field label="Customer"><OptionSelect value={list.params.customer} onChange={(v) => list.setFilter('customer', v)} options={customers} /></Field>
        <Field label="Material"><OptionSelect value={list.params.material} onChange={(v) => list.setFilter('material', v)} options={materials} /></Field>
        <Field label="From"><Input type="date" value={list.params.date_from ?? ''} onChange={(e) => list.setFilter('date_from', e.target.value)} /></Field>
        <Field label="To"><Input type="date" value={list.params.date_to ?? ''} onChange={(e) => list.setFilter('date_to', e.target.value)} /></Field>
        <button className="btn" onClick={list.reset}>Clear</button>
      </div>
      <DataTable columns={columns} rows={list.rows} loading={list.loading} error={list.error} onRetry={list.reload}
        emptyTitle="No supply entries" emptyHint="Record supply against a purchase order to see it here." />
      <Pagination page={list.params.page} pageSize={list.params.page_size} count={list.count} onPage={list.setPage} onPageSize={list.setPageSize} />
      {del && (
        <ConfirmDialog title="Delete supply entry" onClose={() => setDel(null)}
          message={`Delete the supply of ${qty(del.quantity)} ${uomLabel(del.uom)} of ${del.material_name} on PO ${del.po_number}? Pending quantity and PO status will be recalculated.`}
          onConfirm={async () => { await supplyApi.remove(del.id); toast.success('Supply entry deleted.'); list.reload() }} />
      )}
    </div>
  )
}

export default function SupplyTracking() {
  const toast = useToast()
  const [tab, setTab] = useState('open')
  const [form, setForm] = useState(null) // {po, entry?}
  const [version, setVersion] = useState(0)

  const openForm = async (poId, entry) => {
    try { setForm({ po: await purchaseOrdersApi.get(poId), entry }) } catch (e) { toast.error(errorMessage(e)) }
  }

  return (
    <>
      <PageHeader title="Supply Tracking" subtitle="Record material supplied against purchase orders. Pending quantities and PO status are derived from these entries." />
      <div className="tabs">
        <button className={`tab ${tab === 'open' ? 'active' : ''}`} onClick={() => setTab('open')}>Open purchase orders</button>
        <button className={`tab ${tab === 'history' ? 'active' : ''}`} onClick={() => setTab('history')}>Supply history</button>
      </div>
      {tab === 'open' ? <OpenOrders key={`o${version}`} onRecord={(id) => openForm(id)} /> : <History key={`h${version}`} onEdit={(s) => openForm(s.po, s)} refreshKey={version} />}
      {form && <SupplyEntryForm po={form.po} entry={form.entry} onClose={() => setForm(null)} onSaved={() => { setForm(null); setVersion((v) => v + 1) }} />}
    </>
  )
}
