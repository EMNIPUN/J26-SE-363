# Frontend UI, Theming & Motion System Guide

This document is the **single source of truth** for all developers contributing to the EduFlow frontend. It details how to build UI components, maintain design and surface hierarchy, follow the global theme across light and dark modes, adhere to the motion system, and leverage **shadcn/ui** and the **shadcn MCP server**.

---

## 1. Core Principles (The "Zero-Custom-CSS" Rule)

To keep the entire frontend maintainable, visually unified, and responsive without duplicated effort:

1. **Do NOT write custom `.css` files** for individual pages or components. All legacy `.css` files have been removed.
2. **Use Tailwind CSS utility classes** for layout, spacing, and styling.
3. **Always use semantic theme tokens** (`bg-background`, `bg-card`, `bg-sidebar`, `border-border`, `text-foreground`, `text-muted-foreground`, `bg-primary`, `text-destructive`). **Never hardcode hex color values** (e.g. `#ffffff`, `#1e293b`).
4. **Prefer existing shadcn primitives** from `@/components/ui` and shared wrappers from `@/shared/components`.
5. **Always preserve the surface hierarchy and tactile motion system** detailed below.

---

## 2. Surface Background Hierarchy & Contrast

A common pitfall in web dashboards is placing white cards on pure white backgrounds, or flat dark cards on flat dark backgrounds, which creates a washed-out, clinical look with zero contrast.

EduFlow employs the **3-layer surface hierarchy** used by industry benchmarks like **Stripe**, **Linear**, **Vercel**, and **GitHub**:

```
┌────────────────────────────────────────────────────────────────────────┐
│ TopNavbar (Frame Surface: bg-sidebar/95 / bg-card/95)                   │
├──────────────┬──────────────────────────────────────────┬──────────────┤
│ Column 1     │ Column 2: Workspace Canvas (Floor)       │ Column 3     │
│ Sidebar      │ (Shaded Slate Canvas: bg-background)     │ AI Copilot   │
│ (Frame)      │                                          │ (Frame)      │
│ bg-sidebar   │   ┌──────────────────────────────────┐   │ bg-sidebar   │
│              │   │ Cards, Tables, Metric Panels     │   │              │
│              │   │ (Elevated Plate: bg-card)        │   │              │
│              │   │ border border-border shadow-xs   │   │              │
│              │   └──────────────────────────────────┘   │              │
└──────────────┴──────────────────────────────────────────┴──────────────┘
```

### Color Token Mapping

| Section / Element | Role | Light Mode Value | Dark / Black Mode Value | Tailwind Class |
| :--- | :--- | :--- | :--- | :--- |
| **Workspace Canvas** | Recessed floor | Soft Light Slate/Zinc Gray (`oklch(0.955 0.005 260)`) | Charcoal / Zinc Gray (`oklch(0.12 0.005 260)`) | `bg-background` |
| **Cards & Panels** | Elevated floating plate | Crisp Pure White (`oklch(1 0 0)`) | Elevated Dark Surface (`oklch(0.165 0.005 260)`) | `bg-card` + `shadow-xs border border-border` |
| **Cockpit Frame** | Sidebar, Navbar, AI Panel | Framing Pure White (`oklch(1 0 0)`) | Deep Black Frame (`oklch(0.07 0 0)`) | `bg-sidebar` + `border-sidebar-border` |
| **Borders & Dividers** | Structural separation | Crisp Defining Border (`oklch(0.89 0.005 260)`) | Luminous 12% Dark Border (`oklch(1 0 0 / 12%)`) | `border-border` |
| **Muted Surfaces** | Secondary tags, badges | Subtle Cool Tint (`oklch(0.935 0.005 260)`) | Subtle Dark Tint (`oklch(0.18 0.005 260)`) | `bg-muted` / `text-muted-foreground` |

### ❌ Anti-Patterns vs. ✅ Best Practices

