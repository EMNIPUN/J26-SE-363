# Frontend UI & Theming Guide: shadcn/ui & Tailwind CSS

This document is the definitive guide for all developers contributing to the EduFlow frontend. It establishes how to build UI components, maintain design consistency, follow the global theme, and leverage the **shadcn/ui** component library and **MCP server**.

---

## 1. Core Principles (The "Zero-Custom-CSS" Rule)

To maintain a cohesive, maintainable, and responsive dashboard without duplicating styling effort:

1. **Do NOT write custom `.css` files** for pages or components. All legacy `.css` files (like `Button.css`, `Card.css`, `table.css`) have been removed.
2. **Use Tailwind CSS utility classes** for positioning, layout, typography, and spacing.
3. **Use semantic theme tokens** (e.g. `bg-background`, `text-foreground`, `bg-card`, `border-border`, `bg-primary`, `text-muted-foreground`), **never raw hardcoded hex codes** (like `#fff` or `#1e293b`).
4. **Prefer existing shadcn primitives** from `@/components/ui` or shared wrappers from `@/shared/components`.

---

## 2. Directory Architecture

```
frontend/
├── src/
│   ├── components/
│   │   └── ui/              # Raw shadcn UI primitives (button, card, table, sheet, etc.)
│   ├── shared/
│   │   ├── components/      # Reusable project components (StatCard, PageHeader, Avatar, Badge, etc.)
│   │   ├── layout/          # Dashboard layout (DashboardShell, TopNavbar, Sidebar)
│   │   ├── auth/            # AuthContext, credentials, protection wrappers
│   │   └── pages/           # Common pages (Login, NotFound, DashboardHome)
│   ├── modules/             # Capstone feature modules
│   │   ├── planning/        # Requirements planning, decomposition, estimation
│   │   ├── performance/     # Assessments, progress, instructor reports
│   │   ├── tutor/           # AI tutor chat, nudges
│   │   ├── security/        # AEGIS security review, remediation
│   │   └── admin/           # Users and settings management
│   ├── lib/
│   │   └── utils.js         # cn() utility helper (clsx + tailwind-merge)
│   ├── index.css            # Tailwind directives and semantic theme variables
│   └── main.jsx             # React entry point
├── components.json          # shadcn configuration
└── vite.config.js           # Path alias (@ -> ./src) and Tailwind vite plugin
```

---

## 3. How to Keep the Theme Consistent

The theme is defined semantically using CSS variables in `src/index.css`. This ensures uniform contrast, clean dark/light mode compatibility, and identical look-and-feel across all modules.

### Semantic Color Reference

| Category | Tailwind Class | Semantic Usage |
| :--- | :--- | :--- |
| **Page Surface** | `bg-background` / `text-foreground` | Main app background and default readable text |
| **Containers & Panels** | `bg-card` / `text-card-foreground` | Dashboard cards, tables, summary boxes |
| **Subtle Backgrounds** | `bg-muted` / `text-muted-foreground` | Inactive pills, table headers, secondary labels, timestamps |
| **Borders & Dividers** | `border-border` / `border-input` | Card outlines, dividers, form inputs |
| **Brand / Primary** | `bg-primary` / `text-primary-foreground` | Main action buttons, active navigation states, primary focus items |
| **Accent / Hover** | `hover:bg-accent` / `hover:text-accent-foreground` | List item hover states, menu dropdown hover items |
| **Destructive / Danger** | `text-destructive` / `bg-destructive/10` | Error messages, delete actions, critical security findings |
| **Success Status** | `text-emerald-700` / `bg-emerald-50` | Quality gate passed, active status, good progress |
| **Warning Status** | `text-amber-700` / `bg-amber-50` | Medium risk, invited status, review pending |

### ❌ Anti-Patterns vs. ✅ Best Practices

```jsx
// ❌ BAD: Hardcoded styles & inline colors
<div style={{ backgroundColor: '#ffffff', color: '#333333', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
  <span style={{ color: '#4f46e5' }}>Title</span>
</div>

// ✅ GOOD: Semantic Tailwind tokens & shadcn Card
<Card className="p-5 border-border bg-card">
  <span className="font-semibold text-primary">Title</span>
</Card>
```

### Dark / Black Theme Support

The application supports three theme modes: **Light**, **Dark / Black** (OLED deep-black aesthetic), and **System** (follows OS preferences).

