import { useMutation, useQuery } from '@tanstack/react-query'
import { qualityService } from '../services/qualityService.js'

/** Upload an SRS .docx -> extract + score (mutation). */
export function useUploadSrs() {
  return useMutation({
    mutationFn: ({ file, threshold = 75 }) => qualityService.uploadSrs(file, threshold),
  })
}

/** Score one or more typed-in requirements (mutation) — drives re-check + manual add. */
export function useAnalyzeQuality() {
  return useMutation({
    mutationFn: ({ requirements, threshold = 75 }) => qualityService.analyzeQuality(requirements, threshold),
  })
}

/** Latest stored results for the active team — hydrates the page on mount. */
export function useQualityResults(enabled = true) {
  return useQuery({
    queryKey: ['quality-results'],
    queryFn: () => qualityService.getResults(),
    enabled,
  })
}

/** Quality gate decision for the active session. */
export function useQualityGate(enabled = true) {
  return useQuery({
    queryKey: ['quality-gate'],
    queryFn: () => qualityService.getGate(),
    enabled,
  })
}

/** Stored versions of one requirement (history drawer). */
export function useRequirementHistory(requirementRef) {
  return useQuery({
    queryKey: ['quality-history', requirementRef],
    queryFn: () => qualityService.getHistory(requirementRef),
    enabled: Boolean(requirementRef),
  })
}
