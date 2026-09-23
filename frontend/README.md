# MENTOR Frontend

The unified frontend for **MENTOR** (**M**ulti-agent **E**ngineering **N**etwork for **T**ask **O**rchestration & **R**eview).

> **MENTOR is a multi-agent engineering system that orchestrates software project tasks, evaluates student contributions, provides adaptive learning support, and performs security review.**

---

## Tech Stack

- **Framework**: React 19 + Vite 8
- **UI & Styling**: [Tailwind CSS v4](https://tailwindcss.com/) + [shadcn/ui](https://ui.shadcn.com/)
- **Motion System**: Physics-informed easing (`cubic-bezier(0.16, 1, 0.3, 1)`) + tactile micro-interactions
- **Icons**: [Lucide React](https://lucide.dev/)
- **Routing**: React Router v7
- **AI Tooling**: shadcn Model Context Protocol (MCP) Server

---

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Run local development server
npm run dev

# 3. Lint and code verification
npm run lint

# 4. Production build
npm run build
```

---

## 🎨 UI, Theming & Motion Standards (Must Read)

> [!IMPORTANT]
> **Zero-Custom-CSS Policy**: Do NOT create or write custom `.css` files. All UI development uses **Tailwind CSS v4 utility classes** and **shadcn/ui** components.

Every developer contributing to this codebase must adhere to the following standards:

1. **Surface Background Hierarchy**:
   - The workspace canvas (Column 2) is **shaded/recessed** (`bg-background`: soft slate-50 in Light mode, deep matte black in Dark mode).
   - Cards, data tables, and metrics (`bg-card`) are **elevated floating plates** with `shadow-xs border border-border`. Never place identical white cards on identical white backgrounds.
   - The cockpit frame (Sidebar, TopNavbar, AI Copilot) uses dedicated frame surface tokens (`bg-sidebar`).
2. **3-Column Dashboard & Collapsible AI Copilot**:
   - Column 1: Left Navigation Sidebar (fixed to screen).
   - Column 2: Center Workspace Canvas (independently scrollable, auto-expanding layout).
   - Column 3: AI Copilot Chat Panel (fixed to screen, persistent in `localStorage`, collapsible via toggle or `X` button).
   - **Isolated Chat Scroll**: Only the chat messages list can scroll; the AI panel header and footer input are pinned in place.
3. **Global Motion System (Linear / Vercel Standards)**:
   - Signature easing curve: `--ease-spring: cubic-bezier(0.16, 1, 0.3, 1)`.
   - Tactile active press on interactive controls: `active:scale-[0.98]` and `duration-150 ease-out`.
   - Subtle fluid tab entrance: `animate-fade-rise` on page routes.
   - Card hover lift: `.card-hover-lift` on clickable cards.
   - Column scroll containment: `.column-scroll-contain` to isolate scroll physics.
4. **Automatic Fluid Typography**:
   - Typography scales continuously with screen width using CSS `clamp()` (`--text-xs` through `--text-4xl` and root `html`). Developers simply write standard classes (e.g. `text-2xl`, `text-sm`) without needing manual responsive media query breakpoints.
5. **Professional Custom Scrollbars**:
   - Slim 6px profile, transparent track, theme-adaptive pill thumb with hover states.
6. **Theme Support**:
   - Native support for **Light**, **Dark / Black** (OLED deep-black), and **System** themes with `<ThemeToggle />` and `useTheme()`.
7. **MCP Server Integration**:
   - Configured in `.vscode/mcp.json` and `.mcp.json` for AI assistants (Antigravity, Copilot, Cursor) to search and install shadcn components automatically.

📖 **For detailed code examples, component templates, and color tables, see:**  
👉 **[Full UI & Theming Guidelines](docs/UI_GUIDELINES.md)**

---

## 🌐 API Calling & Data Synchronization Standards (Must Read)

> [!IMPORTANT]
> **Zero Hardcoded URLs Policy**: Never write hardcoded URLs or `fetch()` directly in React components.
> All API communication follows a strict 4-layer architecture:
> **Vite/Vercel Proxy (`/api`) → Central `apiClient` → Domain Services → TanStack Query (`useQuery` / `useMutation`)**.

- **In-Memory Token Management**: Access tokens live in memory (`tokenManager.js`), preventing XSS token harvesting.
- **Single Source of Truth**: All endpoint paths are defined in `src/shared/api/endpoints.js`.
- **Automatic Caching & Deduplication**: Managed by `@tanstack/react-query`.

📖 **For the complete developer tutorial and copy-paste examples, see:**  
👉 **[API Architecture Guidelines](docs/API_GUIDELINES.md)**

---

## Project Structure

```
src/
├── components/ui/       # Raw shadcn/ui primitives (button, card, table, sheet, etc.)
├── shared/
│   ├── components/      # Project-specific shared wrappers (StatCard, PageHeader, Badge, etc.)
│   ├── layout/          # DashboardShell (3-column layout), TopNavbar, Sidebar
│   ├── theme/           # ThemeProvider, useTheme, context
│   ├── auth/            # AuthContext, mock credentials, route guards
│   └── pages/           # Login, NotFound, DashboardHome
├── modules/             # Capstone feature areas
│   ├── planning/        # Requirements engineering & estimation
│   ├── performance/     # Student progress & instructor assessments
│   ├── tutor/           # Adaptive AI tutoring
│   ├── security/        # AEGIS security reviews
│   └── admin/           # Platform user & settings management
├── lib/
│   └── utils.js         # cn() utility helper (clsx + tailwind-merge)
└── index.css            # Tailwind import, semantic CSS tokens, motion & scrollbar styles
```
