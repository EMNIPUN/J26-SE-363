import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import bundle from '../demo/demoBundle.json'
import { OverviewBody } from '../pages/OverviewPage.jsx'
import { StartScanControl, NO_SCAN_REASON } from './AssistantFrame.jsx'
import { DemoBanner, HowToRead, MockBadge } from './common.jsx'
import RunBar from './RunBar.jsx'
import { CoverageGrid, IncompleteBanner, ProvenanceCard, StageStrip, ToolRunsTable } from './OverviewParts.jsx'

const html = (element) => renderToStaticMarkup(element)
const FULL = 'sample-python-demo'
const NO_LLM = 'sample-python-no-llm'

const failedTool = { tool: 'codeql', status: 'failed', reason: 'timed out after 600 s', tool_version: '2.20', duration_s: 600, findings_count: 0 }
const okTool = { tool: 'semgrep', status: 'succeeded', reason: '', tool_version: '1.0', duration_s: 3, findings_count: 4 }

describe('IncompleteBanner', () => {
  it('lists the reasons and the tools that did not do their job when the run is incomplete', () => {
    const markup = html(
      <IncompleteBanner run={{ complete: false, incomplete_reasons: ['stage interpret partial: 2 calls failed'] }} scan={{ tool_runs: [failedTool, okTool] }} />,
    )
    expect(markup).toContain('INCOMPLETE RUN. This is not a clean result.')
    expect(markup).toContain('role="alert"')
    expect(markup).toContain('stage interpret partial: 2 calls failed')
    expect(markup).toContain('codeql failed: timed out after 600 s')
    expect(markup).not.toContain('semgrep succeeded')
  })

  it('says COMPLETE, calmly, when everything ran', () => {
    const markup = html(<IncompleteBanner run={{ complete: true, incomplete_reasons: [] }} scan={{ tool_runs: [okTool] }} />)
    expect(markup).toContain('COMPLETE.')
    expect(markup).not.toContain('INCOMPLETE')
    expect(markup).not.toContain('role="alert"')
  })
})

describe('ToolRunsTable', () => {
  it('does not render a failed tool like a tool that found nothing', () => {
    const markup = html(<ToolRunsTable toolRuns={[failedTool, { ...okTool, tool: 'gitleaks', findings_count: 0 }]} />)
    const failedRow = markup.split('data-tool="codeql"')[1].split('</tr>')[0]
    const cleanRow = markup.split('data-tool="gitleaks"')[1].split('</tr>')[0]
    expect(failedRow).toContain('failed')
    expect(failedRow).toContain('n/a') // no count of findings is shown for a check that did not finish
    expect(failedRow).toContain('timed out after 600 s')
    expect(cleanRow).toContain('succeeded')
    expect(cleanRow).toContain('>0<')
    expect(failedRow).not.toEqual(cleanRow)
  })

  it('says so when no tool ran', () => {
    expect(html(<ToolRunsTable toolRuns={[]} />)).toContain('No tool ran in this run.')
  })
})

describe('CoverageGrid', () => {
  const none = { confirmed: 0, dismissed: 0, uncertain: 0, 'not interpreted': 0 }

  it('says that 0 findings means nothing where the category was not covered, and "clean" only with full coverage', () => {
    const markup = html(
      <CoverageGrid
        coverage={{ V1: { level: 'FULL', note: 'semgrep ran' }, V2: { level: 'NONE', note: 'codeql did not run' }, V3: { level: 'REDUCED', note: 'half' } }}
        counts={{ V1: none, V2: none, V3: none }}
      />,
    )
    expect(markup).toContain('Full coverage and no findings.')
    expect(markup).toContain('Not checked: 0 findings here means nothing.')
    expect(markup).toContain('Reduced coverage: 0 findings does not mean clean.')
    expect(markup.match(/Full coverage and no findings\./g)).toHaveLength(1)
    for (const id of ['V1', 'V2', 'V3', 'V4', 'V5']) expect(markup).toContain(`data-category="${id}"`)
  })
})

describe('StageStrip', () => {
  it('shows all eight stages and marks a skipped one and a failed one', () => {
    const stages = [
      { stage: 'fetch', status: 'completed', detail: 'repository fetched' },
      { stage: 'interpret', status: 'skipped', detail: '--allow-external-llm was not given: nothing was sent to any LLM' },
      { stage: 'risk', status: 'failed', detail: 'RuntimeError: scoring broke' },
    ]
    const markup = html(<StageStrip stages={stages} />)
    expect(markup.match(/data-stage=/g)).toHaveLength(8)
    expect(markup).toContain('data-stage="interpret" data-status="skipped"')
    expect(markup).toContain('data-stage="risk" data-status="failed"')
    expect(markup).toContain('data-stage="trace" data-status="not recorded"')
    expect(markup).toContain('nothing was sent to any LLM')
  })
})

