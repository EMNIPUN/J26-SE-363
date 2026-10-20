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

test('a student for the lecturer', async ({ page }) => {
  await open(page, `/teams/MC01/performance/students/${STUDENTS[1].id}?sprint=MC01-S3`)
  await expect(page.getByText('Points to check')).toBeVisible()
  await expect(page.getByText('The code question')).toBeVisible()
  await shot(page, 'student-lecturer')
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
