import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Eye, Pencil, Plus, Trash2 } from 'lucide-react'
import PageHeader from '../../components/PageHeader'
import DataTable, { Pagination } from '../../components/DataTable'
import { SearchInput, Select, Field } from '../../components/FormControls'
import StatusBadge from '../../components/StatusBadge'
import Modal from '../../components/Modal'
import ConfirmDialog from '../../components/ConfirmDialog'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import useList from '../../hooks/useList'
import { customersApi } from '../../api/customers'
import { fmtDate } from '../../utils/format'
import CustomerForm from './CustomerForm'

function CustomerView({ customer, onClose }) {
  const rows = [
    ['Customer code', customer.customer_code], ['Name', customer.name], ['Contact person', customer.contact_person || '—'],
    ['Email', customer.email || '—'], ['Mobile', customer.mobile || '—'], ['GST number', customer.gst_number || '—'],
    ['Billing address', customer.billing_address || '—'], ['Shipping address', customer.shipping_address || '—'],
    ['Status', <StatusBadge key="s" status={customer.is_active ? 'active' : 'inactive'} />], ['Created', fmtDate(customer.created_at)],
  ]
  return (
    <Modal title={customer.name} onClose={onClose} footer={<>
      <Link className="btn" to={`/purchase-orders?customer=${customer.id}`}>View purchase orders ({customer.po_count})</Link>
      <button className="btn btn-primary" onClick={onClose}>Close</button></>}>
      <dl className="kv">{rows.map(([k, v]) => <div key={k} style={{ display: 'contents' }}><dt>{k}</dt><dd style={{ whiteSpace: 'pre-wrap' }}>{v}</dd></div>)}</dl>
    </Modal>
  )
}

export default function Customers() {
  const toast = useToast()
  const { isAdmin } = useAuth()
  const list = useList(customersApi.list, { ordering: 'name' })
  const [modal, setModal] = useState(null) // {type:'form'|'view'|'delete', customer?}

  const columns = [
    { key: 'customer_code', header: 'Code', render: (c) => <strong>{c.customer_code}</strong> },
    { key: 'name', header: 'Customer' },
    { key: 'contact_person', header: 'Contact', render: (c) => <div>{c.contact_person || '—'}<div className="small muted">{c.mobile}</div></div> },
    { key: 'email', header: 'Email', render: (c) => c.email || '—' },
    { key: 'gst_number', header: 'GST', render: (c) => <span className="mono">{c.gst_number || '—'}</span> },
    { key: 'po_count', header: 'POs', num: true },
    { key: 'is_active', header: 'Status', render: (c) => <StatusBadge status={c.is_active ? 'active' : 'inactive'} /> },
    {
      key: 'actions', header: '', render: (c) => (
        <div className="actions">
          <button className="btn btn-sm btn-icon" title="View" onClick={() => setModal({ type: 'view', customer: c })}><Eye size={15} /></button>
          <button className="btn btn-sm btn-icon" title="Edit" onClick={() => setModal({ type: 'form', customer: c })}><Pencil size={15} /></button>
          {isAdmin && <button className="btn btn-sm btn-icon btn-danger" title="Delete" onClick={() => setModal({ type: 'delete', customer: c })}><Trash2 size={15} /></button>}
        </div>
      ),
    },
  ]

  return (
    <>
      <PageHeader title="Customers" subtitle="Companies that send you purchase orders"
        actions={<button className="btn btn-primary" onClick={() => setModal({ type: 'form' })}><Plus size={16} /> Add customer</button>} />
      <div className="card">
        <div className="toolbar">
          <SearchInput value={list.params.search} onChange={(v) => list.setFilter('search', v)} placeholder="Search code, name, GST, email…" />
          <Field label="Status">
            <Select value={list.params.is_active ?? ''} onChange={(e) => list.setFilter('is_active', e.target.value)}>
              <option value="">All</option><option value="true">Active</option><option value="false">Inactive</option>
            </Select>
          </Field>
          <button className="btn" onClick={list.reset}>Clear</button>
        </div>
        <DataTable columns={columns} rows={list.rows} loading={list.loading} error={list.error} onRetry={list.reload}
          emptyTitle="No customers found" emptyHint="Add a customer or adjust the search and filters." />
        <Pagination page={list.params.page} pageSize={list.params.page_size} count={list.count} onPage={list.setPage} onPageSize={list.setPageSize} />
      </div>

      {modal?.type === 'form' && <CustomerForm initial={modal.customer} onClose={() => setModal(null)} onSaved={() => { setModal(null); list.reload() }} />}
      {modal?.type === 'view' && <CustomerView customer={modal.customer} onClose={() => setModal(null)} />}
      {modal?.type === 'delete' && (
        <ConfirmDialog title="Delete customer" onClose={() => setModal(null)}
          message={`Delete "${modal.customer.name}"? Customers linked to purchase orders cannot be deleted — deactivate them instead.`}
          onConfirm={async () => { await customersApi.remove(modal.customer.id); toast.success('Customer deleted.'); list.reload() }} />
      )}
    </>
  )
}