```jsx
// ❌ WRONG: Flat card without contrast or using hardcoded colors
<div className="bg-white border-none p-6">
  <h3>Metrics</h3>
</div>

// ✅ CORRECT: Semantic Card that automatically lifts off the shaded canvas in both themes
<Card className="p-6 shadow-xs border border-border bg-card">
  <h3 className="text-base font-semibold text-foreground">Metrics</h3>
</Card>
```

---

## 3. The 3-Column Dashboard Layout Architecture

The application layout is built into `src/shared/layout/DashboardShell.jsx`.

### Structure

1. **Column 1: Left Navigation Sidebar**
   - Fixed to the screen height with independent vertical scrolling (`h-full overflow-y-auto column-scroll-contain`).
   - Uses `bg-sidebar` and `border-r border-sidebar-border`.
   - On screens `< 768px`, it collapses into a mobile slide-over drawer powered by shadcn `Sheet`.

2. **Column 2: Main Workspace Canvas (`<Outlet />`)**
   - Independently scrollable canvas (`bg-background column-scroll-contain`).
   - **Auto-expanding layout**: When Column 3 (AI Copilot) is closed, Column 2 smoothly and responsively expands to fill the entire remaining screen width (2-column layout).
   - Includes automatic route/tab entrance glide (`animate-fade-rise`).

3. **Column 3: AI Copilot Chat Panel (`AiChatPanel.jsx`)**
   - **Fixed to Screen Height**: The panel itself is completely rigid (`h-full overflow-hidden`).
   - **Isolated Chat Scrolling**: The header (title, controls) and footer (prompt input) are pinned in place (`shrink-0`). **Only the chat messages list (`overflow-y-auto min-h-0`) can be scrolled**.
   - **Default Visible**: Defaults to open on initial load.
   - **Silky-Smooth Motion Choreography**:
     - **No Sudden DOM Unmounting**: Column 3 remains in the layout tree and uses continuous CSS width interpolation (`transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]`) between `w-0` and `w-80 xl:w-96`.
     - **Content Sliding Parallax**: The inner panel content smoothly translates (`translate-x-6` to `translate-x-0`) while fading in (`opacity-0` to `opacity-100`), preventing text wrapping or squishing while gliding into place.
     - **Automatic Canvas Reflow**: Column 2 (`main`) smoothly and dynamically adapts its width to accommodate the panel with zero layout popping.
   - **User Toggle**:
     - When the 3rd column is **closed**: A sleek, pill-shaped **Floating Action Button (FAB)** floats in the bottom-right corner (`fixed bottom-6 right-6 z-50`) with an active pulse indicator.
     - When clicked: The FAB smoothly scales down, drops slightly, and fades out (`opacity-0 scale-75 translate-y-4`) as Column 3 glides open in perfect synchrony.
     - When Column 3 is closed via the `X` button: The column slides shut into the right edge, and the FAB smoothly scales and glides up into position (`opacity-100 scale-100 translate-y-0`).
   - On screens `< 1024px`, the copilot automatically transitions to a slide-over `Sheet` drawer.

---

## 4. Global Professional Smoothness & Motion System

Drawing directly from the interaction standards of **Linear**, **Vercel (Geist)**, and **Stripe**, all interactive components must adhere to the global motion system:

### 1. Human-Centric Easing Curves
We avoid linear or bouncy, cartoonish defaults. We use custom ease-out curves that launch with energy and settle softly and confidently:
- CSS Variable: `--ease-spring: cubic-bezier(0.16, 1, 0.3, 1)`
- Smooth curve: `--ease-smooth: cubic-bezier(0.4, 0, 0.2, 1)`

### 2. Tactile Active Press Feedback
Buttons, dropdown items, sidebar links, and clickable chips must provide immediate physical feedback when pressed:
```jsx
// Applied via class or custom utility:
className="transition-all duration-150 ease-out active:scale-[0.98] cursor-pointer"
```

