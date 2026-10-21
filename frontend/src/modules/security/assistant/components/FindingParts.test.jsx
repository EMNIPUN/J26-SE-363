import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import bundle from '../demo/demoBundle.json'
import { FindingCard } from '../pages/FindingDetailPage.jsx'
import { FindingsBody } from '../pages/FindingsPage.jsx'
import AssistantNav from './AssistantNav.jsx'
import { FindingRow, MaskedCode, RiskBreakdown, ScannerVsVerdict, StatusCounts, TraceLinks } from './FindingParts.jsx'
import { riskTotal } from '../lib/format.js'

const FULL = 'sample-python-demo'
const NO_LLM = 'sample-python-no-llm'
const html = (element) => renderToStaticMarkup(<MemoryRouter>{element}</MemoryRouter>)
const cards = (run) => Object.values(bundle.finding[run])
const card = (run, category) => cards(run).find((f) => f.category === category)
const overview = bundle.overview[FULL]

describe('the finding card on the sample run', () => {
  const f = card(FULL, 'V2')
  const markup = html(<FindingCard finding={f} overview={overview} team="J26-SE-363" run={FULL} />)

  it('has every section, in the order a reader needs them', () => {
    const order = ['finding-header', 'scanner-vs-verdict', 'data-slot="risk"', 'data-slot="trace"', 'data-slot="fix"', 'data-slot="probe"']
    const at = order.map((s) => markup.indexOf(s))
    expect(at.every((i) => i >= 0)).toBe(true)
    expect([...at].sort((a, b) => a - b)).toEqual(at)
    expect(markup).toContain('Request review')
  })

  it('puts the scanner evidence beside the LLM verdict, with its rationale and cited evidence', () => {
    expect(markup).toContain('data-slot="scanner"')
    expect(markup).toContain('data-slot="verdict"')
    expect(markup).toContain('py/sql-injection')
    expect(markup).toContain('CWE-89')
    expect(markup).toContain('app.py:22')
    expect(markup).toContain('This SQL query depends on a user-provided value.')
    expect(markup).toContain('mock-model')
    expect(markup).toContain('the evidence shows it')
    expect(markup).toContain('>E1<')
    expect(markup).toContain('data-slot="code"')
  })

  it('shows the risk factors adding up to the score', () => {
    expect(markup).toContain('data-factor="severity"')
    expect(markup).toContain('data-factor="exposure"')
    expect(markup).toContain(`Score <b>${f.risk.score}</b>`)
    expect(markup).toContain('aria-label="matches the score"')
  })

  it('shows the story, task and introducing commit with verified links and a pseudonym', () => {
    expect(markup).toContain('US-01')
    expect(markup).toContain('T-101')
    expect(markup).toContain('verified')
    expect(markup).toContain(f.introducing_commit.sha.slice(0, 7))
    expect(markup).toContain(f.introducing_commit.contributor)
    expect(markup).toContain('not who is at fault')
  })

  it('shows the fix steps, a safe example and OWASP and CWE links that open safely', () => {
    expect(markup).toContain('Use parameterised queries')
    expect(markup).toContain('data-slot="safe-example"')
    expect(markup).toContain('OWASP Cheat Sheet')
    expect(markup).toContain('CWE-89')
    expect(markup).toContain('https://cwe.mitre.org/data/definitions/89.html')
    expect(markup).toMatch(/target="_blank" rel="noopener noreferrer"/)
  })

  it('says so, in those words, when no tailored note was generated', () => {
    expect(markup).toContain('data-slot="tailored-note"')
    expect(markup).toContain('Tailored note not generated in this run')
  })

  it('shows the probe question with hint levels, simulated scores and the MOCK label', () => {
    const probe = markup.split('data-slot="probe"')[1]
    expect(probe).toContain('MOCK')
    expect(probe).toContain('nobody answered and nothing was graded')
    expect(probe).toContain('Attempt 1 (hint level 0)')
    expect(probe).toContain('simulated score')
    expect(probe).toContain('against the threshold 0.7')
  })
})

describe('a secret finding', () => {
  const f = card(FULL, 'V4')
  const markup = html(<FindingCard finding={f} overview={overview} team="J26-SE-363" run={FULL} />)

  it('says "Code line hidden for secrets" instead of an empty snippet box', () => {
    expect(markup).toContain('data-slot="code-hidden"')
    expect(markup).toContain('Code line hidden for secrets')
    expect(markup).not.toContain('data-slot="code"')
    expect(markup).not.toContain('data-slot="code-none"')
  })

  it('does so even when the answer carries no note', () => {
    expect(html(<MaskedCode finding={{ ...f, snippet_note: undefined, snippet: 'x' }} />)).toContain('Code line hidden for secrets')
  })

  it('shows no raw secret anywhere on the card', () => {
    expect(markup).not.toMatch(/AKIA[0-9A-Z]{16}/)
    expect(markup).not.toMatch(/[A-Za-z0-9+/]{40}/)
  })
})

