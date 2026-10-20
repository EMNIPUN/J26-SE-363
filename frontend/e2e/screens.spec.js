import { expect, test } from '@playwright/test'
import { mockApi, STUDENTS } from './mock.js'

const shot = (page, name, full = true) => page.screenshot({ path: `e2e/screenshots/${name}.png`, fullPage: full })
const open = async (page, hash, opts = {}) => {
  await mockApi(page, opts)
  await page.goto(`/preview.html?role=${opts.role || 'instructor'}${opts.theme ? `&theme=${opts.theme}` : ''}#${hash}`)
}

test('team results', async ({ page }) => {
  await open(page, '/teams/MC01/performance/assessment?sprint=MC01-S3')
  await expect(page.getByText('Sadeesha Sathsara').first()).toBeVisible()
  await expect(page.getByText('How the work is spread')).toBeVisible()
  await shot(page, 'team-results')
})

test('team results on a phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await open(page, '/teams/MC01/performance/assessment?sprint=MC01-S3')
  await expect(page.getByText('Eric Devon').first()).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true) // no sideways scroll
  await shot(page, 'team-results-phone')
})

for (const tab of ['development', 'runs', 'reviews', 'setup']) {
  test(`team ${tab}`, async ({ page }) => {
    await open(page, `/teams/MC01/performance/assessment?sprint=MC01-S3&tab=${tab}`)
    await page.waitForTimeout(600)
    await shot(page, `team-${tab}`)
  })
}

const scrollUntilVisible = (page, locator) => expect(async () => {
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  await expect(locator).toBeVisible({ timeout: 1500 })
}).toPass({ timeout: 15000 })

test('a student for the lecturer: separate sections, parts that come in one by one, a way into the questions', async ({ page }) => {
  await open(page, `/teams/MC01/performance/students/${STUDENTS[1].id}?sprint=MC01-S3`)
  // the top of the page is a profile: a large photo and the name in large type
  await expect(page.getByRole('heading', { level: 1, name: STUDENTS[1].name })).toBeVisible()
  await expect(page.locator('main img, #root img').first()).toBeVisible()
  await expect(page.getByText('2nd of 4 in the team').or(page.getByText(/of 4 in the team/))).toBeVisible()
  for (const title of ['Points to check', 'How the mark is made', 'Why this mark', 'The factors']) await expect(page.getByRole('heading', { name: title })).toBeVisible()
  await expect(page.getByText('Effort added the most').or(page.getByText(/added the most/)).first()).toBeVisible()
  // the arrow on a factor card opens its explanation
  const height = async (name) => (await page.getByRole('heading', { name }).locator('xpath=ancestor::*[contains(@class,"gap-4")][1]').boundingBox()).height
  const before = await height('Consistency')
  await page.getByRole('button', { name: 'Show the explanation of Effort' }).click()
  await expect(page.getByText('In short').first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'Hide the explanation of Effort' })).toHaveAttribute('aria-expanded', 'true')
  await page.waitForTimeout(500)
  expect(Math.abs((await height('Consistency')) - before)).toBeLessThan(2) // the card next to it does not grow with it
  // later parts appear when they are about to be seen
  await scrollUntilVisible(page, page.getByRole('heading', { name: 'The code questions' }))
  await expect(page.getByText('Open all 10 questions')).toBeVisible()
  await expect(page.getByText('The code question', { exact: true })).toHaveCount(0)
  await scrollUntilVisible(page, page.getByRole('heading', { name: 'Day by day' }))
  await shot(page, 'student-lecturer')
})

test('the code questions have a page of their own, with ten or more of them', async ({ page }) => {
  await open(page, `/teams/MC01/performance/students/${STUDENTS[1].id}/questions?sprint=MC01-S3`)
  await expect(page.getByRole('heading', { name: 'Code questions' })).toBeVisible()
  await expect(page.getByRole('tab', { name: /All\s*10/ })).toBeVisible()
  await expect(page.getByRole('tab', { name: /Answered\s*8/ })).toBeVisible()
  await page.getByRole('tab', { name: /Not answered/ }).click()
  await expect(page.getByRole('button', { name: /How many times does wait_for_db try/ })).toBeVisible()
  await page.getByRole('tab', { name: /All/ }).click()
  await page.getByRole('button', { name: /In your own words, what does build_report do/ }).click()
  await expect(page.getByText('It adds up the rows above the threshold')).toBeVisible()
  await shot(page, 'student-questions')
})

