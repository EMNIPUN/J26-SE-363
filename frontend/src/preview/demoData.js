// Invented answers of the Core API, for the screenshot tests and for the demo mode of the app (?demo=1 in development). The numbers are for layout only.
// The graph of the agent, handed in by respond() (the app imports it, the Playwright tests read it from disk).
let topology = { nodes: [], edges: [] }

export const STUDENTS = [
  { id: 'u-sam', name: 'Sadeesha Sathsara', mark: 78, interval: [64, 88], status: 'provisional', pattern: 'Consistent deep contributor' },
  { id: 'u-eri', name: 'Eric Devon', mark: 61, interval: [45, 76], status: 'pending_review', pattern: 'Balanced contributor' },
  { id: 'u-cha', name: 'Chathush Perera', mark: 52, interval: [34, 71], status: 'provisional', pattern: 'Burst worker' },
  { id: 'u-nip', name: 'Nipun Dhananjaya', mark: 14, interval: [6, 39], status: 'pending_review', pattern: 'Free rider' },
]
const scored = (score, extra = {}) => ({ status: 'completed', score, interval: [Math.max(0, score - 0.15), Math.min(1, score + 0.15)], provisional: true, ...extra })
const none = (status) => ({ status, score: null, interval: null, provisional: false })

function factors(i) {
  const k = [[0.82, 0.74, 0.7, null, 0.71, 'pending'], [0.68, 0.26, 0.33, null, 0.8, 'pending'], [0.75, 0.52, 0.55, null, 0.76, 'pending'], [0, 0.1, null, null, 0.7, 'pending']][i]
  return {
    effort: k[0] === 0 ? none('not_available') : scored(k[0]), consistency: scored(k[1]), requirement_fulfillment: k[2] == null ? none('not_available') : scored(k[2]), collaboration: none('not_available'),
    task_complexity: scored(k[4]), code_ownership: none('pending'), behavioral_pattern: { persona: STUDENTS[i].pattern, applied: false, modifier: 1 },
  }
}
const block = (title, status, score, reasons, warnings = []) => ({ title, status, score, band: score == null ? null : score < 0.34 ? 'low' : score < 0.67 ? 'medium' : 'high', reasons, warnings, how_much_to_trust: 'Checked on 144 assistant-rated sprints; not yet compared with lecturer grades.' })

function result(i) {
  const s = STUDENTS[i]
  const f = factors(i)
  const flags = i === 1 ? [{ severity: 'warn', message: 'Requirement Fulfillment could not be judged: the model refused two requests.', action: 'escalate', reason: 'A person should check the two tasks by hand.' }] : i === 3 ? [{ severity: 'warn', message: 'No commits in the sprint, but the board shows 2 tasks as done.', action: 'escalate', reason: 'The commits may be under an unmapped e-mail address.' }] : []
  return {
    id: `r${i}`, run_id: 'run-done', team_ref: 'MC01', sprint_id: 'MC01-S3', student_id: s.id, student: { name: s.name, picture: null }, mark: s.mark, effective_mark: i === 1 ? 66 : s.mark, mark_interval: s.interval, status: s.status,
    override: i === 1 ? { mark: 66, reason: 'Pair-programmed with Chathush; most of the integration was his.', by_name: 'Ada Lecturer', at: '2026-04-14T09:00:00Z' } : null, factors: f,
    justification: {
      summary: `Provisional mark ${s.mark} out of 100 (plausible range ${s.interval[0]} to ${s.interval[1]}). Strongest factor: Task Complexity; weakest: ${i === 3 ? 'Effort' : 'Consistency'}. Not part of the mark: Code Ownership, Collaboration.`,
      friendly_summary: i === 0 ? 'A steady contributor this sprint, with most of the work on the gateway and deployment, and every task on time.' : null,
      how_computed: 'Mark = 100 x pattern adjustment x sum of (weight x factor score) over the factors that exist.', caveats: ['All validation of these factors used ratings written by the assistant, not human graders. Treat the mark as a prediction to check, not a grade.'],
      flags,
      factors: {
        effort: block('Effort', f.effort.status, f.effort.score, i === 3 ? ['No commits changed a counted source line in this sprint.'] : ['9 counted commits, 2335 net lines of real code, 58 files changed, 2 tasks finished', '44 comment, blank or formatting-only lines were not counted as work'], i === 3 ? ['Effort cannot be measured: 0 commits.'] : []),
        consistency: block('Consistency', 'completed', f.consistency.score, ['worked on about 3 of 6 days; first commit on day 4 of the sprint']),
        requirement_fulfillment: block('Requirement Fulfillment', f.requirement_fulfillment.status, f.requirement_fulfillment.score, ['task MC01-304: 1 of 4 acceptance criteria met, 1 partly', 'task MC01-305: 3 of 4 acceptance criteria met'], i === 1 ? ['2 model calls were refused and retried'] : []),
        collaboration: block('Collaboration', 'not_available', null, ['Collaboration could not be measured: nobody in the team reviewed or commented in this sprint. It is left out of the mark and its weight is shared by the other factors.']),
        task_complexity: block('Task Complexity', 'completed', f.task_complexity.score, ['5 story points assigned in the sprint over 3 subtasks in the sampled task'], ['this model is not shown to beat the single-feature baseline']),
        code_ownership: block('Code Ownership', 'pending', null, ['Code Ownership is still pending: waiting for the student\'s answer. The mark is provisional until it arrives.']),
        behavioral_pattern: { persona: s.pattern, reasons: ['Work is spread evenly over the sprint with high effort.'] },
      },
      audit: { summary: 'The results are consistent; one factor needs a person to look at it.', model: 'openai/gpt-oss-120b', checked: [{ tool: 'inspect_evidence', result: '{"count": 9, "recent": [...]}' }, { tool: 'get_factor_card', result: '{"title": "Effort"...}' }], left_out: {}, actions: flags.map((x, n) => ({ id: `x${n}`, factor: 'requirement_fulfillment', severity: 'warn', action: x.action, reason: x.reason })) },
    },
  }
}