describe('other states of the card', () => {
  it('says there is no code snippet when a non-secret finding has none', () => {
    const f = { ...card(FULL, 'V2'), snippet: null }
    expect(html(<MaskedCode finding={f} />)).toContain('data-slot="code-none"')
  })

  it('shows a downgrade: what the model first said and why the checks changed it', () => {
    const f = { ...card(FULL, 'V2'), status: 'uncertain', original_status: 'dismissed', downgrade_reason: 'cited evidence was not in the bundle' }
    const markup = html(<ScannerVsVerdict finding={f} model="m" />)
    expect(markup).toContain('The model first said <b>dismissed</b>')
    expect(markup).toContain('cited evidence was not in the bundle')
  })

  it('marks a candidate link differently from a verified one', () => {
    const f = { ...card(FULL, 'V2'), links: [{ kind: 'story', id: 'US-9', title: 't', status: 'candidate', methods: [], evidence: ['proposed'], confidence: 0.4 }] }
    const markup = html(<TraceLinks finding={f} />)
    expect(markup).toContain('candidate')
    expect(markup).not.toContain('>verified<')
    expect(html(<TraceLinks finding={{ ...f, links: [], introducing_commit: null }} />)).toContain('No introducing commit was found')
  })

  it('shows a finding the LLM did not analyse as not analysed and not ranked, never as clean', () => {
    const f = card(NO_LLM, 'V2')
    const markup = html(<FindingCard finding={f} overview={bundle.overview[NO_LLM]} team="J26-SE-363" run={NO_LLM} />)
    expect(markup).toContain('not interpreted')
    expect(markup).toContain('No rationale: the LLM did not analyse this finding.')
    expect(markup).toContain('Not ranked')
    expect(markup).toContain('No probe question was made for this finding.')
    expect(markup).not.toContain('data-factor=')
  })

  it('has a risk breakdown that adds up for every finding of the sample', () => {
    for (const f of cards(FULL).filter((x) => x.risk)) expect(riskTotal(f.risk.breakdown)).toBeCloseTo(f.risk.score, 1)
    expect(html(<RiskBreakdown risk={null} />)).toContain('Not ranked')
  })
})

describe('the list of findings', () => {
  const data = bundle.findings[FULL]
  const base = (extra) => ({
    overview,
    selection: { run: FULL, student: null },
    team: 'J26-SE-363',
    category: 'V3',
    mine: false,
    status: '',
    data,
    onChange() {},
    linkFor: (f) => `/x/${f.group_id}`,
    ...extra,
  })

  it('has one tab per type with the count of findings of that type', () => {
    const markup = html(<FindingsBody {...base()} />)
    for (const [id, row] of Object.entries(data.counts)) {
      const total = Object.values(row).reduce((a, b) => a + b, 0)
      expect(markup).toMatch(new RegExp(`data-category="${id}"[^>]*>${id} [^<]*<span[^>]*>${total}</span>`))
    }
  })

  it('lists the findings of the chosen type only, with counts by status', () => {
    const markup = html(<FindingsBody {...base()} />)
    const v3 = data.findings.filter((f) => f.category === 'V3')
    expect(markup.match(/data-group=/g)).toHaveLength(v3.length)
    expect(markup).toContain(`${v3.length} confirmed`)
    expect(markup).toContain('data-status="dismissed"')
  })

  it('lists only my findings with the "mine" filter, and says when there are none', () => {
    const mineCount = data.findings.filter((f) => f.category === 'V3' && f.mine).length
    expect(html(<FindingsBody {...base({ mine: true })} />).match(/data-group=/g) ?? []).toHaveLength(mineCount)
    const none = html(<FindingsBody {...base({ mine: true, data: { ...data, my_contributor_ids: [], findings: data.findings.map((f) => ({ ...f, mine: false })) } })} />)
    expect(none).toContain('None of the findings of this type are yours')
    expect(none).toContain('so &quot;mine&quot; is empty')
  })

  it('filters by status and says what an empty list means given the coverage', () => {
    const markup = html(<FindingsBody {...base({ status: 'dismissed' })} />)
    expect(markup).toContain('No dismissed findings of this type')
  })

  it('shows rows with title, place, tool, status, risk and a link to the finding', () => {
    const f = data.findings[0]
    const markup = html(<FindingRow finding={f} to="/go" />)
    expect(markup).toContain(f.title)
    expect(markup).toContain('href="/go"')
    expect(markup).toContain(`risk ${f.risk_score}`)
    expect(html(<FindingRow finding={{ ...f, risk_score: null, risk_rank: null }} to="/go" />)).toContain('not ranked')
  })

  it('shows the counts of a type by status, hiding "not interpreted" when there are none', () => {
    expect(html(<StatusCounts row={{ confirmed: 2, dismissed: 1, uncertain: 0, 'not interpreted': 0 }} />)).not.toContain('not interpreted')
    expect(html(<StatusCounts row={{ confirmed: 0, dismissed: 0, uncertain: 0, 'not interpreted': 3 }} />)).toContain('3 not interpreted')
  })
})

describe('navigation and privacy', () => {
  it('links the pages and keeps the chosen run in the address', () => {
    const markup = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/teams/J26-SE-363/security/assistant/findings/V2?run=r1']}>
        <Routes>
          <Route path="/teams/:teamId/security/assistant/*" element={<AssistantNav />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(markup).toContain('href="/teams/J26-SE-363/security/assistant?run=r1"')
    expect(markup).toContain('href="/teams/J26-SE-363/security/assistant/findings?run=r1"')
    expect(markup).toMatch(/aria-current="page"[^>]*>Findings by type/)
  })

  it('shows no e-mail address, local path or secret on any card of either run', () => {
    for (const run of [FULL, NO_LLM]) {
      for (const f of cards(run)) {
        const markup = html(<FindingCard finding={f} overview={bundle.overview[run]} team="J26-SE-363" run={run} />)
        expect(markup).not.toMatch(/[\w.+-]+@[\w-]+\.[a-z]{2,}/i)
        expect(markup).not.toMatch(/[A-Z]:\\|\/Users\/|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20}/)
        expect(markup).not.toMatch(/Jane|Eric/)
      }
    }
  })
})
