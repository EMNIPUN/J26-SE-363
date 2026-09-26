# MENTOR Frontend API Architecture Guidelines

This guide explains how to make backend API calls in the **MENTOR** platform following production-grade clean architecture.

---

## 🏗️ The 4-Layer Architecture

```
[ Layer 4: UI Components & TanStack Hooks ] (e.g. useProjects.js)
                      │
                      ▼
[ Layer 3: Domain Service Modules ]         (e.g. planningService.js)
                      │
                      ▼
[ Layer 2: Central HTTP Client ]             (src/shared/api/apiClient.js)
                      │
                      ▼
[ Layer 1: Environment & Reverse Proxy ]     (Vite proxy / Vercel rewrites)
```

---

## ⚡ 5 Golden Rules for Every Developer

1. **NEVER Hardcode URLs**:
   - ❌ Never write `fetch("http://localhost:8000/api/projects")` or `axios.get("https://api.mentor.com/...")`.
   - ✅ Always use relative paths starting with `/api` registered in [`src/shared/api/endpoints.js`](../src/shared/api/endpoints.js).
2. **NEVER Store Tokens in `localStorage`**:
   - ❌ Never store JWT tokens in `localStorage.setItem("token")` (vulnerable to XSS).
   - ✅ Access tokens live in JavaScript memory via [`tokenManager.js`](../src/shared/api/tokenManager.js), and refresh tokens live in secure `HttpOnly` cookies.
3. **NEVER Put Secret Keys in Frontend `.env`**:
   - ❌ Never put API secret keys, database passwords, or OpenAI keys in frontend `.env`.
   - Any variable starting with `VITE_*` is baked into the public browser bundle.
4. **NEVER Call `apiClient` Directly Inside React Components**:
   - ❌ Don't write `useEffect(() => { apiClient.get(...) }, [])` in components.
   - ✅ Create a service in `src/modules/<feature>/services/<feature>Service.js` and wrap it in a TanStack Query hook (`useQuery` / `useMutation`).
5. **Always Use `ENDPOINTS` Registry Constants**:
   - If you need a new route, add it to [`endpoints.js`](../src/shared/api/endpoints.js) first.

---

## 📖 Complete Developer Tutorial: How to Add & Use a New API

Here is an end-to-end example of adding a new feature (e.g. **Tasks**) with data fetching, creating a task, error handling, and loading states.

---

### Step 1: Register the Route in `endpoints.js`

Open [`src/shared/api/endpoints.js`](../src/shared/api/endpoints.js) and register your endpoint:

```javascript
// src/shared/api/endpoints.js
export const ENDPOINTS = {
  // ...
  TASKS: {
    LIST: '/planning/tasks',
    DETAIL: (id) => `/planning/tasks/${id}`,
    CREATE: '/planning/tasks',
    UPDATE: (id) => `/planning/tasks/${id}`,
    DELETE: (id) => `/planning/tasks/${id}`,
  },
}
```

---

### Step 2: Create the Domain Service

Create your service in `src/modules/<module-name>/services/<name>Service.js`:

```javascript
// src/modules/planning/services/taskService.js
import apiClient from '@/shared/api/apiClient'
import { ENDPOINTS } from '@/shared/api/endpoints'

export const taskService = {
  // GET: Fetch list with optional query filters (e.g. ?status=in_progress)
  getTasks: (params) => {
    return apiClient.get(ENDPOINTS.TASKS.LIST, { params })
  },

  // GET: Fetch single item by ID
  getTaskById: (taskId) => {
    return apiClient.get(ENDPOINTS.TASKS.DETAIL(taskId))
  },

  // POST: Create new record
  createTask: (payload) => {
    return apiClient.post(ENDPOINTS.TASKS.CREATE, payload)
  },

  // PATCH: Partial update
  updateTask: (taskId, updates) => {
    return apiClient.patch(ENDPOINTS.TASKS.UPDATE(taskId), updates)
  },

  // DELETE: Remove record
  deleteTask: (taskId) => {
    return apiClient.delete(ENDPOINTS.TASKS.DELETE(taskId))
  },
}

export default taskService
```

---

### Step 3: Create TanStack Query & Mutation Hooks

Create your hooks in `src/modules/<module-name>/hooks/useTasks.js`:

```javascript
// src/modules/planning/hooks/useTasks.js
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { taskService } from '../services/taskService'
import { toast } from 'sonner'

/**
 * 1. Fetching Data with useQuery:
 * - Automatically caches data for 5 minutes
 * - Auto-refetches when window regains focus
 * - Deduplicates requests across multiple components
 */
export function useTasks(filters) {
  return useQuery({
    queryKey: ['tasks', filters],
    queryFn: () => taskService.getTasks(filters),
  })
}

/**
 * 2. Modifying Data with useMutation:
 * - Handles loading state during submission
 * - Automatically invalidates cache on success so UI refreshes instantly
 */
export function useCreateTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (taskData) => taskService.createTask(taskData),
    onSuccess: () => {
      // Invalidate the 'tasks' query cache so the task list re-renders with the new task
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      toast.success('Task created successfully!')
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to create task.')
    },
  })
}
```

---

### Step 4: Consume in Your React Component

Notice how clean the component becomes: **zero `fetch` calls, zero `useState(loading)`, zero `useEffect` boilerplate!**

```jsx
// src/modules/planning/pages/TaskListPage.jsx
import { useState } from 'react'
import { useTasks, useCreateTask } from '../hooks/useTasks'
import { Button } from '@/components/ui/button'
import { CardSkeleton } from '@/components/ui/skeleton'

export default function TaskListPage() {
  const [filter, setFilter] = useState({ status: 'active' })

  // 1. Data Query (handles loading, error, and cached data)
  const { data: tasks, isLoading, isError, error } = useTasks(filter)

  // 2. Data Mutation (handles pending state on form submit)
  const createTaskMutation = useCreateTask()

  const handleAddNew = () => {
    createTaskMutation.mutate({
      title: 'Analyze Neural Agent Telemetry',
      priority: 'high',
      dueDate: '2026-10-01',
    })
  }

  // Loading State
  if (isLoading) {
    return (
      <div className="space-y-3 p-6">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    )
  }

  // Error State
  if (isError) {
    return (
      <div className="p-6 text-destructive">
        <p>Error loading tasks: {error.message}</p>
      </div>
    )
  }

  // Render Data
  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Project Tasks</h1>
        <Button 
          onClick={handleAddNew}
          disabled={createTaskMutation.isPending}
        >
          {createTaskMutation.isPending ? 'Creating...' : '+ Add Task'}
        </Button>
      </div>

      <div className="grid gap-3">
        {tasks?.map((task) => (
          <div key={task.id} className="p-4 rounded-xl border bg-card shadow-xs">
            <h3 className="font-semibold text-foreground">{task.title}</h3>
            <span className="text-xs text-muted-foreground">{task.priority}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## 🛡️ How Environments Work Automatically

| Environment | Where It Runs | How `/api` is Routed |
| :--- | :--- | :--- |
| **Local Dev** | `npm run dev` (Localhost) | Vite dev proxy in `vite.config.js` forwards `/api/*` to `http://localhost:8000` |
| **Testing** | Vercel (`mentor-frontend-testing`) | Vercel rewrite in `vercel.json` proxies `/api/*` to test backend |
| **Production** | Vercel (`mentor` production) | Vercel rewrite in `vercel.json` proxies `/api/*` to production backend |

**You never need to change backend URLs when shipping code.**
