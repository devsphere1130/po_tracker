import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Download } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import PageHeader from '../../components/PageHeader'
import { EmptyState, ErrorBanner, Loading } from '../../components/DataTable'
import { Field, Input, OptionSelect, Select } from '../../components/FormControls'
import { PoStatus } from '../../components/StatusBadge'
import { useToast } from '../../components/Toast'
import { useCustomers, useMaterials } from '../../hooks/useOptions'
import { downloadCsv, getPoReport, getReport } from '../../api/reports'
import { errorMessage } from '../../api/client'
import { fmtDate, money, moneyCompact, qty, uomLabel } from '../../utils/format'

const BLUE = '#2563eb'
const AMBER = '#d97706'
const GREEN = '#15803d'
const trunc = (v) => (v.length > 24 ? `${v.slice(0, 23)}…` : v)

function HBar({ data, dataKey, name, fmt, color = BLUE, labelKey }) {
  if (!data.length) return <EmptyState title="No data for the selected filters" />
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e8edf5" horizontal={false} />
          <XAxis type="number" fontSize={12} tickFormatter={fmt} allowDecimals={false} />
          <YAxis type="category" dataKey={labelKey} width={160} fontSize={11} tickFormatter={trunc} />
          <Tooltip formatter={(v) => (fmt ? fmt(v) : v)} />
          <Bar dataKey={dataKey} name={name} fill={color} radius={[0, 3, 3, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function Table({ columns, rows, render }) {
  if (!rows.length) return <EmptyState title="No records for the selected filters" />
  return (
    <div className="table-wrap"><table className="table">
      <thead><tr>{columns.map((c) => <th key={c.key} className={c.num ? 'num' : ''}>{c.label}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}>{columns.map((c) => <td key={c.key} className={c.num ? 'num' : ''}>{render(c, r)}</td>)}</tr>)}</tbody>
    </table></div>
  )
}

const TABS = [['overview', 'Overview'], ['customers', 'Customers'], ['materials', 'Materials'], ['po', 'PO status'], ['monthly', 'Monthly trend']]
const PO_KINDS = [['pending', 'Pending'], ['partial', 'Partial'], ['fulfilled', 'Fulfilled'], ['overdue', 'Overdue'], ['cancelled', 'Cancelled']]

export default function Reports() {
  const toast = useToast()
  const [customers] = useCustomers()
  const [materials] = useMaterials()
  const [filters, setFilters] = useState({ date_from: '', date_to: '', customer: '', material: '', status: '' })
  const [tab, setTab] = useState('overview')
  const [kind, setKind] = useState('pending')
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const params = useMemo(() => Object.fromEntries(Object.entries(filters).filter(([, v]) => v)), [filters])
  // Report endpoint + params for the active tab (the PO-status tab ignores the status filter: the kind is the status)
  const endpoint = tab === 'overview' ? 'summary' : tab === 'po' ? `po-status/${kind}` : tab
  const effective = tab === 'po' ? { ...params, status: undefined } : params

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      setData(tab === 'po' ? await getPoReport(kind, effective) : await getReport(tab === 'overview' ? 'summary' : tab, effective))
    } catch (e) { setError(errorMessage(e)); setData(null) } finally { setLoading(false) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, kind, JSON.stringify(effective)])
  useEffect(() => { load() }, [load])

  const set = (k) => (v) => setFilters((f) => ({ ...f, [k]: v }))
  const exportCsv = async () => {
    try { await downloadCsv(tab === 'overview' ? 'customers' : endpoint, effective) } catch (e) { toast.error(errorMessage(e)) }
  }

  const numeric = (rows, keys) => rows.map((r) => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, keys.includes(k) ? Number(v) : v])))

  const renderCell = (c, r) => {
    const v = r[c.key]
    if (c.key === 'total_value' || c.key === 'order_total' || c.key === 'order_value') return money(v)
    if (['ordered', 'supplied', 'pending'].includes(c.key)) return qty(v)
    if (c.key === 'uom') return uomLabel(v)
    if (c.key === 'po_date' || c.key === 'delivery_date') return fmtDate(v)
    if (c.key === 'status') return <PoStatus po={{ status: v, is_overdue: false }} />
    if (c.key === 'po_number' && r.id) return <Link to={`/purchase-orders/${r.id}`}>{v}</Link>
    if (c.key === 'progress_percent') return `${v}%`
    return v ?? '—'
  }

  const body = () => {
    if (loading && !data) return <Loading />
    if (error) return <ErrorBanner message={error} onRetry={load} />
    if (!data) return null
    if (tab === 'overview') {
      const s = data.by_status
      return (
        <div className="grid grid-4">
          <div className="card stat stat-accent"><span className="label">Total POs</span><span className="value">{data.total_pos}</span><span className="sub">{data.active_customers} customer(s)</span></div>
          <div className="card stat"><span className="label">Total order value</span><span className="value">{money(data.total_value)}</span></div>
          <div className="card stat"><span className="label">Overdue</span><span className="value">{data.overdue}</span></div>
          <div className="card stat"><span className="label">Pending / Partial</span><span className="value">{s.pending} / {s.partial}</span></div>
          <div className="card stat"><span className="label">Fulfilled</span><span className="value">{s.fulfilled}</span></div>
          <div className="card stat"><span className="label">Cancelled</span><span className="value">{s.cancelled}</span></div>
        </div>
      )
    }
    if (tab === 'customers') {
      const rows = numeric(data.rows, ['total_value'])
      return (
        <div className="stack">
          <div className="grid grid-2">
            <div className="card"><div className="card-head"><h3>Top customers by number of POs</h3></div>
              <HBar data={[...rows].sort((a, b) => b.po_count - a.po_count).slice(0, 8)} dataKey="po_count" name="POs" labelKey="customer" /></div>
            <div className="card"><div className="card-head"><h3>Top customers by order value</h3></div>
              <HBar data={[...rows].sort((a, b) => b.total_value - a.total_value).slice(0, 8)} dataKey="total_value" name="Order value" fmt={moneyCompact} color={GREEN} labelKey="customer" /></div>
          </div>
          <div className="card"><div className="card-head"><h3>Customer-wise PO count and value</h3></div><Table columns={data.columns} rows={data.rows} render={renderCell} /></div>
        </div>
      )
    }
    if (tab === 'materials') {
      const rows = numeric(data.rows, ['ordered', 'supplied', 'pending']).map((r) => ({ ...r, label: `${r.material} (${uomLabel(r.uom)})` }))
      return (
        <div className="stack">
          <div className="alert alert-info small">Quantities are grouped by material <em>and</em> unit of measure — different units are never added together. Cancelled POs are excluded unless you filter by Cancelled.</div>
          <div className="grid grid-2">
            <div className="card"><div className="card-head"><h3>Top materials ordered</h3></div>
              <HBar data={[...rows].sort((a, b) => b.ordered - a.ordered).slice(0, 8)} dataKey="ordered" name="Ordered" labelKey="label" /></div>
            <div className="card"><div className="card-head"><h3>Top materials actually supplied</h3></div>
              <HBar data={[...rows].sort((a, b) => b.supplied - a.supplied).filter((r) => r.supplied > 0).slice(0, 8)} dataKey="supplied" name="Supplied" color={GREEN} labelKey="label" /></div>
          </div>
          <div className="card"><div className="card-head"><h3>Material-wise ordered, supplied and pending</h3></div><Table columns={data.columns} rows={data.rows} render={renderCell} /></div>
        </div>
      )
    }
    if (tab === 'po') {
      return (
        <div className="card">
          <div className="card-head"><div className="flex">{PO_KINDS.map(([k, l]) => <button key={k} className={`btn btn-sm ${kind === k ? 'btn-primary' : ''}`} onClick={() => setKind(k)}>{l}</button>)}</div><span className="small muted">{data.rows.length} PO(s)</span></div>
          <Table columns={data.columns} rows={data.rows} render={renderCell} />
        </div>
      )
    }
    const rows = numeric(data.rows, ['total_value'])
    return (
      <div className="stack">
        <div className="card"><div className="card-head"><h3>Monthly PO trend</h3></div>
          {rows.length === 0 ? <EmptyState title="No data for the selected filters" /> : (
            <div className="chart-box"><ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e8edf5" />
                <XAxis dataKey="month" fontSize={12} />
                <YAxis yAxisId="l" allowDecimals={false} fontSize={12} />
                <YAxis yAxisId="r" orientation="right" tickFormatter={moneyCompact} fontSize={12} width={60} />
                <Tooltip formatter={(v, n) => (n === 'Order value' ? money(v) : v)} />
                <Legend />
                <Bar yAxisId="l" dataKey="po_count" name="POs" fill={BLUE} radius={[3, 3, 0, 0]} />
                <Line yAxisId="r" dataKey="total_value" name="Order value" stroke={AMBER} strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer></div>
          )}
        </div>
        <div className="card"><Table columns={data.columns} rows={data.rows} render={renderCell} /></div>
      </div>
    )
  }

  return (
    <>
      <PageHeader title="Reports" subtitle="Live analysis of orders, customers, materials and supply"
        actions={tab !== 'overview' && <button className="btn" onClick={exportCsv}><Download size={15} /> Export CSV</button>} />
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="toolbar" style={{ borderBottom: 0 }}>
          <Field label="PO date from"><Input type="date" value={filters.date_from} onChange={(e) => set('date_from')(e.target.value)} /></Field>
          <Field label="PO date to"><Input type="date" value={filters.date_to} onChange={(e) => set('date_to')(e.target.value)} /></Field>
          <Field label="Customer"><OptionSelect value={filters.customer} onChange={set('customer')} options={customers} /></Field>
          <Field label="Material"><OptionSelect value={filters.material} onChange={set('material')} options={materials} /></Field>
          {tab !== 'po' && (
            <Field label="Status">
              <Select value={filters.status} onChange={(e) => set('status')(e.target.value)}>
                <option value="">All</option><option value="pending">Pending</option><option value="partial">Partial</option><option value="fulfilled">Fulfilled</option><option value="cancelled">Cancelled</option>
              </Select>
            </Field>
          )}
          <button className="btn" onClick={() => setFilters({ date_from: '', date_to: '', customer: '', material: '', status: '' })}>Clear</button>
        </div>
      </div>
      <div className="tabs">{TABS.map(([k, l]) => <button key={k} className={`tab ${tab === k ? 'active' : ''}`} onClick={() => setTab(k)}>{l}</button>)}</div>
      <div style={{ opacity: loading ? 0.6 : 1 }}>{body()}</div>
    </>
  )
}
