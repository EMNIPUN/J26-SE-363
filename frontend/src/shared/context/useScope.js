import { useContext } from 'react'
import ScopeContext from './ScopeContext.jsx'

export function useScope() {
  const context = useContext(ScopeContext)
  if (!context) {
    throw new Error('useScope must be used within a ScopeProvider')
  }
  return context
}

export default useScope
