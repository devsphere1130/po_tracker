const LABELS = {
  pending: 'Pending', partial: 'Partial', fulfilled: 'Fulfilled', cancelled: 'Cancelled', overdue: 'Overdue',
  new: 'New', scanned: 'Scanned', verified: 'Verified', converted: 'Converted', duplicate: 'Duplicate', rejected: 'Rejected',
  processed: 'Processed', failed: 'Failed', active: 'Active', inactive: 'Inactive', connected: 'Connected',
  disconnected: 'Disconnected', demo: 'Demo',
}

export default function StatusBadge({ status, label }) {
  return <span className={`badge badge-${status}`}>{label || LABELS[status] || status}</span>
}

export function PoStatus({ po }) {
  return (
    <span className="flex" style={{ gap: 4 }}>
      <StatusBadge status={po.status} />
      {po.is_overdue && <StatusBadge status="overdue" />}
    </span>
  )
}

export function Progress({ value }) {
  const v = Math.max(0, Math.min(100, Number(value) || 0))
  return (
    <div className="flex" style={{ gap: 8 }}>
      <div className={`progress grow ${v >= 100 ? 'done' : ''}`}><div style={{ width: `${v}%` }} /></div>
      <span className="small muted mono" style={{ width: 38, textAlign: 'right' }}>{v.toFixed(0)}%</span>
    </div>
  )
}
