const ROWS = [
  ['View dashboard, reports, all records', true, true],
  ['Create / edit customers, materials, purchase orders', true, true],
  ['Record and edit supply entries', true, true],
  ['Scan, verify OCR data and convert emails to POs', true, true],
  ['Cancel / reopen purchase orders', true, true],
  ['Delete customers, materials, purchase orders, supply entries', true, false],
  ['Edit company profile and inbox configuration', true, false],
  ['Manage users and roles', true, false],
]

export default function RolePermissions() {
  return (
    <div className="card" style={{ maxWidth: 760 }}>
      <div className="card-head"><h3>Role permissions</h3></div>
      <table className="table">
        <thead><tr><th>Capability</th><th>Admin</th><th>Staff</th></tr></thead>
        <tbody>{ROWS.map(([label, a, s]) => <tr key={label}><td>{label}</td><td>{a ? '✔' : '—'}</td><td>{s ? '✔' : '—'}</td></tr>)}</tbody>
      </table>
      <div className="card-pad small muted">Permissions are enforced by the API on every request, not just hidden in the interface.</div>
    </div>
  )
}
