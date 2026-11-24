import { ChevronLeft, ChevronRight, Inbox } from 'lucide-react'

export function Loading({ text = 'Loading…' }) {
  return <div className="loading"><span className="spinner" /> <span style={{ marginLeft: 8 }}>{text}</span></div>
}

export function EmptyState({ title = 'No records found', hint, icon: Icon = Inbox }) {
  return (
    <div className="empty">
      <Icon size={30} />
      <div style={{ fontWeight: 600 }}>{title}</div>
      {hint && <div className="small">{hint}</div>}
    </div>
  )
}

export function ErrorBanner({ message, onRetry }) {
  if (!message) return null
  return (
    <div className="alert alert-error flex-between" role="alert">
      <span>{message}</span>
      {onRetry && <button className="btn btn-sm" onClick={onRetry}>Retry</button>}
    </div>
  )
}

/** columns: [{ key, header, render?(row), className?, num? }] */
export default function DataTable({ columns, rows, loading, error, onRetry, emptyTitle, emptyHint, onRowClick, rowKey = 'id' }) {
  if (error) return <div style={{ padding: 16 }}><ErrorBanner message={error} onRetry={onRetry} /></div>
  if (loading && !rows?.length) return <Loading />
  if (!rows?.length) return <EmptyState title={emptyTitle} hint={emptyHint} />
  return (
    <div className="table-wrap" style={{ opacity: loading ? 0.6 : 1 }}>
      <table className="table">
        <thead>
          <tr>{columns.map((c) => <th key={c.key} className={c.num ? 'num' : ''}>{c.header}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row[rowKey]} className={onRowClick ? 'clickable' : ''} onClick={onRowClick ? () => onRowClick(row) : undefined}>
              {columns.map((c) => (
                <td key={c.key} className={`${c.num ? 'num' : ''} ${c.className || ''}`}>
                  {c.render ? c.render(row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Pagination({ page, pageSize, count, onPage, onPageSize }) {
  const pages = Math.max(1, Math.ceil(count / pageSize))
  const from = count === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(count, page * pageSize)
  return (
    <div className="pager">
      <span>{from}–{to} of {count}</span>
      <div className="btns">
        {onPageSize && (
          <select className="input" style={{ width: 'auto' }} value={pageSize} onChange={(e) => onPageSize(Number(e.target.value))} aria-label="Rows per page">
            {[10, 25, 50].map((n) => <option key={n} value={n}>{n} / page</option>)}
          </select>
        )}
        <button className="btn btn-sm btn-icon" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Previous page"><ChevronLeft size={16} /></button>
        <span>Page {page} / {pages}</span>
        <button className="btn btn-sm btn-icon" disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label="Next page"><ChevronRight size={16} /></button>
      </div>
    </div>
  )
}