function ownRow() {
  const r = { ...result(0) }
  for (const k of ['id', 'run_id', 'student', 'override', 'effective_mark']) delete r[k]
  return { ...r, student_id: 'me', mark: 78, overridden: false, justification: { ...r.justification, flags: undefined, audit: undefined } }
}

export const runsList = (state = 'done') => [
  { id: state === 'done' ? 'run-done' : 'run-live', team_ref: 'MC01', sprint_id: 'MC01-S3', mode: 'snapshot', status: state === 'done' ? 'succeeded' : 'running', created_at: '2026-04-13T18:10:00Z', started_at: '2026-04-13T18:10:05Z', finished_at: state === 'done' ? '2026-04-13T18:24:30Z' : null, has_report: state === 'done', summary: state === 'done' ? { students: 4, method: { weights: { effort: 0.2, consistency: 0.15, requirement_fulfillment: 0.25, collaboration: 0.15, task_complexity: 0.1, code_ownership: 0.15 }, factors: { effort: { title: 'Effort', measures: 'Commits that carry code, net lines of real code, files and tasks finished.', validation: 'Checked on 144 sprints rated by an assistant. Beats the single-feature baseline.', limits: 'Counts source code only: configuration and documents do not count.' }, consistency: { title: 'Consistency', measures: 'How evenly the work is spread over the sprint.', validation: 'Cross-validated MAE 0.058.', limits: 'Fitted on 14-day sprints.' }, requirement_fulfillment: { title: 'Requirement Fulfillment', measures: 'Whether the student\'s own code meets the acceptance criteria.', validation: 'No finished held-out evaluation.', limits: 'The judge sees only the student\'s changed lines.' }, collaboration: { title: 'Collaboration', measures: 'Substantive reviews of teammates\' pull requests.', validation: 'Unavailable for most sprints.', limits: 'Needs reviews to exist.' }, task_complexity: { title: 'Task Complexity', measures: 'How demanding the tasks were.', validation: 'Does not beat the story-point baseline.', limits: 'Close to the story points.' }, code_ownership: { title: 'Code Ownership', measures: 'A question about code the student wrote.', validation: 'Tested on Python only.', limits: 'Rated on assistant-written answers.' }, behavioral_pattern: { title: 'Behavioral Pattern', measures: 'The working pattern.', validation: 'Rules calibrated on 144 sprints.', limits: 'Two patterns rarely fire.' } } } } : {}, requested_by: 'u-lec' },
]

