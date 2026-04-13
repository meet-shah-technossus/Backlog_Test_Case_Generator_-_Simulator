import { createContext, useContext, useState, useCallback, useRef } from 'react'
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react'

const ToastContext = createContext(null)

// ── Individual toast item ──────────────────────────────────────────────────

function ToastItem({ toast, onRemove }) {
  const icon =
    toast.type === 'success' ? <CheckCircle2 size={13} className="text-teal-400  flex-shrink-0 mt-0.5" /> :
    toast.type === 'error'   ? <AlertCircle  size={13} className="text-red-400   flex-shrink-0 mt-0.5" /> :
                               <Info         size={13} className="text-blue-400  flex-shrink-0 mt-0.5" />

  return (
    <div className="flex items-start gap-3 glass px-4 py-3 min-w-[220px] max-w-[320px]
                    shadow-xl shadow-black/40 animate-slide-in pointer-events-auto">
      {icon}
      <span className="text-xs text-white/80 flex-1 leading-relaxed">{toast.message}</span>
      <button
        onClick={() => onRemove(toast.id)}
        className="text-white/30 hover:text-white/60 transition-colors ml-1 mt-0.5"
      >
        <X size={11} />
      </button>
    </div>
  )
}

// ── Provider ───────────────────────────────────────────────────────────────

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const counter = useRef(0)

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  /**
   * addToast(message, type?, duration?)
   *   type:     'info' | 'success' | 'error'   default: 'info'
   *   duration: ms until auto-dismiss           default: 3000 (0 = sticky)
   */
  const addToast = useCallback((message, type = 'info', duration = 3000) => {
    const id = ++counter.current
    setToasts(prev => [...prev, { id, message, type }])
    if (duration > 0) {
      setTimeout(() => removeToast(id), duration)
    }
    return id
  }, [removeToast])

  return (
    <ToastContext.Provider value={addToast}>
      {children}

      {/* Fixed toast container — bottom-right, above everything */}
      <div className="fixed bottom-5 right-5 flex flex-col gap-2 z-50 pointer-events-none">
        {toasts.map(t => (
          <ToastItem key={t.id} toast={t} onRemove={removeToast} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// ── Hook ───────────────────────────────────────────────────────────────────

/**
 * Returns the `addToast(message, type, duration)` function.
 * Must be called inside a component wrapped by <ToastProvider>.
 */
export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}