test('the sprint picker is a styled menu, not the browser list', async ({ page }) => {
  await open(page, '/teams/MC01/performance/team/results?sprint=MC01-S3')
  await expect(page.locator('select')).toHaveCount(0)
  await page.getByRole('combobox', { name: 'Sprint' }).click()
  await expect(page.getByRole('option', { name: /MC01-S4/ })).toBeVisible()
  await expect(page.getByText('Apr 16 to Apr 21')).toBeVisible()
  await shot(page, 'sprint-picker')
  await page.getByRole('option', { name: /MC01-S4/ }).click()
  await expect(page.getByRole('combobox', { name: 'Sprint' })).toContainText('MC01-S4')
})

test('the pipeline of a finished run, and its replay', async ({ page }) => {
  await open(page, '/teams/MC01/performance/runs/run-done')
  await expect(page.getByText('Assess students').first()).toBeVisible()
  await expect(page.getByRole('button', { name: /Replay/ })).toBeVisible()
  await shot(page, 'pipeline-finished')
  await page.getByRole('button', { name: /Replay/ }).click()
  await page.waitForTimeout(900)
  await shot(page, 'pipeline-replay')
})

test('the pipeline of a live run', async ({ page }) => {
  await open(page, '/teams/MC01/performance/runs/run-live', { live: true })
  await expect(page.getByText('Running').first()).toBeVisible()
  await shot(page, 'pipeline-live')
  const active = await page.locator('.pf-step.active').count()
  expect(active).toBeGreaterThan(0)
  expect(await page.locator('.pf-line.flowing').count()).toBeGreaterThan(0) // the light travels down a line into the running step
})

test('method', async ({ page }) => {
  await open(page, '/teams/MC01/performance/method')
  await expect(page.getByRole('heading', { name: 'Weights', exact: true })).toBeVisible()
  await shot(page, 'method')
})

test('a student sees only their own assessment', async ({ page }) => {
  await open(page, '/teams/MC01/performance/my-assessment', { role: 'student' })
  await expect(page.getByText('A question about code you wrote')).toBeVisible()
  await expect(page.getByText('Eric Devon')).toHaveCount(0)
  await expect(page.getByText('Points to check')).toHaveCount(0)
  await shot(page, 'student-self')
})

test('a student is kept out of the lecturer pages', async ({ page }) => {
  await open(page, '/teams/MC01/performance/runs/run-done', { role: 'student' })
  await page.waitForTimeout(500)
  await expect(page.getByText('Assess students')).toHaveCount(0)
})

test('the GitHub link card', async ({ page }) => {
  await open(page, '/teams/MC01/github')
  await expect(page.getByText('Each member connects their GitHub account')).toBeVisible()
  await shot(page, 'github-card')
})

test('dark theme', async ({ page }) => {
  await open(page, '/teams/MC01/performance/students/u-sam?sprint=MC01-S3', { theme: 'dark' })
  await expect(page.getByRole('heading', { name: 'The factors' })).toBeVisible()
  await shot(page, 'student-dark')
})

const GATE_CASES = [
  ['repo_not_linked', 'Waiting for your team leader', 'Sadeesha Sathsara has not linked'],
  ['repo_not_linked_leader', 'Link your team\u2019s repository', 'Now choose the repository'],
  ['repo_not_installed_leader', 'Link your team\u2019s repository', 'Install on GitHub'],
  ['account_not_linked', 'Sign in with GitHub to enter MediCare', 'Continue with GitHub'],
  ['read_only', 'Your account can only read this repository', 'Use a different GitHub account'],
  ['no_access', '@some-other-account is not a collaborator of this repository', 'Use a different GitHub account'],
  ['github_unavailable', 'GitHub could not be reached', 'Try again in a moment'],
]
for (const [state, title, extra] of GATE_CASES) {
  test(`the gate says what to do when: ${state}`, async ({ page }) => {
    await open(page, '/teams/MC01/gate', { role: 'student', gate: state })
    await expect(page.getByRole('heading', { name: title })).toBeVisible()
    await expect(page.getByText(extra).first()).toBeVisible()
    await expect(page.getByText('The team dashboard')).toHaveCount(0) // the dashboard is not rendered behind the gate
    await shot(page, `gate-${state}`)
  })
}