function events(upTo = Infinity) {
  const out = []
  let seq = 0
  let t = Date.parse('2026-04-13T18:10:05Z')
  const push = (type, node_path, message = '', extra = {}) => { seq += 1; t += 1500; out.push({ seq, ts: new Date(t).toISOString(), type, node_path, message, level: 'info', payload: extra }) }
  const node = (path, secs, logs = []) => { push('node_start', path, path.split('/').pop()); logs.forEach((l) => push('log', path, l)); push('node_end', path, path.split('/').pop(), { seconds: secs }) }
  const teamNodes = topology.nodes.filter((n) => n.group === 'team')
  const lane = topology.nodes.filter((n) => n.group === 'student')
  for (const n of teamNodes) {
    if (n.id === 'dispatch_students') {
      push('node_start', 'team/dispatch_students', 'dispatch_students')
      for (const s of STUDENTS) {
        for (const l of lane) {
          const p = `student:${s.id}/${l.id}`
          if (l.id === 'rf_subagent') {
            push('node_start', p, l.id); push('log', p, 'task_start: judging task MC01-304'); for (let k = 0; k < 4; k++) push('log', p, `llm_call: agent:decide:MC01-304:C${k + 1}:0: ${1100 + k * 300}+${40 + k * 11} tokens, 1.${k}s`)
            push('log', p, 'task_done: task MC01-304: fulfilment 0.33'); push('node_end', p, l.id, { seconds: 41.2 })
          } else node(p, 1.4 + (l.id.length % 5), [`${l.label}: ok`])
        }
      }
      push('node_end', 'team/dispatch_students', 'dispatch_students', { seconds: 612 })
    } else node(`team/${n.id}`, 2.5 + n.id.length % 7, [`${n.label} finished`])
  }
  push('run_end', '', 'succeeded')
  return out.slice(0, upTo)
}
export const liveEvents = () => {
  // stop in the middle of the second student's factors
  const all = events()
  const cut = all.findIndex((e) => e.node_path === `student:${STUDENTS[1].id}/rf_subagent` && e.type === 'node_start') + 3
  return all.slice(0, cut)
}

// Ten code questions about one student's functions, in every state, as the final assessment can produce.
const CODE = [
  ['report.py', [1, 9], 'build_report', 'In your own words, what does build_report do, and what do rows and threshold control?', 'It adds up the rows above the threshold and returns the total with the doubled values.', 4.2],
  ['gateway/auth.py', [12, 31], 'verify_token', 'What happens when verify_token receives an expired token, and why is that check done before the role lookup?', 'It raises an unauthorized error. The role lookup costs a database call, so it is skipped for a token that is already invalid.', 4.6],
  ['gateway/routes.py', [40, 58], 'create_visit', 'Which input does create_visit reject, and what does the caller get back in that case?', 'It rejects a visit with no patient id and returns a 422 with the field name.', 3.8],
  ['scheduler/slots.py', [5, 27], 'free_slots', 'Why does free_slots sort the booked intervals before it walks through them?', 'Sorting lets it find gaps in one pass; without it two overlapping bookings could hide a gap.', 4.4],
  ['scheduler/slots.py', [30, 44], 'merge_intervals', 'What would merge_intervals return for [(1, 3), (2, 6), (8, 10)]?', '(1, 6) and (8, 10), because the first two overlap.', 5],
  ['records/store.py', [3, 22], 'save_record', 'What does save_record do if the same record id is saved twice?', 'It updates the existing row instead of adding a second one.', 3.2],
  ['records/store.py', [25, 39], 'archive_old', 'What is the risk in how archive_old chooses which records to remove?', 'It compares dates as text, so a record from a different year could be removed by mistake.', 2.6],
  ['notify/mailer.py', [8, 30], 'send_reminder', 'Why is the mail sent from a background task and not inside the request?', 'Sending takes seconds and could fail, so the visitor should not wait for it.', 4.0],
  ['deploy/health.py', [2, 15], 'check_ready', 'What does check_ready test, and what status does it give while the database is down?', null, null],
  ['deploy/health.py', [18, 33], 'wait_for_db', 'How many times does wait_for_db try, and what happens after the last try?', null, null],
]
const QUESTIONS = CODE.map(([file, range, fn, question, answer, rating], i) => ({
  n: i + 1,
  status: answer ? 'answered' : i === 8 ? 'open' : 'expired',
  file_path: file,
  line_range: range,
  snippet: `def ${fn}(items, limit=10):\n    result = []\n    for item in items:\n        if item.ok and len(result) < limit:\n            result.append(item)\n    return result`,
  question,
  answer,
  answered_at: answer ? '2026-04-14T10:00:00Z' : null,
  in_second_window: i === 5,
  rating,
  warnings: i === 6 ? ['The answer scorer was not sure about this one.'] : [],
}))

const GATE = {
  ok: { state: 'ok' },
  repo_not_linked: { state: 'repo_not_linked', is_leader: false, installed: false, repo: null },
  repo_not_linked_leader: { state: 'repo_not_linked', is_leader: true, installed: true, installed_by: 'sadeesha', repo: null },
  repo_not_installed_leader: { state: 'repo_not_linked', is_leader: true, installed: false, repo: null },
  account_not_linked: { state: 'account_not_linked', installed: true, repo: 'acme/app', is_leader: false },
  read_only: { state: 'read_only', installed: true, repo: 'acme/app', login: 'chathush', permission: 'read', is_leader: false },
  no_access: { state: 'no_access', installed: true, repo: 'acme/app', login: 'some-other-account', permission: 'none', is_leader: false },
  github_unavailable: { state: 'github_unavailable', installed: true, repo: 'acme/app', login: 'eric-devon', is_leader: false },
}


