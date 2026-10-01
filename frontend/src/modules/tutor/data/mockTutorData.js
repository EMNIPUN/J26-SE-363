import { BookOpenCheck, Compass, Flame } from 'lucide-react'

// The three cooperating tutor agents. Every assistant message and nudge is
// attributed to one of them so students can see who is guiding them.
export const AGENTS = {
  learning: {
    key: 'learning',
    label: 'Project Learning',
    icon: BookOpenCheck,
    tone: 'bg-primary/10 text-primary',
  },
  sprint: {
    key: 'sprint',
    label: 'Sprint Guidance',
    icon: Compass,
    tone: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400',
  },
  momentum: {
    key: 'momentum',
    label: 'Learning Momentum',
    icon: Flame,
    tone: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400',
  },
}

export const MOMENTUM = {
  score: 72,
  change: +6,
  streakDays: [true, true, false, true, true, true, false],
  sessionsThisWeek: 3,
  conceptsMastered: 14,
  checksPassed: 9,
  checksTotal: 11,
}

export const CONCEPTS = [
  { id: 'c1', label: 'Requirements engineering', mastery: 82 },
  { id: 'c2', label: 'Effort estimation', mastery: 54 },
  { id: 'c3', label: 'Secure coding practices', mastery: 41 },
  { id: 'c4', label: 'Software testing', mastery: 67 },
]

export const SPRINT_GUIDANCE = [
  {
    id: 'g1',
    agent: 'sprint',
    title: 'Break REQ-021 into smaller stories',
    detail: 'Its estimate (13 pts) is above your team’s safe sprint limit of 8 points per story.',
    prompt: 'How should I split REQ-021 into smaller user stories?',
  },
  {
    id: 'g2',
    agent: 'learning',
    title: 'Revisit planning poker basics',
    detail: 'Your last two estimates differed from the team median by more than 60%.',
    prompt: 'Can you explain how planning poker estimation works?',
  },
  {
    id: 'g3',
    agent: 'learning',
    title: 'Understand the hardcoded-secret finding',
    detail: 'AEGIS flagged config.py — learn why it matters before fixing it.',
    prompt: 'Why is a hardcoded secret in config.py a security risk?',
  },
]

export const SESSIONS = [
  { id: 's1', title: 'Splitting large user stories', agent: 'sprint', when: 'Today, 9:40 AM', messages: 8 },
  { id: 's2', title: 'Planning poker and estimation bias', agent: 'learning', when: 'Yesterday', messages: 12 },
  { id: 's3', title: 'Weekly momentum check-in', agent: 'momentum', when: 'Mon, Sep 28', messages: 5 },
  { id: 's4', title: 'SQL injection and prepared statements', agent: 'learning', when: 'Fri, Sep 25', messages: 15 },
]

export const SUGGESTED_PROMPTS = [
  'What should I focus on this sprint?',
  'Explain story points with an example',
  'Quiz me on secure coding',
  'Why did my momentum score change?',
]

export const INITIAL_NUDGES = [
  {
    id: 'n1',
    agent: 'sprint',
    type: 'sprint',
    title: 'Sprint 4 deadline is at risk',
    message: 'Two of your tasks are still open with 3 days left. Want help prioritising them?',
    time: '20 min ago',
    unread: true,
    action: { label: 'Plan my tasks', prompt: 'Help me prioritise my open Sprint 4 tasks.' },
  },
  {
    id: 'n2',
    agent: 'learning',
    type: 'check',
    title: 'Learning check ready: effort estimation',
    message: 'A 5-question check to confirm your understanding before the next estimation round.',
    time: '2 hours ago',
    unread: true,
    action: { label: 'Start check', prompt: 'Start the effort estimation learning check.' },
  },
  {
    id: 'n3',
    agent: 'momentum',
    type: 'momentum',
    title: 'Nice streak — 3 active days in a row',
    message: 'Keep it going: a short 10-minute session today will maintain your momentum.',
    time: 'Yesterday',
    unread: false,
    action: { label: 'Start a session', prompt: 'Give me a 10-minute learning activity for today.' },
  },
  {
    id: 'n4',
    agent: 'learning',
    type: 'check',
    title: 'Close your security finding with a learning check',
    message: 'The hardcoded-secret finding closes once you pass a short comprehension check.',
    time: '2 days ago',
    unread: false,
    action: { label: 'Start check', prompt: 'Start the learning check for the hardcoded-secret finding.' },
  },
]

// Keyword routing that mimics the orchestrator choosing an agent; replaced by
// tutorService.sendMessage once the backend is connected.
export function mockAgentReply(text) {
  const q = text.toLowerCase()
  if (q.includes('sprint') || q.includes('prioriti') || q.includes('split') || q.includes('task')) {
    return {
      agent: 'sprint',
      content:
        'Here’s a plan for this sprint:\n\n1. Finish “Review open DART arbitration flags” first — it unblocks your teammates.\n2. Split REQ-021 into 2–3 smaller stories (each ≤ 8 points).\n3. Leave the security fix for Thursday and pair it with the learning check.\n\nWant me to draft the smaller stories for REQ-021?',
    }
  }
  if (q.includes('momentum') || q.includes('streak') || q.includes('10-minute')) {
    return {
      agent: 'momentum',
      content:
        'Your momentum score rose to 72 (+6) because you completed three sessions this week and passed two learning checks. A short session today keeps your streak alive — try a 5-question quiz on effort estimation.',
    }
  }
  return {
    agent: 'learning',
    content:
      'Good question. Story points measure relative effort, not hours. For example, if a login form is a 3, a password-reset flow with emails might be a 5 because it has more moving parts and unknowns.\n\nWould you like a quick 3-question check to test this?',
  }
}