test('the gate lets the student through when the check passes', async ({ page }) => {
  await open(page, '/teams/MC01/gate', { role: 'student', gate: 'ok' })
  await expect(page.getByText('The team dashboard')).toBeVisible()
})

test('the gate on a phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await open(page, '/teams/MC01/gate', { role: 'student', gate: 'no_access' })
  await expect(page.getByRole('heading', { name: /not a collaborator/ })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true)
  await shot(page, 'gate-phone')
})

test('the gate asks again on every load', async ({ page }) => {
  let calls = 0
  await open(page, '/teams/MC01/gate', { role: 'student', gate: 'ok' })
  await page.route((url) => url.pathname === '/api/teams/MC01/gate', async (route) => { calls += 1; await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ state: 'ok' }) }) })
  await page.reload()
  await expect(page.getByText('The team dashboard')).toBeVisible()
  await page.reload()
  await expect(page.getByText('The team dashboard')).toBeVisible()
  expect(calls).toBeGreaterThanOrEqual(2)
})

test('the access page lets the student on to where they were going once the check passes', async ({ page }) => {
  await open(page, '/teams/MC01/access?next=%2Fteams%2FMC01%2Fgithub', { role: 'student', gate: 'ok' })
  await expect(page.getByText('Each member connects their GitHub account')).toBeVisible()
  expect(page.url()).toContain('#/teams/MC01/github')
})

test('the access page stays on the check, at its own address, when the check fails', async ({ page }) => {
  await open(page, '/teams/MC01/access?next=%2Fteams%2FMC01%2Fgithub', { role: 'student', gate: 'account_not_linked' })
  await expect(page.getByRole('heading', { name: 'Sign in with GitHub to enter MediCare' })).toBeVisible()
  expect(page.url()).toContain('#/teams/MC01/access')
})

test('GitHub opens in a small window and the button keeps working until it reports back', async ({ page }) => {
  await open(page, '/teams/MC01/access', { role: 'student', gate: 'account_not_linked', popupFlow: true })
  const button = page.getByRole('button', { name: 'Continue with GitHub' })
  const popupOpened = page.waitForEvent('popup')
  await button.click()
  const popup = await popupOpened
  await expect(button).toBeDisabled() // busy while the small window is open
  await popup.waitForEvent('close') // the small window reports back and closes itself
  await expect(button).toBeDisabled() // still busy while the access is checked again
  await expect.poll(() => page.url()).not.toContain('/access') // and then it goes on, with no extra click
})

test('demo mode shows sample data on the real team address without asking the server (lecturer side)', async ({ page }) => {
  await page.goto('/preview.html?role=instructor&demo=1#/teams/SE4529/performance/assessment?sprint=MC01-S3')
  await expect(page.getByText('Sadeesha Sathsara').first()).toBeVisible()
  await expect(page.getByText(/Sample data/)).toBeVisible()
  await shot(page, 'demo-lecturer')
})

test('demo mode shows sample data on the student side', async ({ page }) => {
  await page.goto('/preview.html?role=student&demo=1#/teams/SE4529/performance/my-assessment')
  await expect(page.getByText(/Sample data/)).toBeVisible()
  await expect(page.getByText(/Eric Devon/)).toHaveCount(0) // a student sees only their own result
  await shot(page, 'demo-student')
})

test('the run page is one fixed screen: the pipeline and the logs scroll on their own', async ({ page }) => {
  await open(page, '/teams/MC01/performance/runs/run-done')
  await expect(page.getByText('Choose a step to read what it did, line by line.')).toBeVisible()
  await page.waitForTimeout(400)
  const m = await page.evaluate(() => {
    const scrollers = [...document.querySelectorAll('div')].filter((d) => getComputedStyle(d).overflowY === 'auto' && d.scrollHeight > d.clientHeight + 4)
    return { page: document.documentElement.scrollHeight - window.innerHeight, scrollers: scrollers.length }
  })
  expect(m.page).toBeLessThanOrEqual(1) // the page itself does not scroll
  expect(m.scrollers).toBeGreaterThanOrEqual(1) // a column inside does
  await shot(page, 'run-fixed-screen')
})
