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
| **Workspace Canvas** | Recessed floor | Cool Slate-50 tint (`oklch(0.976 0.003 260)`) | Deep Matte Black (`oklch(0.06 0 0)`) | `bg-background` |
| **Cards & Panels** | Elevated floating plate | Crisp Pure White (`oklch(1 0 0)`) | Elevated Dark Surface (`oklch(0.135 0 0)`) | `bg-card` + `shadow-xs border border-border` |
| **Cockpit Frame** | Sidebar, Navbar, AI Panel | Framing Pure White (`oklch(1 0 0)`) | Framing Dark Surface (`oklch(0.095 0 0)`) | `bg-sidebar` + `border-sidebar-border` |
| **Borders & Dividers** | Structural separation | Soft Slate Border (`oklch(0.91 0.003 260)`) | Luminous 12% Dark Border (`oklch(1 0 0 / 12%)`) | `border-border` |
| **Muted Surfaces** | Secondary tags, badges | Subtle Cool Tint (`oklch(0.95 0.003 260)`) | Subtle Dark Tint (`oklch(0.16 0 0)`) | `bg-muted` / `text-muted-foreground` |

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
   - **Persistent State**: The open/closed state is automatically saved in `localStorage` under the key `'eduflow-ai-panel-open'`.
   - **User Toggle**: Users can toggle or close the panel via the **AI Copilot** button in `TopNavbar` or the `X` button on the panel.
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

## 6. Theme System & Dark/Black Mode

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

## 7. Adding & Using shadcn Primitives

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

## 8. Using the shadcn MCP Server with AI

The repository is pre-configured with the **shadcn Model Context Protocol (MCP) server** in `.vscode/mcp.json` and `.mcp.json`.

AI coding assistants (Antigravity, Copilot, Cursor, Claude Code) can search and install shadcn components automatically. You can prompt:
- *"Add the dialog and progress components from shadcn to this project."*
- *"Search shadcn for a calendar component and install it."*
- *"Build a rubric evaluation modal using shadcn Dialog, Card, and Slider."*

---

## 9. Pre-commit Verification Checklist

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