### 3. Fluid Route & Tab Gliding
When switching routes or tabs, content must enter smoothly:
```jsx
<div key={location.pathname} className="max-w-7xl mx-auto animate-fade-rise">
  <Outlet />
</div>
```
`animate-fade-rise` provides a subtle 240ms 6px lift with an opacity fade.

### 4. Interactive Card Lift (`.card-hover-lift`)
All clickable dashboard cards and quick-launch links should use `.card-hover-lift`:
```jsx
<Card className="card-hover-lift border-border bg-card cursor-pointer">
  {/* Soft 2px elevation with gentle shadow bloom on hover */}
</Card>
```

### 5. Column Scroll Containment (`.column-scroll-contain`)
All 3 columns use `.column-scroll-contain` (`overscroll-behavior: contain; scroll-behavior: smooth;`). This isolates scrolling physics so scrolling to the end of a data table or chat history never causes rubber-banding or chaining into neighboring columns.

### 6. Accessibility (Reduced Motion)
All animations and transitions automatically collapse to instantaneous transitions under `@media (prefers-reduced-motion: reduce)`.

---

## 5. Professional Custom Scrollbars

EduFlow features a unified, minimalist custom scrollbar configured in `src/index.css`:
- **Profile**: Slim 6px width/height.
- **Track**: Completely transparent so underlying cards and canvas show through seamlessly.
- **Thumb**: Rounded pill thumb (`border-radius: 9999px`) with subtle neutral opacity (`18%`), brightening on hover (`32%`).
- **Theme-Adaptive**: Automatically adapts to Light mode (`oklch(0 0 0 / 18%)`) and Dark mode (`oklch(1 0 0 / 18%)`).
- **Utility Class**: Use `.scrollbar-none` when you need an area to remain scrollable without displaying a scrollbar.

---

## 6. Automatic Fluid Typography (Zero-Breakpoint Responsive Text)

In EduFlow, **developers never have to manually write breakpoint font sizes** (e.g. `text-lg sm:text-xl md:text-2xl lg:text-3xl`).

The entire typography scale adapts **automatically and continuously** to the user's viewport width using native CSS `clamp()` formulas:

### How It Works Under the Hood
1. **Root Scaling**: The root `html` font-size baseline scales fluidly from `14px` on mobile screens (`360px`) up to `16px` on full desktop displays (`clamp(14px, 0.85rem + 0.3vw, 16px)`). Because all `rem` values derive from this root, all typography naturally scales with screen size while fully preserving accessibility and browser zoom preferences.
2. **Fluid Tailwind Scale**: Tailwind's text tokens (`--text-xs` through `--text-4xl`) are bound to fluid `clamp()` ranges.

### Developer Usage: Simple & Clean
Just use standard Tailwind typography classes. You never need to write manual media query variants for text:

```jsx
// ✅ DO THIS: Write clean, standard classes — the typography scale handles responsiveness automatically!
<h1 className="text-3xl font-bold tracking-tight text-foreground">Student Portal</h1>
<h2 className="text-xl font-semibold text-foreground">Upcoming Milestones</h2>
<p className="text-sm text-muted-foreground">Track your project deadlines.</p>

// ❌ AVOID THIS: Redundant, messy breakpoint soup is unnecessary!
<h1 className="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-bold">Student Portal</h1>
```

### Scale Reference

| Class | Mobile (360px) | Desktop (1440px+) | Typical Semantic Role |
| :--- | :--- | :--- | :--- |
| `text-xs` | `0.70rem` (~10.5px) | `0.75rem` (12px) | Status badges, timestamps, table hints |
| `text-sm` | `0.80rem` (~12px) | `0.875rem` (14px) | Table cell text, card descriptions, navigation |
| `text-base` | `0.90rem` (~13.5px) | `1.00rem` (16px) | Body copy, card titles, form inputs |
| `text-lg` | `1.00rem` (~15px) | `1.125rem` (18px) | Section subtitles, module card headers |
| `text-xl` | `1.10rem` (~16.5px) | `1.25rem` (20px) | Section headings, dialog titles |
| `text-2xl` | `1.25rem` (~18.5px) | `1.50rem` (24px) | Metric numbers, major section titles |
| `text-3xl` | `1.50rem` (~22.5px) | `1.875rem` (30px) | Main dashboard page headers |
| `text-4xl` | `1.75rem` (~26px) | `2.25rem` (36px) | Hero titles, landing page banners |

