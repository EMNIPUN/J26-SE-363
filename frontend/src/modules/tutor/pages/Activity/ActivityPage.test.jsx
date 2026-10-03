import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ActivityPage from './ActivityPage.jsx'
import mockApi from '../../services/mockApi.js'
import tutorApi from '../../services/tutorApi.js'
import { ACTIVITY_COMPLETED_MESSAGE } from '../../utils/constants.js'

vi.mock('@/shared/context/useScope.js', () => ({
  useScope: () => ({ selectedGroup: { code: 'J26-SE-363' } }),
}))

const SLOW = { timeout: 3000 }

function renderActivity(activityId) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/teams/J26-SE-363/tutor/activity/${activityId}`]}>
        <Routes>
          <Route path="/teams/:teamId/tutor/activity/:activityId" element={<ActivityPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function finishInLearningApp(activityId) {
  sessionStorage.setItem('selvia-mock-learning-app-completions', JSON.stringify([activityId]))
  const frame = document.querySelector('iframe')
  act(() => {
    window.dispatchEvent(
      new MessageEvent('message', {
        source: frame.contentWindow,
        origin: window.location.origin,
        data: { type: ACTIVITY_COMPLETED_MESSAGE, activityId },
      }),
    )
  })
}

beforeEach(async () => {
  await mockApi.resetSession()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ActivityPage', () => {
  it('embeds the activity and updates competency when the learning app reports completion', async () => {
    renderActivity('act-quiz-jwt')

    expect(await screen.findByRole('heading', { name: 'JWT Adaptive Quiz' })).toBeInTheDocument()
    expect(screen.getByTitle('JWT Adaptive Quiz in Learning Lab')).toHaveAttribute('sandbox')

    fireEvent.click(screen.getByRole('button', { name: 'Check progress' }))
    expect(await screen.findByText(/has not reported a finished result yet/, {}, SLOW)).toBeInTheDocument()

    finishInLearningApp('act-quiz-jwt')

    expect(await screen.findByText('Activity completed', {}, SLOW)).toBeInTheDocument()
    expect(screen.getByText('Score 76%')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view full results/i })).toHaveAttribute(
      'href',
      '/teams/J26-SE-363/tutor/results/asm-act-quiz-jwt-1',
    )
  })

  it('shows an error with a retry when the activity cannot be loaded', async () => {
    sessionStorage.setItem('selvia-tutor-mock-fail', 'getActivity')
    renderActivity('act-quiz-jwt')

    expect(await screen.findByText('Could not open this activity')).toBeInTheDocument()

    sessionStorage.removeItem('selvia-tutor-mock-fail')
    fireEvent.click(screen.getByRole('button', { name: /try again/i }))

    expect(await screen.findByRole('heading', { name: 'JWT Adaptive Quiz' }, SLOW)).toBeInTheDocument()
  })

  it('refuses to embed a launch URL that is not secure', async () => {
    const activity = await mockApi.getActivity('act-quiz-jwt')
    vi.spyOn(tutorApi, 'getActivity').mockResolvedValue({ ...activity, launchUrl: 'http://lab.example.com/play' })
    renderActivity('act-quiz-jwt')

    expect(await screen.findByText('This activity cannot be opened here')).toBeInTheDocument()
    expect(document.querySelector('iframe')).toBeNull()
  })
})
