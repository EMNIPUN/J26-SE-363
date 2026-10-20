import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { securityAssistantService } from '../services/securityAssistantService.js'
import { isDemoMode } from '../config.js'

const key = (...parts) => ['security-assistant', isDemoMode() ? 'demo' : 'live', ...parts]

export function useRuns(team) {
  return useQuery({ queryKey: key('runs', team), queryFn: () => securityAssistantService.runs(team), enabled: Boolean(team) })
}

export function useStudents(team, enabled) {
  return useQuery({ queryKey: key('students', team), queryFn: () => securityAssistantService.students(team), enabled: Boolean(team) && enabled })
}

export function useRunOverview(team, run, student) {
  return useQuery({
    queryKey: key('run', team, run, student ?? null),
    queryFn: () => securityAssistantService.run(team, run, { student }),
    enabled: Boolean(team && run),
  })
}

// Which run and which student the page shows lives in the URL (?run=...&student=...), so a link reproduces the view.
// With no ?run= the newest run is shown.
export function useSelection(runs) {
  const [params, setParams] = useSearchParams()
  const run = params.get('run') || runs?.[0]?.run_id || null
  const student = params.get('student') || null
  const set = useMemo(
    () => (name, value) =>
      setParams((current) => {
        const next = new URLSearchParams(current)
        if (value) next.set(name, value)
        else next.delete(name)
        return next
      }),
    [setParams],
  )
  return { run, student, setRun: (value) => set('run', value), setStudent: (value) => set('student', value) }
}
