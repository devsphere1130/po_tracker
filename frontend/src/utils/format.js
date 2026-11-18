const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 })
const inrCompact = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', notation: 'compact', maximumFractionDigits: 1 })

export const money = (v) => (v === null || v === undefined || v === '' ? '—' : inr.format(Number(v)))
export const moneyCompact = (v) => inrCompact.format(Number(v || 0))
export const qty = (v) => (v === null || v === undefined || v === '' ? '—' : Number(v).toLocaleString('en-IN', { maximumFractionDigits: 3 }))

export function fmtDate(v) {
  if (!v) return '—'
  const d = new Date(v.length === 10 ? `${v}T00:00:00` : v)
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function fmtDateTime(v) {
  if (!v) return '—'
  return new Date(v).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export const todayIso = () => {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

export const lineAmount = (q, p) => Math.round((Number(q) || 0) * (Number(p) || 0) * 100) / 100

export const UOMS = ['NOS', 'PCS', 'KG', 'MTR', 'LTR', 'BOX', 'SET', 'TON', 'ROLL', 'BAG']
export const uomLabel = (u) => (u ? u.charAt(0) + u.slice(1).toLowerCase() : '')