describe('ProvenanceCard', () => {
  const overview = bundle.overview[FULL]

  it('shows the source, trigger, scan type, times, checkout, tool and model facts of the sample run', () => {
    const markup = html(<ProvenanceCard overview={overview} />)
    for (const text of ['vuln_py_repo', 'Manual', 'Saved scan reused', 'Read-only', 'No: nothing from the repository was run', 'mock-model', 'interpreter-v4', 'Seed']) {
      expect(markup).toContain(text)
    }
    expect(markup).toContain('A local folder, opened in place and only read')
    expect(markup).toMatch(/Tutor is a mock/)
  })

  it('says "Not recorded" instead of inventing what a run did not record', () => {
    const markup = html(<ProvenanceCard overview={{ manifest: {}, scan: { tool_runs: [] }, llm: { model: null, tutor_is_mock: true } }} />)
    expect(markup).toContain('Not recorded')
    expect(markup).toContain('No tool ran.')
    expect(markup).toContain('none (the LLM stages did not run)')
  })
})

describe('labels that must always be visible', () => {
  it('labels the mock Tutor', () => {
    expect(html(<MockBadge />)).toContain('MOCK')
    expect(html(<MockBadge />)).toContain('no answer was graded')
  })

  it('shows the demo label only when demo data is shown', () => {
    expect(html(<DemoBanner active={false} />)).toBe('')
    const markup = html(<DemoBanner active />)
    expect(markup).toContain('DEMO DATA')
    expect(markup).toContain('not a real student result')
  })

  it('has one "how to read this page" sentence', () => {
    expect(html(<HowToRead>Read the banner first.</HowToRead>)).toContain('How to read this page.')
  })

  it('has a disabled "Start a scan" control that gives the reason', () => {
    const markup = html(<StartScanControl />)
    expect(markup).toMatch(/<button[^>]* disabled=""/)
    expect(markup).toContain(NO_SCAN_REASON)
  })
})

describe('RunBar', () => {
  const runs = bundle.runs.runs
  const selection = { run: FULL, student: null, setRun() {}, setStudent() {} }

  it('shows a student their own contributor id and no student picker', () => {
    const markup = html(<RunBar runs={runs} selection={selection} role="student" students={[]} overview={bundle.overview[FULL]} />)
    expect(markup).toContain('Your contributor id')
    expect(markup).toContain(bundle.overview[FULL].my_contributor_ids[0])
    expect(markup).not.toContain('aria-label="Student"')
    expect(markup).toContain('MOCK')
    expect(markup).toContain('COMPLETE')
  })

  it('gives a lecturer a student picker and marks an incomplete run', () => {
    const markup = html(<RunBar runs={runs} selection={{ ...selection, run: NO_LLM }} role="instructor" students={bundle.students} overview={bundle.overview[NO_LLM]} />)
    expect(markup).toContain('aria-label="Student"')
    expect(markup).toContain('INCOMPLETE')
  })

  it('says when there is no contributor id for the student', () => {
    const markup = html(<RunBar runs={runs} selection={selection} role="student" students={[]} overview={{ ...bundle.overview[FULL], my_contributor_ids: [] }} />)
    expect(markup).toContain('so &quot;mine&quot; is empty')
  })
})

describe('the overview of the sample runs', () => {
  it('shows the full run as complete with all stages and the incomplete run with its reasons', () => {
    const full = html(<OverviewBody overview={bundle.overview[FULL]} />)
    expect(full).toContain('COMPLETE.')
    expect(full.match(/data-stage=/g)).toHaveLength(8)
    expect(full).toContain('data-slot="coverage"')

    const incomplete = html(<OverviewBody overview={bundle.overview[NO_LLM]} />)
    expect(incomplete).toContain('INCOMPLETE RUN. This is not a clean result.')
    expect(incomplete).toContain('data-stage="interpret" data-status="skipped"')
    expect(incomplete).toContain('allow-external-llm')
  })

  it('shows no e-mail address, local path or secret on either page', () => {
    for (const run of [FULL, NO_LLM]) {
      const markup = html(<OverviewBody overview={bundle.overview[run]} />)
      expect(markup).not.toMatch(/[\w.+-]+@[\w-]+\.[a-z]{2,}/i)
      expect(markup).not.toMatch(/[A-Z]:\\|\/Users\/|AKIA[0-9A-Z]{16}/)
    }
  })
})
