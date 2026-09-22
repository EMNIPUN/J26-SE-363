import { useState, useCallback, useRef } from 'react'
import { ModalContext } from './modalContextDef.js'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
} from '@/components/ui/alert-dialog'
import { AlertCircle, HelpCircle } from 'lucide-react'

export function ModalProvider({ children }) {
  const [modalState, setModalState] = useState({
    isOpen: false,
    title: '',
    description: '',
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    tone: 'default', // 'default' | 'destructive' | 'warning'
  })

  const resolverRef = useRef(null)

  const confirm = useCallback(
    ({
      title = 'Are you sure?',
      description = 'Please confirm this action to proceed.',
      confirmText = 'Confirm',
      cancelText = 'Cancel',
      tone = 'default',
    } = {}) => {
      return new Promise((resolve) => {
        resolverRef.current = resolve
        setModalState({
          isOpen: true,
          title,
          description,
          confirmText,
          cancelText,
          tone,
        })
      })
    },
    [],
  )

  const handleAction = (result) => {
    setModalState((prev) => ({ ...prev, isOpen: false }))
    if (resolverRef.current) {
      resolverRef.current(result)
      resolverRef.current = null
    }
  }

  return (
    <ModalContext.Provider value={{ confirm }}>
      {children}

      <AlertDialog
        open={modalState.isOpen}
        onOpenChange={(open) => {
          if (!open) handleAction(false)
        }}
      >
        <AlertDialogContent className="sm:max-w-[420px]">
          <AlertDialogHeader>
            <div className="flex items-start gap-3">
              <div
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border shadow-xs ${
                  modalState.tone === 'destructive'
                    ? 'bg-destructive/10 text-destructive border-destructive/20'
                    : 'bg-primary/10 text-primary border-primary/20'
                }`}
              >
                {modalState.tone === 'destructive' ? (
                  <AlertCircle className="h-5 w-5" />
                ) : (
                  <HelpCircle className="h-5 w-5" />
                )}
              </div>
              <div className="flex-1 space-y-1">
                <AlertDialogTitle>{modalState.title}</AlertDialogTitle>
                <AlertDialogDescription>{modalState.description}</AlertDialogDescription>
              </div>
            </div>
          </AlertDialogHeader>

          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => handleAction(false)}>
              {modalState.cancelText}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleAction(true)}
              className={
                modalState.tone === 'destructive'
                  ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90'
                  : ''
              }
            >
              {modalState.confirmText}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </ModalContext.Provider>
  )
}