---

## 7. Theme System & Dark/Black Mode

The app supports **Light**, **Dark / Black** (deep OLED dark mode), and **System**:

- **How it works**: The `ThemeProvider` sets or removes the `.dark` class on `<html>`. All semantic tokens in `src/index.css` adapt instantaneously.
- **Theme State Hook**:
  ```jsx
  import { useTheme } from '@/shared/theme/useTheme'

  function Example() {
    const { theme, setTheme, resolvedTheme } = useTheme()
    return <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>Toggle</button>
  }
  ```
- **Designing for Both Themes**: Because you use semantic classes (`bg-card`, `border-border`, `text-foreground`), components will look balanced in both themes automatically. If you ever need theme-specific styling, use Tailwind's `dark:` modifier (e.g. `dark:bg-emerald-950/40 dark:text-emerald-400`).

---

## 8. Adding & Using shadcn Primitives

Whenever you need a new primitive (e.g., `dialog`, `tabs`, `accordion`, `popover`, `select`, `tooltip`, `progress`):

```bash
npx shadcn@latest add <component-name>
```

**Import convention**: Always import from `@/components/ui/<component>`:
```jsx
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
```

### Merging Class Names with `cn()`
Always use `cn()` from `@/lib/utils` when applying conditional classes:
```jsx
import { cn } from '@/lib/utils'

<div className={cn(
  "p-4 rounded-xl border transition-all duration-150",
  isActive ? "bg-card border-primary text-primary shadow-xs" : "bg-muted/40 border-transparent text-muted-foreground"
)}>
  {children}
</div>
```

---

## 9. Using the shadcn MCP Server with AI

The repository is pre-configured with the **shadcn Model Context Protocol (MCP) server** in `.vscode/mcp.json` and `.mcp.json`.

AI coding assistants (Antigravity, Copilot, Cursor, Claude Code) can search and install shadcn components automatically. You can prompt:
- *"Add the dialog and progress components from shadcn to this project."*
- *"Search shadcn for a calendar component and install it."*
- *"Build a rubric evaluation modal using shadcn Dialog, Card, and Slider."*

---

---

## 10. Global Notification System & Toast Architecture

EduFlow features a unified notification ecosystem built with **shadcn Popover** and **Sonner**:

### 1. Notification Center Dropdown (`NotificationDropdown.jsx`)
Located in `TopNavbar.jsx` beside the theme toggle:
- **Badge Indicator**: Displays a pulsing indicator and live unread counter whenever unread notifications are present.
- **Filter Tabs**: Toggle smoothly between **All** and **Unread** notifications.
- **Notification Cards**: Include contextual category icons (calendar/milestones, supervisor feedback, AI methodology scans, and system maintenance), timestamp, unread indicator dot, and hover-to-dismiss actions.
- **Bulk Actions**: One-click **Mark all read** (updates status and fires a confirmation toast) and **Clear all**.
- **Interactive Sandbox**: Includes a **Simulate New Notification** button for immediate testing of both the dropdown and global toasts.

### 2. Global Notification Toast (`showToast` & Sonner)
The toast system is mounted globally in `App.jsx` via `<Toaster />` and automatically syncs with the active theme (`light` or `dark`).

#### Design Rules for Black & White Themes:
- **Light Theme**: Crisp pure white card surface (`bg-card`), high-contrast dark text (`text-card-foreground`), subtle border (`border-border`), and deep diffused shadow.
- **Dark Theme**: Pitch-black / charcoal elevated card (`bg-card`), luminous 12% border (`border-border`), stark white typography, and subtle glowing icon badges.
- **Micro-Interactions**: Smooth spring enter/exit, swipe-to-dismiss, tactile action buttons, and automatic theme adaptation without jarring neon colors.

