import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import PageHeader from '../../components/PageHeader'
import { ErrorBanner, Loading } from '../../components/DataTable'
import { PoStatus } from '../../components/StatusBadge'
import { getDashboard } from '../../api/dashboard'
import { errorMessage } from '../../api/client'
import { fmtDate, money, moneyCompact, qty, uomLabel } from '../../utils/format'

const BLUE = '#2563eb'
const AMBER = '#d97706'

function Stat({ label, value, sub, to, accent }) {
  const navigate = useNavigate()
  return (
    <div className={`card stat ${to ? 'link' : ''} ${accent ? 'stat-accent' : ''}`} onClick={to ? () => navigate(to) : undefined} role={to ? 'link' : undefined}>
      <span className="label">{label}</span>
      <span className="value">{value}</span>
      {sub && <span className="sub">{sub}</span>}
    </div>
  )
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const load = () => getDashboard().then(setData).catch((e) => setError(errorMessage(e)))
  useEffect(() => { load() }, [])

  if (error) return <ErrorBanner message={error} onRetry={load} />
  if (!data) return <Loading />

  const trend = data.monthly_trend.map((m) => ({ ...m, total_value: Number(m.total_value) }))
  const customers = data.customer_summary.map((c) => ({ ...c, total_value: Number(c.total_value) }))

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Live overview calculated from your purchase order and supply records" />
      <div className="grid grid-4" style={{ marginBottom: 16 }}>
        <Stat label="Total received POs" value={data.total_pos} to="/purchase-orders" accent />
        <Stat label="Pending POs" value={data.pending} sub="Nothing supplied yet" to="/purchase-orders?status=pending" />
        <Stat label="Partially supplied" value={data.partial} sub="Balance remaining" to="/purchase-orders?status=partial" />
        <Stat label="Fulfilled POs" value={data.fulfilled} to="/purchase-orders?status=fulfilled" />
        <Stat label="Cancelled POs" value={data.cancelled} to="/purchase-orders?status=cancelled" />
        <Stat label="Overdue POs" value={data.overdue} sub="Past delivery date, not fulfilled" to="/purchase-orders?overdue=true" />
        <Stat label="Active PO value" value={money(data.active_value)} sub="Pending + partial orders" />
        <Stat label="Pending value" value={money(data.pending_value)} sub="Unsupplied quantity × unit price" />
      </div>

      <div className="grid grid-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="card-head"><h3>Monthly order trend</h3></div>
          <div className="chart-box">
            {trend.length === 0 ? <div className="empty">No orders yet.</div> : (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e8edf5" />
                  <XAxis dataKey="month" fontSize={12} />
                  <YAxis yAxisId="l" allowDecimals={false} fontSize={12} />
                  <YAxis yAxisId="r" orientation="right" tickFormatter={moneyCompact} fontSize={12} width={60} />
                  <Tooltip formatter={(v, n) => (n === 'Order value' ? money(v) : v)} />
                  <Legend />
                  <Bar yAxisId="l" dataKey="po_count" name="POs received" fill={BLUE} radius={[3, 3, 0, 0]} />
                  <Line yAxisId="r" dataKey="total_value" name="Order value" stroke={AMBER} strokeWidth={2} dot={{ r: 3 }} />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
        <div className="card">
          <div className="card-head"><h3>Customer-wise order value</h3><span className="small muted">Excludes cancelled</span></div>
          <div className="chart-box">
            {customers.length === 0 ? <div className="empty">No orders yet.</div> : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={customers} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e8edf5" horizontal={false} />
                  <XAxis type="number" tickFormatter={moneyCompact} fontSize={12} />
                  <YAxis type="category" dataKey="customer" width={150} fontSize={11} tickFormatter={(v) => (v.length > 22 ? `${v.slice(0, 21)}…` : v)} />
                  <Tooltip formatter={(v) => money(v)} />
                  <Bar dataKey="total_value" name="Order value" fill={BLUE} radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-head"><h3>Customer-wise order summary</h3></div>
        <div className="table-wrap"><table className="table">
          <thead><tr><th>Customer</th><th className="num">POs</th><th className="num">Open POs</th><th className="num">Order value</th></tr></thead>
          <tbody>
            {customers.length === 0 ? <tr><td colSpan={4} className="muted">No data.</td></tr> : customers.map((c) => (
              <tr key={c.customer_id}><td><Link to={`/purchase-orders?customer=${c.customer_id}`}>{c.customer}</Link></td><td className="num">{c.po_count}</td><td className="num">{c.open_count}</td><td className="num">{money(c.total_value)}</td></tr>
            ))}
          </tbody>
        </table></div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-head"><h3>Recent purchase orders</h3><Link to="/purchase-orders" className="small">View all</Link></div>
          <div className="table-wrap"><table className="table">
            <thead><tr><th>PO</th><th>Customer</th><th>Status</th><th className="num">Total</th></tr></thead>
            <tbody>
              {data.recent_pos.length === 0 ? <tr><td colSpan={4} className="muted">No purchase orders yet.</td></tr> : data.recent_pos.map((p) => (
                <tr key={p.id}><td><Link to={`/purchase-orders/${p.id}`}><strong>{p.po_number}</strong></Link><div className="small muted">{fmtDate(p.po_date)}</div></td><td>{p.customer_name}</td><td><PoStatus po={p} /></td><td className="num">{money(p.order_total)}</td></tr>
              ))}
            </tbody>
          </table></div>
        </div>
        <div className="card">
          <div className="card-head"><h3>Recent supplies</h3><Link to="/supply" className="small">Supply tracking</Link></div>
          <div className="table-wrap"><table className="table">
            <thead><tr><th>Date</th><th>PO</th><th>Material</th><th className="num">Qty</th></tr></thead>
            <tbody>
              {data.recent_supplies.length === 0 ? <tr><td colSpan={4} className="muted">No supplies recorded yet.</td></tr> : data.recent_supplies.map((s) => (
                <tr key={s.id}><td>{fmtDate(s.supply_date)}</td><td><Link to={`/purchase-orders/${s.po}`}>{s.po_number}</Link><div className="small muted">{s.customer_name}</div></td><td>{s.material_name}</td><td className="num">{qty(s.quantity)} {uomLabel(s.uom)}</td></tr>
              ))}
            </tbody>
          </table></div>
        </div>
      </div>
    </>
  )
}
