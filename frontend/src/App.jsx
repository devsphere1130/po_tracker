import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { Loading } from './components/DataTable'
import AppLayout from './layouts/AppLayout'
import Login from './modules/auth/Login'
import Dashboard from './modules/dashboard/Dashboard'
import Customers from './modules/customers/Customers'
import Materials from './modules/materials/Materials'
import Inbox from './modules/inbox/Inbox'
import OCRUploads from './modules/ocr/OCRUploads'
import OCRVerification from './modules/ocr/OCRVerification'
import PurchaseOrders from './modules/purchase_orders/PurchaseOrders'
import PurchaseOrderForm from './modules/purchase_orders/PurchaseOrderForm'
import PurchaseOrderDetails from './modules/purchase_orders/PurchaseOrderDetails'
import SupplyTracking from './modules/supply_tracking/SupplyTracking'
import Reports from './modules/reports/Reports'
import Settings from './modules/settings/Settings'

function Protected({ children }) {
  const { user, ready } = useAuth()
  if (!ready) return <Loading text="Starting…" />
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  const { user, ready } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={ready && user ? <Navigate to="/" replace /> : <Login />} />
      <Route element={<Protected><AppLayout /></Protected>}>
        <Route index element={<Dashboard />} />
        <Route path="customers" element={<Customers />} />
        <Route path="materials" element={<Materials />} />
        <Route path="inbox" element={<Inbox />} />
        <Route path="ocr" element={<OCRUploads />} />
        <Route path="ocr/:id" element={<OCRVerification />} />
        <Route path="purchase-orders" element={<PurchaseOrders />} />
        <Route path="purchase-orders/new" element={<PurchaseOrderForm />} />
        <Route path="purchase-orders/:id" element={<PurchaseOrderDetails />} />
        <Route path="purchase-orders/:id/edit" element={<PurchaseOrderForm />} />
        <Route path="supply" element={<SupplyTracking />} />
        <Route path="reports" element={<Reports />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<div className="empty">Page not found.</div>} />
      </Route>
    </Routes>
  )
}