#### Developer Usage: Simple & Consistent
Import `showToast` from `@/shared/utils/toast.jsx`:

```jsx
import { showToast } from '@/shared/utils/toast.jsx'

// ✅ Success (e.g. after form submission, project save, grade publish)
showToast.success('Project Saved', {
  description: 'Your milestone changes have been safely synchronized.'
})

// ✅ Error (e.g. validation failure, network disconnect)
showToast.error('Submission Failed', {
  description: 'Unable to reach the server. Please check your connection.'
})

// ✅ Info / Neutral (e.g. navigation hint, status notice)
showToast.info('Defense Schedule Updated', {
  description: 'Review the new time slot assigned to your group.'
})

// ✅ AI Copilot Notification
showToast.ai('AI Analysis Ready', {
  description: 'Methodology citation scan finished with 0 discrepancies.'
})

// ✅ Async Promises (automatically handles loading, success, and error)
showToast.promise(apiCall(), {
  loading: 'Uploading file...',
  success: 'File uploaded successfully!',
  error: 'Upload failed. Please try again.'
})
```

---

---

## 11. Global Popup & Modal Suite (`Dialog`, `AlertDialog`, `useConfirm`)

Modals in EduFlow are designed for zero friction and strict visual harmony with Black & White themes:

### 1. General Modals (`Dialog`)
Used for custom forms, detail inspectors, evaluation rubrics, and settings:

```jsx
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

<Dialog>
  <DialogTrigger asChild>
    <Button size="sm">Open Rubric</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Rubric Evaluation</DialogTitle>
      <DialogDescription>Score student criteria according to research guidelines.</DialogDescription>
    </DialogHeader>
    {/* Form / Content here */}
    <DialogFooter>
      <Button variant="outline">Cancel</Button>
      <Button>Save Scores</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### 2. High-Stakes Confirmation Popups (`AlertDialog`)
For destructive or irreversible actions with explicit confirmation:

```jsx
import {
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogAction,
  AlertDialogCancel,
} from '@/components/ui/alert-dialog'
```

### 3. Global 1-Line Imperative Confirmation Hook (`useConfirm`)
**Developers never have to write local `const [open, setOpen] = useState(false)` boilerplate for confirmations!**
Simply call `useConfirm()` anywhere in the application:

```jsx
import { useConfirm } from '@/shared/utils/useConfirm.js'
import { showToast } from '@/shared/utils/toast.jsx'

function DeleteMilestoneButton({ milestoneId }) {
  const confirm = useConfirm()

  const handleDelete = async () => {
    // Returns a Promise that resolves to true or false:
    const confirmed = await confirm({
      title: 'Delete Milestone?',
      description: 'This will permanently delete the milestone and all submitted student artifacts.',
      confirmText: 'Delete Permanently',
      cancelText: 'Cancel',
      tone: 'destructive', // 'destructive' | 'default'
    })

    if (confirmed) {
      await apiDeleteMilestone(milestoneId)
      showToast.success('Milestone deleted')
    }
  }

  return (
    <Button variant="destructive" size="sm" onClick={handleDelete}>
      Delete
    </Button>
  )
}
```

---

## 12. Global Command Palette (`Ctrl+K` / `Cmd+K`)

EduFlow features a global Spotlight Command Menu accessible anywhere:
- **Shortcut**: `Ctrl+K` (Windows/Linux) or `Cmd+K` (macOS).
- **Navbar Search**: Clicking the top search bar immediately opens the command palette.
- **Capabilities**:
  - Direct portal jump (Student, Instructor, Admin, Planning, Performance, AI Tutor, Security).
  - Instant Theme toggling (Light vs. Dark / Black).
  - Triggering live alerts & AI Copilot.

---

## 13. Zero-Boilerplate Loading & Intelligent Auto-Skeleton System

**Developers should never have to manually craft repetitive skeleton boxes for everyday components.**
EduFlow provides automatic skeleton rendering with full override capabilities:

### 1. Zero-Boilerplate `<Card loading={isLoading}>`
Simply pass `loading={isLoading}` to any `<Card>`:

```jsx
// ✅ DO THIS: 1 prop, zero boilerplate!
<Card loading={isLoading}>
  <CardHeader>
    <CardTitle>Milestone 2 Overview</CardTitle>
  </CardHeader>
  <CardContent>
    <p>Loaded project content...</p>
  </CardContent>
