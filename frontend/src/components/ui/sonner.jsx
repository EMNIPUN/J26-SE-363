import { Toaster as Sonner } from 'sonner'
import { useTheme } from '@/shared/theme/useTheme.js'

export function Toaster({ ...props }) {
  const { resolvedTheme = 'light' } = useTheme()

  return (
    <Sonner
      theme={resolvedTheme}
      position="top-right"
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            'group toast group-[.toaster]:bg-card group-[.toaster]:text-card-foreground group-[.toaster]:border-border group-[.toaster]:shadow-2xl group-[.toaster]:rounded-xl font-sans text-xs border p-3.5 gap-3 backdrop-blur-sm transition-all duration-200',
          description: 'group-[.toast]:text-muted-foreground text-[11px] leading-relaxed',
          actionButton:
            'group-[.toast]:bg-primary group-[.toast]:text-primary-foreground group-[.toast]:rounded-lg group-[.toast]:font-semibold text-xs px-3 py-1.5 active:scale-95 transition-all shadow-xs cursor-pointer',
          cancelButton:
            'group-[.toast]:bg-muted group-[.toast]:text-muted-foreground group-[.toast]:rounded-lg text-xs px-2.5 py-1.5 cursor-pointer',
          closeButton:
            'group-[.toast]:bg-card group-[.toast]:text-muted-foreground hover:group-[.toast]:text-foreground group-[.toast]:border-border cursor-pointer transition-colors',
        },
      }}
      {...props}
    />
  )
}
