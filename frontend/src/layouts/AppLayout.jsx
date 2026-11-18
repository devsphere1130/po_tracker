import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { BarChart3, ClipboardList, FileScan, Inbox, LayoutDashboard, LogOut, Menu, Package, Settings, Truck, Users } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/inbox', label: 'Inbox', icon: Inbox },
  { to: '/ocr', label: 'OCR Documents', icon: FileScan },
  { to: '/purchase-orders', label: 'Purchase Orders', icon: ClipboardList },
  { to: '/supply', label: 'Supply Tracking', icon: Truck },
  { to: '/customers', label: 'Customers', icon: Users },
  { to: '/materials', label: 'Materials', icon: Package },
  { to: '/reports', label: 'Reports', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function AppLayout() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  return (
    <div className="app">
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="brand"><span className="brand-mark"><ClipboardList size={18} /></span> PO Tracker</div>
        <nav className="nav">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)} className={({ isActive }) => (isActive ? 'active' : '')}>
              <Icon size={17} /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot muted">Supplier PO management<br />Currency: INR (₹)</div>
      </aside>
      <div className={`scrim ${open ? 'open' : ''}`} onClick={() => setOpen(false)} />
      <div className="main">
        <header className="topbar">
          <button className="btn btn-icon menu-btn" onClick={() => setOpen(true)} aria-label="Open menu"><Menu size={18} /></button>
          <div className="grow" />
          <div className="flex">
            <div style={{ textAlign: 'right', lineHeight: 1.25 }}>
              <div style={{ fontWeight: 600 }}>{user.full_name}</div>
              <div className="small muted" style={{ textTransform: 'capitalize' }}>{user.role}</div>
            </div>
            <button className="btn btn-sm" onClick={async () => { await logout(); navigate('/login') }}><LogOut size={14} /> Logout</button>
          </div>
        </header>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  )
}