/** What the Core API would answer for `method path`, or a 404. `topology` is the graph of the agent (fixtures/topology.json). */
export function respond(p, m, { role = 'instructor', live = false, gate = 'ok' } = {}, graph = topology) {
    topology = graph
    const json = (body, status = 200) => ({ status, body })
    if (p === '/teams/MC01') return json({ id: 't1', code: 'MC01', name: 'MediCare', term: '2026-S1', status: 'active', my_role: 'lecturer', repo_url: 'https://github.com/acme/app', members: [], invitations: [] })
    if (p === '/performance/teams/MC01/tracking') return json({ team_ref: 'MC01', repo_url: 'https://github.com/acme/app', board_ref: 'MC01', status: 'active', config: { sprints: [{ id: 'MC01-S3', start: '2026-04-10', end: '2026-04-15' }, { id: 'MC01-S4', start: '2026-04-16', end: '2026-04-21' }], release_to_students: true } })
    if (p === '/performance/teams/MC01/readiness') return json({ ready: true, blockers: [], notes: ['Lee has not connected GitHub.'], repo: 'acme/app', members: [{ user_id: 'u1', name: 'Sadeesha Sathsara', login: 'sadeesha', state: 'ready', is_leader: true }, { user_id: 'u2', name: 'Eric Devon', login: 'eric-devon', state: 'ready' }, { user_id: 'u3', name: 'Chathush Perera', login: 'chathush', state: 'read_only' }, { user_id: 'u4', name: 'Nipun Dhananjaya', login: null, state: 'not_connected' }] })
    if (/^\/performance\/teams\/MC01\/runs$/.test(p)) return json(runsList(live ? 'live' : 'done'))
    if (/\/sprints\/[^/]+\/results$/.test(p)) return json(STUDENTS.map((_, i) => result(i)))
    if (/\/trajectory$/.test(p)) return json([2, 3, 4, 5].map((d, k) => ({ as_of: `2026-04-${10 + d}T20:00:00Z`, sprint_elapsed: d / 6, mark: 30 + k * 15, mark_interval: [20 + k * 12, 45 + k * 17], factors: { effort: { score: 0.3 + k * 0.15 }, consistency: { score: 0.5 } } })))
    if (/\/quiz$/.test(p)) return json({ ...QUESTIONS[0], questions: QUESTIONS })
    if (p === '/performance/graph') return json(topology)
    if (/^\/performance\/runs\/[^/]+\/events$/.test(p)) return json(live ? liveEvents() : events())
    if (/^\/performance\/runs\/[^/]+\/stream$/.test(p)) return { status: 404, body: '' }
    if (/^\/performance\/runs\/[^/]+$/.test(p) && m === 'GET') return json(runsList(live ? 'live' : 'done')[0])
    if (p === '/performance/reviews') return json([{ id: 'rev1', run_id: 'run-done', team_ref: 'MC01', sprint_id: 'MC01-S3', student_id: 'u-eri', kind: 'audit', reason: 'requirement_fulfillment could not be computed | A person should check the two tasks by hand.', status: 'open' }])
    if (p === '/github/config') return json({ configured: true, app_slug: 'selvia-ai' })
    if (p === '/teams/MC01/gate') return json({ team: 'MC01', team_name: 'MediCare', leader_name: 'Sadeesha Sathsara', configured: true, verified: true, staff: false, can_link: false, ...GATE[gate] })
    if (p === '/teams/MC01/github/repos') return json([{ id: 1, full_name: 'sadeesha/medicare', private: false }, { id: 2, full_name: 'sadeesha/medicare-docs', private: true }])
    if (p === '/teams/MC01/github') return json({ repo: 'acme/app', ready: true, blockers: [], notes: [], can_link: role === 'instructor', members: [{ user_id: 'u1', name: 'Sadeesha Sathsara', login: 'sadeesha', state: 'ready', is_leader: true }, { user_id: 'u2', name: 'Eric Devon', login: 'eric-devon', state: 'ready' }, { user_id: 'u3', name: 'Chathush Perera', login: 'chathush', state: 'read_only' }, { user_id: 'u4', name: 'Nipun Dhananjaya', login: null, state: 'not_connected' }] })
    if (p === '/performance/me/results') return json([{ team_ref: 'MC01', ...ownRow() }])
    if (p === '/performance/me/quizzes') return json([{ id: 'q1', team_ref: 'MC01', sprint_id: 'MC01-S3', question: 'What does build_report do, and what do rows and threshold control?', snippet: 'def build_report(rows, threshold):\n    total = 0\n    for row in rows:\n        if row > threshold:\n            total += row\n    return total', file_path: 'report.py', line_range: [1, 6], status: 'open', deadline_at: new Date(Date.now() + 40 * 3600e3).toISOString() }])
    return json({}, 404)
}
