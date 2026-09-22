import { toast } from 'sonner'
import { CheckCircle2, AlertCircle, Info, AlertTriangle, Sparkles } from 'lucide-react'

/**
 * Global Professional Notification Toast Utility
 * Designed specifically for high-contrast Light (white) and Dark (black/charcoal) themes.
 */
export const showToast = {
  success: (message, options = {}) => {
    return toast.success(message, {
      icon: <CheckCircle2 className="h-4 w-4 text-emerald-500 dark:text-emerald-400 shrink-0" />,
      ...options,
    })
  },

  error: (message, options = {}) => {
    return toast.error(message, {
      icon: <AlertCircle className="h-4 w-4 text-destructive shrink-0" />,
      ...options,
    })
  },

  info: (message, options = {}) => {
    return toast.info(message, {
      icon: <Info className="h-4 w-4 text-primary shrink-0" />,
      ...options,
    })
  },

  warning: (message, options = {}) => {
    return toast.warning(message, {
      icon: <AlertTriangle className="h-4 w-4 text-amber-500 dark:text-amber-400 shrink-0" />,
      ...options,
    })
  },

  ai: (message, options = {}) => {
    return toast(message, {
      icon: <Sparkles className="h-4 w-4 text-amber-400 dark:text-amber-300 shrink-0" />,
      ...options,
    })
  },

  promise: (promise, options = {}) => {
    return toast.promise(promise, options)
  },

  dismiss: (id) => toast.dismiss(id),
}

export { toast }
