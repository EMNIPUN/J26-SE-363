# EduFlow Frontend

The unified frontend for the **EduFlow** capstone learning platform, integrating project requirements planning, student performance analytics, an adaptive AI tutor, and automated security assessment.

---

## Tech Stack

- **Framework**: React 19 + Vite 8
- **UI & Styling**: [Tailwind CSS v4](https://tailwindcss.com/) + [shadcn/ui](https://ui.shadcn.com/)
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

## 🎨 UI & Theming Guidelines (Important)

> [!IMPORTANT]
> **No Custom CSS Files**: Do not create or write custom `.css` files. All styling must use **Tailwind CSS utility classes** and **shadcn/ui** components.

- **Theme Consistency**: Always use semantic design tokens (`bg-card`, `text-foreground`, `bg-muted`, `text-muted-foreground`, `border-border`, `bg-primary`, `text-destructive`). Never hardcode hex color values.
- **Responsive Layout**: The app uses `DashboardShell.jsx` with a responsive desktop sidebar and a mobile drawer (`Sheet`) for mobile screens.
- **Adding New Components**: Use `npx shadcn@latest add <component>` to scaffold new primitives directly into `src/components/ui/`.
- **MCP Server**: The repository includes MCP configuration (`.vscode/mcp.json` and `.mcp.json`) allowing AI assistants to browse and install registry components seamlessly.

📖 **For the complete guide on component patterns, color tables, and examples, see:**  
👉 **[UI & Theming Guidelines](docs/UI_GUIDELINES.md)**

---

## Project Structure

```
src/
├── components/ui/       # shadcn/ui primitives (button, card, table, sheet, etc.)
├── shared/
│   ├── components/      # Project-specific shared wrappers (StatCard, PageHeader, Badge, etc.)
│   ├── layout/          # DashboardShell, TopNavbar, Sidebar
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
└── index.css            # Tailwind import & semantic CSS theme variables
```

