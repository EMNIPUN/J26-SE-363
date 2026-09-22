import { useContext } from 'react'
import { ModalContext } from '../context/modalContextDef.js'

export function useConfirm() {
  const context = useContext(ModalContext)
  if (!context) {
    throw new Error('useConfirm must be used within a ModalProvider')
  }
  return context.confirm
}