</Card>

// Need a custom skeleton design for a specialized card? Just pass loadingFallback:
<Card loading={isLoading} loadingFallback={<MyCustomChartSkeleton />}>
  {/* Component content */}
</Card>
```

### 2. Zero-Boilerplate `<StatCard loading={isLoading}>`
```jsx
<StatCard
  loading={isLoading}
  icon={GraduationCap}
  label="Total Submissions"
  value={48}
  trend="+12% from last week"
/>
```

### 3. Universal `<LoadingState>` Wrapper
Wrap any data table, card grid, list, or text area with `<LoadingState>`:

```jsx
import LoadingState from '@/shared/components/LoadingState.jsx'

// Renders an automatic multi-row table skeleton:
<LoadingState loading={isLoading} variant="table">
  <StudentSubmissionsTable data={submissions} />
</LoadingState>

// Renders a grid of 3 card skeletons:
<LoadingState loading={isLoading} variant="card" count={3} className="grid-cols-3">
  {projects.map(p => <ProjectCard key={p.id} project={p} />)}
</LoadingState>

// Fully overridable with custom fallback:
<LoadingState loading={isLoading} fallback={<SpecialGraphicSkeleton />}>
  <ComplexDashboardWidget />
</LoadingState>
```

---

## 14. Essential Dashboard Primitives Reference

| Component | Import Path | Primary Use Case |
| :--- | :--- | :--- |
| **`Tabs`** | `@/components/ui/tabs` | Section switching (`TabsList`, `TabsTrigger`, `TabsContent`) |
| **`Select`** | `@/components/ui/select` | Styled dropdown pickers (`SelectTrigger`, `SelectContent`, `SelectItem`) |
| **`Checkbox`** | `@/components/ui/checkbox` | Batch table selection & rubric checklists |
| **`Progress`** | `@/components/ui/progress` | Milestone completion percentage bars (`<Progress value={75} />`) |
| **`Tooltip`** | `@/components/ui/tooltip` | Sleek hover micro-labels (`<Tooltip><TooltipTrigger>...<TooltipContent>...`) |
| **`Textarea`** | `@/components/ui/textarea` | Styled multi-line input for supervisor feedback & abstracts |
| **`Breadcrumb`** | `@/components/ui/breadcrumb` | Hierarchical navigation paths (`Home > Planning > Milestones`) |
| **`EmptyState`** | `@/shared/components/EmptyState` | Polished placeholder when tables/lists have 0 records |

---

## 15. Pre-commit Verification Checklist

Before pushing code or opening a pull request, you MUST verify:

```bash
# 1. Lint verification (must return 0 errors and 0 warnings)
npm run lint

# 2. Production build verification (must compile cleanly)
npm run build
```

Verify these UX criteria manually:
- [ ] Cards have visible contrast and float above the shaded canvas in both Light and Dark themes.
- [ ] Interactive elements feature tactile active press (`active:scale-[0.98]`).
- [ ] Layout transitions fluidly when the AI Copilot is opened/closed.
- [ ] Scrollbars are slim and styled cleanly without default OS scrollbar artifacts.
- [ ] Notifications dropdown and toasts adapt cleanly to Black & White themes with crisp typography.
- [ ] Popups, Dialogs, and Command Palette (`Ctrl+K`) render centered with smooth backdrop blur.
- [ ] Skeletons shimmer smoothly without causing layout shifts when loaded.
