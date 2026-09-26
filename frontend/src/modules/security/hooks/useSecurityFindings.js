import { useQuery } from '@tanstack/react-query'
import { useScope } from '@/shared/context/useScope.js'
import { securityService } from '../services/securityService.js'

export function useSecurityFindings() {
  const { selectedGroup } = useScope()

  return useQuery({
    queryKey: ['security-findings', selectedGroup?.code],
    queryFn: () => securityService.getFindings(),
    enabled: Boolean(selectedGroup),
  })
}

export default useSecurityFindings
