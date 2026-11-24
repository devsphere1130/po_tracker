import { useState } from 'react'
import { Eye, Link2, Pencil, Plus, Trash2 } from 'lucide-react'
import PageHeader from '../../components/PageHeader'
import DataTable, { Pagination } from '../../components/DataTable'
import { SearchInput, Select, Field } from '../../components/FormControls'
import StatusBadge from '../../components/StatusBadge'
import Modal from '../../components/Modal'
import ConfirmDialog from '../../components/ConfirmDialog'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import useList from '../../hooks/useList'
import { materialsApi } from '../../api/materials'
import { money, UOMS, uomLabel } from '../../utils/format'
import MaterialForm from './MaterialForm'
import MaterialAliases from './MaterialAliases'

function MaterialView({ material, onClose }) {
  const rows = [
    ['Material code', material.material_code], ['Name', material.name], ['Category', material.category || '—'],
    ['Unit', material.uom_display], ['Default rate', money(material.default_rate)], ['Description', material.description || '—'],
    ['Used in PO lines', material.usage_count], ['Status', <StatusBadge key="s" status={material.is_active ? 'active' : 'inactive'} />],
  ]
  return (
    <Modal title={material.name} onClose={onClose} footer={<button className="btn btn-primary" onClick={onClose}>Close</button>}>
      <dl className="kv">{rows.map(([k, v]) => <div key={k} style={{ display: 'contents' }}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
    </Modal>
  )
}

export default function Materials() {
  const toast = useToast()
  const { isAdmin } = useAuth()
  const list = useList(materialsApi.list, { ordering: 'name' })
  const [modal, setModal] = useState(null)

  const columns = [
    { key: 'material_code', header: 'Code', render: (m) => <strong>{m.material_code}</strong> },
    { key: 'name', header: 'Material' },
    { key: 'category', header: 'Category', render: (m) => m.category || '—' },
    { key: 'uom', header: 'Unit', render: (m) => uomLabel(m.uom) },
    { key: 'default_rate', header: 'Default rate', num: true, render: (m) => money(m.default_rate) },
    { key: 'usage_count', header: 'PO lines', num: true },
    { key: 'is_active', header: 'Status', render: (m) => <StatusBadge status={m.is_active ? 'active' : 'inactive'} /> },
    {
      key: 'actions', header: '', render: (m) => (
        <div className="actions">
          <button className="btn btn-sm btn-icon" title="View" onClick={() => setModal({ type: 'view', material: m })}><Eye size={15} /></button>
          <button className="btn btn-sm btn-icon" title="Customer description mapping" onClick={() => setModal({ type: 'aliases', material: m })}><Link2 size={15} /></button>
          <button className="btn btn-sm btn-icon" title="Edit" onClick={() => setModal({ type: 'form', material: m })}><Pencil size={15} /></button>
          {isAdmin && <button className="btn btn-sm btn-icon btn-danger" title="Delete" onClick={() => setModal({ type: 'delete', material: m })}><Trash2 size={15} /></button>}
        </div>
      ),
    },
  ]

  return (
    <>
      <PageHeader title="Materials" subtitle="Master list of materials you supply"
        actions={<button className="btn btn-primary" onClick={() => setModal({ type: 'form' })}><Plus size={16} /> Add material</button>} />
      <div className="card">
        <div className="toolbar">
          <SearchInput value={list.params.search} onChange={(v) => list.setFilter('search', v)} placeholder="Search code, name, category…" />
          <Field label="Unit">
            <Select value={list.params.uom ?? ''} onChange={(e) => list.setFilter('uom', e.target.value)}>
              <option value="">All</option>{UOMS.map((u) => <option key={u} value={u}>{uomLabel(u)}</option>)}
            </Select>
          </Field>
          <Field label="Status">
            <Select value={list.params.is_active ?? ''} onChange={(e) => list.setFilter('is_active', e.target.value)}>
              <option value="">All</option><option value="true">Active</option><option value="false">Inactive</option>
            </Select>
          </Field>
          <button className="btn" onClick={list.reset}>Clear</button>
        </div>
        <DataTable columns={columns} rows={list.rows} loading={list.loading} error={list.error} onRetry={list.reload}
          emptyTitle="No materials found" emptyHint="Add a material or adjust the search and filters." />
        <Pagination page={list.params.page} pageSize={list.params.page_size} count={list.count} onPage={list.setPage} onPageSize={list.setPageSize} />
      </div>

      {modal?.type === 'form' && <MaterialForm initial={modal.material} onClose={() => setModal(null)} onSaved={() => { setModal(null); list.reload() }} />}
      {modal?.type === 'view' && <MaterialView material={modal.material} onClose={() => setModal(null)} />}
      {modal?.type === 'aliases' && <MaterialAliases material={modal.material} onClose={() => setModal(null)} />}
      {modal?.type === 'delete' && (
        <ConfirmDialog title="Delete material" onClose={() => setModal(null)}
          message={`Delete "${modal.material.name}"? Materials used in purchase orders cannot be deleted — deactivate them instead.`}
          onConfirm={async () => { await materialsApi.remove(modal.material.id); toast.success('Material deleted.'); list.reload() }} />
      )}
    </>
  )
}
