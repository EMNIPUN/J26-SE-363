# SELVIA Team-Scoped Architecture & Guidelines

This document is the **single source of truth** for all 4 research modules (**Project Planning**, **Performance Assessment**, **Adaptive AI Tutor**, and **Security Assistant**) on how team scoping and tenancy isolation are structured in SELVIA.

---

## 🏛️ Conceptual Hierarchy vs Runtime Scoping

In the academic domain, projects belong to a batch and specialization:
```text
🎓 Batch (e.g. 2026 Batch — Y4S1)
   └── 💻 Specialization (e.g. Software Engineering)
        └── 👥 Research Group / Team (e.g. J26-SE-363 — SELVIA Platform)
             └── 👤 Student Members (e.g. Sadeesha, Chathush, Nipun, Dilshan)
```

### The Pragmatic Architectural Decision:
Instead of forcing users through 4 clumsy cascading dropdowns in the top header, **the entire application is scoped at the Team / Project level**:
- The **Team** (`/teams/:teamId/...`) is the active workspace.
- The **Students** are viewed and managed at the **Page and Tab level** (in roster tables, tabs, and detail views).

**Teams are real.** A lecturer creates a team and invites its students; the teams a person belongs to come from the Core API (`GET /api/v1/me/teams`) and are listed on `/home`. `useScope()` exposes them. The batch and specialization levels above are conceptual only; a team carries a `term` such as `2026-S1`. How teams, invitations and leadership work: [REGISTRATION_AND_TEAMS.md](../../docs/REGISTRATION_AND_TEAMS.md).

---

## 🌐 URL Routing Standard

All four module teams mount their routes under the team prefix:

```text
/teams/:teamId/app
/teams/:teamId/planning/*
/teams/:teamId/performance/*
/teams/:teamId/tutor/*
/teams/:teamId/security/*
```

### Role Behavior & Tenancy Guard (`TeamScopeGuard.jsx`):
1. **Everyone**:
   - Opens a team from `/home`; the team becomes the active workspace (`/teams/J26-SE-363/...`).
   - The top navbar has a **Searchable Team Dropdown** (`ScopeSelector.jsx`) with the teams the person belongs to, and an "All teams" link back to `/home`.
   - **Cross-Tenancy Protection**: a team the person is not in (a typo, another team's code) is "not found". The guard never falls back to a different team, and the Core API answers 404 for it too.
2. **Students** belong to the teams they accepted an invitation to (one per term).
3. **Lecturers** supervise the teams they created or were invited to (several lecturers can share a team; they evaluate and take no part in development). **Admins** can open any team.

---

## 💻 Developer Guide: How to Use `useScope()` in Any Module

Any developer can access the active team and its student members with **one hook**:

```jsx
import { useScope } from '@/shared/context/useScope'

export default function MyModuleDashboard() {
  const {
    isStudent,        // true for students, false for instructors/admins
    selectedGroup,    // { id: '<uuid>', code: 'J26-SE-363', name: 'Group 07', projectTitle: '...', repositoryUrl: '...', batchId: '2026-S1' (the term) }
    teamStudents,     // Array of student objects belonging to the active team
    studentProfile,   // Profile of the logged-in student (if isStudent === true)
  } = useScope()

  return (
    <div>
      <h2>Active Team: {selectedGroup.name} ({selectedGroup.code})</h2>
      <p>Project: {selectedGroup.projectTitle}</p>
      <p>Team Size: {teamStudents.length} members</p>
    </div>
  )
}
```

---

## ⚡ Connecting with TanStack Query (`useQuery`)

Always include `selectedGroup?.code` or `selectedGroup?.id` in your query keys so cache invalidation happens automatically when an instructor switches teams:

```jsx
import { useQuery } from '@tanstack/react-query'
import { useScope } from '@/shared/context/useScope'
import { myService } from '../services/myService'

export default function ProjectBoard() {
  const { selectedGroup } = useScope()

  const { data, isLoading } = useQuery({
    queryKey: ['team-backlog', selectedGroup?.code],
    queryFn: () => myService.getBacklog(selectedGroup?.id),
    enabled: Boolean(selectedGroup?.id),
  })

  if (isLoading) return <p>Loading team backlog...</p>

  return <div>{/* Render team backlog */}</div>
}
```

---

## 📡 Backend API Contract-First Forwarding

Even if the backend has not yet implemented database multi-tenancy, every outgoing HTTP request made via `apiClient.js` automatically forwards the active team in the request headers:

```http
X-Team-Id: J26-SE-363
```

When backend services are ready to filter queries by team, developers simply inspect `req.headers['x-team-id']`. **No frontend changes will be necessary.**

---

## 📋 Role Comparison Summary

| Feature | Student Persona | Instructor / Admin Persona |
| :--- | :--- | :--- |
| **Top Navbar** | Read-only active team pill badge | Interactive searchable team dropdown |
| **URL Scope** | Only teams they belong to | Only teams they belong to (admins: any team) |
| **Tamper Attempt** | "Not found" (never another team) | "Not found" (never another team) |
| **Student Roster** | Views own metrics + team contribution parity | Explores full roster table & deep dive reviews |
| **Backend Header** | Injects enrolled `X-Team-Id` | Injects currently selected `X-Team-Id` |
