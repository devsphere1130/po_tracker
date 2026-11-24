import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Eye, Pencil, Plus, Trash2 } from 'lucide-react'
import PageHeader from '../../components/PageHeader'
import DataTable, { Pagination } from '../../components/DataTable'
import { Field, Input, OptionSelect, SearchInput, Select } from '../../components/FormControls'
import { PoStatus, Progress } from '../../components/StatusBadge'
import ConfirmDialog from '../../components/ConfirmDialog'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import useList from '../../hooks/useList'
import { useCustomers } from '../../hooks/useOptions'
import { purchaseOrdersApi } from '../../api/purchaseOrders'
import { fmtDate, money } from '../../utils/format'

export default function PurchaseOrders() {
  const toast = useToast()
  const navigate = useNavigate()
  const { isAdmin } = useAuth()
  const [sp] = useSearchParams()
  const [customers] = useCustomers()
  const list = useList(purchaseOrdersApi.list, { ordering: '-po_date', customer: sp.get('customer') || '', status: sp.get('status') || '', overdue: sp.get('overdue') || '' })
  const [del, setDel] = useState(null)

  const columns = [
    { key: 'po_number', header: 'PO number', render: (p) => <Link to={`/purchase-orders/${p.id}`}><strong>{p.po_number}</strong></Link> },
    { key: 'customer_name', header: 'Customer' },
    { key: 'po_date', header: 'PO date', render: (p) => fmtDate(p.po_date) },
    { key: 'delivery_date', header: 'Delivery', render: (p) => fmtDate(p.delivery_date) },
    { key: 'source', header: 'Source', render: (p) => <span style={{ textTransform: 'capitalize' }}>{p.source}</span> },
    { key: 'status', header: 'Status', render: (p) => <PoStatus po={p} /> },
    { key: 'progress', header: 'Supplied', render: (p) => <div style={{ minWidth: 110 }}><Progress value={p.progress_percent} /></div> },
    { key: 'order_total', header: 'Order total', num: true, render: (p) => money(p.order_total) },
    {
      key: 'actions', header: '', render: (p) => (
        <div className="actions">
          <button className="btn btn-sm btn-icon" title="View" onClick={() => navigate(`/purchase-orders/${p.id}`)}><Eye size={15} /></button>
          <button className="btn btn-sm btn-icon" title="Edit" onClick={() => navigate(`/purchase-orders/${p.id}/edit`)}><Pencil size={15} /></button>
          {isAdmin && <button className="btn btn-sm btn-icon btn-danger" title="Delete" onClick={() => setDel(p)}><Trash2 size={15} /></button>}
        </div>
      ),
    },
  ]

  const statusValue = Array.isArray(list.params.status) ? list.params.status[0] : list.params.status

  return (
    <>
      <PageHeader title="Purchase Orders" subtitle="All purchase orders received from customers"
        actions={<Link className="btn btn-primary" to="/purchase-orders/new"><Plus size={16} /> New purchase order</Link>} />
      <div className="card">
        <div className="toolbar">
          <SearchInput value={list.params.search} onChange={(v) => list.setFilter('search', v)} placeholder="Search PO no., customer, material…" />
          <Field label="Customer"><OptionSelect value={list.params.customer} onChange={(v) => list.setFilter('customer', v)} options={customers} /></Field>
          <Field label="Status">
            <Select value={list.params.overdue === 'true' ? 'overdue' : statusValue ?? ''} onChange={(e) => {
              const v = e.target.value
              list.setFilter('overdue', v === 'overdue' ? 'true' : '')
              list.setFilter('status', v === 'overdue' ? '' : v)
            }}>
              <option value="">All</option><option value="pending">Pending</option><option value="partial">Partial</option>
              <option value="fulfilled">Fulfilled</option><option value="cancelled">Cancelled</option><option value="overdue">Overdue</option>
            </Select>
          </Field>
          <Field label="Source">
            <Select value={list.params.source ?? ''} onChange={(e) => list.setFilter('source', e.target.value)}>
              <option value="">All</option><option value="manual">Manual</option><option value="email">Email</option><option value="upload">Upload</option>
            </Select>
          </Field>
          <Field label="PO date from"><Input type="date" value={list.params.po_date_from ?? ''} onChange={(e) => list.setFilter('po_date_from', e.target.value)} /></Field>
          <Field label="PO date to"><Input type="date" value={list.params.po_date_to ?? ''} onChange={(e) => list.setFilter('po_date_to', e.target.value)} /></Field>
          <button className="btn" onClick={list.reset}>Clear</button>
        </div>
        <DataTable columns={columns} rows={list.rows} loading={list.loading} error={list.error} onRetry={list.reload}
          emptyTitle="No purchase orders found" emptyHint="Create a PO manually, or convert one from the Inbox." />
        <Pagination page={list.params.page} pageSize={list.params.page_size} count={list.count} onPage={list.setPage} onPageSize={list.setPageSize} />
      </div>
      {del && (
        <ConfirmDialog title="Delete purchase order" onClose={() => setDel(null)}
          message={`Delete PO ${del.po_number} (${del.customer_name})? This cannot be undone. POs with supply history cannot be deleted — cancel them instead.`}
          onConfirm={async () => { await purchaseOrdersApi.remove(del.id); toast.success('Purchase order deleted.'); list.reload() }} />
      )}
    </>
  )
}