- **How it works**: The `ThemeProvider` toggles the `.dark` class on the root `<html>` element. All semantic tokens (e.g. `bg-background`, `bg-card`, `border-border`, `text-foreground`) adapt automatically based on the variables defined in `src/index.css`.
- **User Toggle**: Users can switch themes via the `<ThemeToggle />` component in the `TopNavbar` or through **Admin > Settings > Appearance**.
- **Accessing Theme in Code**:
  ```jsx
  import { useTheme } from '@/shared/theme/useTheme'

  function MyComponent() {
    const { theme, setTheme, resolvedTheme } = useTheme()
    // theme: 'light' | 'dark' | 'system'
    // resolvedTheme: 'light' | 'dark'
    return <button onClick={() => setTheme('dark')}>Go Dark</button>
  }
  ```
- **Designing for Both Themes**: Because shadcn components consume semantic classes (`bg-card`, `border-border`, `text-foreground`), they look visually balanced in both themes without needing extra code. If you need variant styling specifically in dark mode, use Tailwind's `dark:` modifier (e.g. `dark:bg-emerald-950/40 dark:text-emerald-400`).

---

## 4. Working with shadcn UI Primitives

### Adding a New shadcn Component

Whenever you need a new UI element (e.g., `dialog`, `tabs`, `accordion`, `popover`, `select`, `tooltip`, `progress`), run:

```bash
npx shadcn@latest add <component-name>
```

**Examples:**
```bash
# Add a modal dialog
npx shadcn@latest add dialog

# Add tabs for switching views
npx shadcn@latest add tabs

# Add select dropdown and tooltip
npx shadcn@latest add select tooltip
```

The component will be automatically generated in `src/components/ui/<component-name>.jsx` with all required dependencies installed.

### Importing Components with `@`

Always import from `@/components/ui/...`:

```jsx
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
```

### Merging Class Names with `cn()`

When combining custom or conditional classes, use the `cn()` helper from `@/lib/utils`:

```jsx
import { cn } from '@/lib/utils'

function NotificationItem({ isRead, message }) {
  return (
    <div className={cn(
      "p-3 rounded-lg border text-sm transition-colors",
      isRead ? "bg-muted/40 text-muted-foreground border-transparent" : "bg-card text-foreground border-border font-medium"
    )}>
      {message}
    </div>
  )
}
```

---

## 5. Standard Dashboard Component Patterns

### A. Data Tables
Always use shadcn `Table` primitives instead of unstyled HTML tables or custom table classes:

```jsx
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card } from '@/components/ui/card'
import Badge from '@/shared/components/Badge.jsx'

export function UserList({ users }) {
  return (
    <Card className="p-0 overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Role</TableHead>
            <TableHead className="text-right">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.map((user) => (
            <TableRow key={user.id}>
              <TableCell className="font-medium">{user.name}</TableCell>
              <TableCell>{user.role}</TableCell>
              <TableCell className="text-right">
                <Badge tone="success">Active</Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}
```

### B. Metric & Stat Cards
Use `@/shared/components/StatCard.jsx`:

```jsx
import { ClipboardCheck } from 'lucide-react'
import StatCard from '@/shared/components/StatCard.jsx'

<StatCard
  icon={ClipboardCheck}
  label="Quality Gate Score"
  value="86%"
  trend="+4% this sprint"
  tone="success" // 'primary' | 'success' | 'warning' | 'danger'
/>
```

### C. Standard Page Header
Use `@/shared/components/PageHeader.jsx`:

```jsx
import PageHeader from '@/shared/components/PageHeader.jsx'
import Button from '@/shared/components/Button.jsx'
import { Plus } from 'lucide-react'

<PageHeader
  title="Requirements Decomposition"
  breadcrumb={['Planning', 'Requirements', 'Decomposition']}
  description="Break user stories down into testable engineering tasks."
  actions={
    <Button icon={Plus} size="md">
      New Requirement
    </Button>
  }
/>
```

---

## 6. Using the shadcn MCP Server with AI Assistants

This repository is configured with the **shadcn MCP Server** in `.vscode/mcp.json` and `.mcp.json`.

If you use AI coding assistants (such as Antigravity, GitHub Copilot in VS Code, Cursor, or Claude Code), the assistant can inspect the shadcn registry and install components directly for you.

### Example Prompts for AI:
- *"Add the dialog and progress components from shadcn to this project."*
- *"Search shadcn for a date picker or calendar component and install it."*
- *"Create an assessment form using shadcn Card, Input, Label, and Button."*
- *"Show me all available components in the shadcn registry."*

---

## 7. Pre-commit & Build Checks

Before pushing any changes, verify that your code compiles cleanly and adheres to linting standards:

```bash
# Run linting check
npm run lint

# Verify production build
npm run build
```
