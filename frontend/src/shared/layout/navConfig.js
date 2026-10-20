import {
  LayoutDashboard,
  BookOpen,
  BarChart3,
  ShieldCheck,
  Bot,
  Users,
  Settings,
  MessageCircle,
  Route,
  Code2,
  ClipboardCheck,
  ChartColumn,
  FolderKanban,
} from "lucide-react";

// One nav tree per role. `to` on a parent makes the whole group a link too
// (used for single-page sections); `children` renders an expandable list.
export function getNavForRole(role, teamCode = "J26-SE-363") {
  const t = (path) => `/teams/${teamCode}${path}`;

  if (role === "student") {
    return [
      { label: "Overview", icon: LayoutDashboard, to: t("/app") },
      { label: "Team", icon: Users, to: t("/members") },
      {
        label: "Project Planning",
        icon: BookOpen,
        color: "#2563eb",
        children: [
          { label: 'Dashboard', to: t('/planning/dashboard') },
          { label: 'SRS Quality', to: t('/planning/requirements/srs-quality') },
          { label: 'Decomposition', to: t('/planning/requirements/decomposition') },
          { label: 'Effort Estimation', to: t('/planning/requirements/estimation') },
          { label: 'Sprint Management', to: t('/planning/sprint-management') },
        ],
      },
      {
        label: "Performance",
        icon: BarChart3,
        color: '#2563eb',
        to: t('/performance/my-assessment'),
      },
      {
        label: "Project Security",
        icon: ShieldCheck,
        color: '#2563eb',
        children: [
          { label: "Dashboard", to: t("/security/dashboard") },
          { label: "Scan Report", to: t("/security/scan-report") },
          { label: "Remediation", to: t("/security/remediation") },
        ],
      },
      {
        label: 'AI Tutor',
        icon: Bot,
        color: '#5146C7',
        children: [
          { label: 'Tutor Chat', icon: MessageCircle, to: t('/tutor/chat') },
          { label: 'Sprint Guidance', icon: Route, to: t('/tutor/guidance') },
          { label: 'Practice Exercises', icon: Code2, to: t('/tutor/practice') },
          { label: 'Assessments', icon: ClipboardCheck, to: t('/tutor/assessments') },
          { label: 'Progress & Results', icon: ChartColumn, to: t('/tutor/progress') },
        ],
      },
    ]
  }

  // Lecturer areas without a page yet (chat workspace, sprint monitoring,
  // learning analytics, settings) are left out rather than linked to nothing.
  if (role === "instructor") {
    return [
      { label: "Dashboard", icon: LayoutDashboard, to: t("/app") },
      { label: "Team", icon: Users, to: t("/members") },
      { label: "Projects", icon: FolderKanban, to: t("/planning/instructor/projects") },
      {
        label: "Groups & Students",
        icon: Users,
        children: [
          { label: "Groups", to: t("/planning/instructor/groups") },
        ],
      },
      {
        label: "Requirements & Planning",
        icon: BookOpen,
        children: [
          { label: "Planning overview", to: t("/planning/instructor/dashboard") },
          { label: "Planning decisions", to: t("/planning/instructor/arbitration") },
        ],
      },
      {
        label: "Assessment",
        icon: ClipboardCheck,
        children: [
          { label: "Team assessment", to: t("/performance/assessment") },
          { label: "Method and weights", to: t("/performance/method") },
        ],
      },
      {
        label: "Security & Quality",
        icon: ShieldCheck,
        children: [
          { label: "Overview", to: t("/security/dashboard") },
          { label: "Scan report", to: t("/security/scan-report") },
          { label: "Remediation", to: t("/security/remediation") },
        ],
      },
    ];
  }

  // admin
  return [
    { label: "Overview", icon: LayoutDashboard, to: t("/app") },
    { label: "Users", icon: Users, to: "/admin/users" },
    { label: "Settings", icon: Settings, to: "/admin/settings" },
    {
      label: "Project Planning",
      icon: BookOpen,
      color: "#2563eb",
      to: t("/planning/dashboard"),
    },
    {
      label: "Performance",
      icon: BarChart3,
      color: '#2563eb',
      to: t('/performance/assessment'),
    },
    { label: 'Security', icon: ShieldCheck, color: '#2563eb', to: t('/security/dashboard') },
  ]
}
