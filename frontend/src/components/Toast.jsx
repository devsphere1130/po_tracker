import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const dismiss = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), [])
  const push = useCallback(
    (type, message) => {
      const id = Math.random().toString(36).slice(2)
      setToasts((t) => [...t, { id, type, message }])
      setTimeout(() => dismiss(id), type === 'error' ? 7000 : 3500)
    },
    [dismiss],
  )
  const api = useMemo(
    () => ({
      success: (m) => push('success', m),
      error: (m) => push('error', m),
      info: (m) => push('info', m),
    }),
    [push],
  )

  const Icon = { success: CheckCircle2, error: AlertCircle, info: Info }
  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => {
          const I = Icon[t.type]
          return (
            <div key={t.id} className={`toast ${t.type}`}>
              <I size={18} />
              <div className="grow">{t.message}</div>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => dismiss(t.id)} aria-label="Dismiss"><X size={14} /></button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)
