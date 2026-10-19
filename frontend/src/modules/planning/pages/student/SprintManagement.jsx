import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ListTodo,
  LayoutGrid,
  BarChart3,
  Layers,
  AlertTriangle,
  Users,
  Clock,
  CheckCircle2,
  Circle,
  Search,
  ChevronDown,
  Bookmark,
  SquareCheck,
  TrendingDown,
  Gauge,
  GraduationCap,
  UserCheck,
  Sparkles,
  BookOpen,
  ArrowRight,
  ExternalLink,
  Send,
  RotateCcw,
  RefreshCw,
  ChevronRight,
  Calendar,
  ArrowUpRight,
  Check,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  Legend,
} from "recharts";
import Card from "../../../../shared/components/Card.jsx";
import Badge from "../../../../shared/components/Badge.jsx";
import Button from "../../../../shared/components/Button.jsx";
import StatCard from "../../../../shared/components/StatCard.jsx";
import EmptyState from "../../../../shared/components/EmptyState.jsx";
import AvatarComp from "../../../../shared/components/Avatar.jsx";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import WorkflowStepper from "../../components/WorkflowStepper.jsx";
import DartButton from "../../components/DartButton.jsx";
import SupervisorConsultationModal from "../../components/SupervisorConsultationModal.jsx";
import { COURSE_INFO } from "../../data/lmsAcademicData.js";
import { usePlanningData } from "../../context/usePlanningData.js";
import { useSprintTasks, useUpdateSprintTask } from "../../hooks/useSprint.js";
import { useStories } from "../../hooks/useDecomposition.js";
import { useEstimates } from "../../hooks/useEstimates.js";
import { jiraService } from "../../services/jiraService.js";
import { mapSprintTasks } from "../../adapters/sprint.js";
import { mapStoryRows } from "../../adapters/decomposition.js";
import {
  KANBAN_COLUMNS,
  BURNDOWN_SEED,
  VELOCITY_TREND,
} from "../../data/mockData.js";
import { showToast } from "@/shared/utils/toast.jsx";
import { useTeamPath } from "@/shared/hooks/useTeamPath.js";

const STATUS_TONE = {
  Todo: "neutral",
  "In Progress": "primary",
  Blocked: "danger",
  Done: "success",
};

const COLUMN_META = {
  Todo: { icon: Circle, iconClass: "text-muted-foreground", bg: "bg-muted/30" },
  "In Progress": { icon: null, iconClass: "bg-primary", bg: "bg-primary/5" },
  Blocked: {
    icon: AlertTriangle,
    iconClass: "text-destructive",
    bg: "bg-destructive/5",
  },
  Done: {
    icon: CheckCircle2,
    iconClass: "text-emerald-500",
    bg: "bg-emerald-500/5",
  },
};

const EPIC_CHIP_COLORS = [
  "bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-400",
  "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400",
  "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400",
  "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400",
  "bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400",
  "bg-cyan-100 text-cyan-700 dark:bg-cyan-950/40 dark:text-cyan-400",
];

function epicChipClass(reqId, requirements) {
  const idx = requirements.findIndex((r) => r.id === reqId);
  return EPIC_CHIP_COLORS[(idx >= 0 ? idx : 0) % EPIC_CHIP_COLORS.length];
}

function memberFor(teamMembers, id) {
  return teamMembers.find((m) => m.id === id) || null;
}

function formatShortDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function IssueTypeIcon({ isStory, className = "h-3.5 w-3.5" }) {
  return isStory ? (
    <Bookmark className={`${className} text-emerald-500 shrink-0`} />
  ) : (
    <SquareCheck className={`${className} text-primary shrink-0`} />
  );
}

function tutorPromptForTask(task) {
  return `I'm working on the sprint task "${task.title}". What should I understand before I continue?`;
}

function IssueCard({ task, member, requirements, onOpen }) {
  const team = useTeamPath();
  return (
    <div
      draggable
      onDragStart={(e) => e.dataTransfer.setData("text/plain", task.id)}
      onClick={() => onOpen(task)}
      className={`p-2.5 rounded-md bg-card card-elevated border border-border/60 cursor-grab active:cursor-grabbing card-hover-lift ${
        task.status === "Blocked" ? "border-l-2 border-l-destructive" : ""
      }`}
    >
      <p className="text-xs text-foreground leading-snug mb-2">{task.title}</p>
      {task.requirementId && (
        <span
          className={`inline-block text-[10px] font-medium px-1.5 py-0.5 rounded mb-2 ${epicChipClass(task.requirementId, requirements)}`}
        >
          {task.requirementId}
        </span>
      )}
      {task.status === "Blocked" && task.blockedReason && (
        <p className="text-[10px] text-destructive mb-2 flex items-start gap-1">
          <AlertTriangle className="h-2.5 w-2.5 mt-0.5 shrink-0" />
          <span className="line-clamp-2">{task.blockedReason}</span>
        </p>
      )}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <IssueTypeIcon isStory={Boolean(task.storyId)} className="h-3 w-3" />
          <span className="text-[10px] font-medium text-muted-foreground">
            {task.id}
          </span>
          {task.status !== "Done" && (
            <Link
              to={team(
                `/tutor/chat?prompt=${encodeURIComponent(tutorPromptForTask(task))}`,
              )}
              onClick={(event) => event.stopPropagation()}
              className="text-[10px] font-medium text-primary hover:underline"
            >
              Ask tutor
            </Link>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-5 min-w-5 px-1 rounded-full bg-muted text-[10px] font-semibold text-foreground flex items-center justify-center">
            {task.points}
          </span>
          {member ? (
            <AvatarComp name={member.name} size={22} />
          ) : (
            <span className="h-[22px] w-[22px] rounded-full border border-dashed border-border shrink-0" />
          )}
        </div>
      </div>
    </div>
  );
}

function KanbanColumns({
  tasks,
  teamMembers,
  requirements,
  onOpen,
  onMove,
  onAssign,
  swimlaneAssigneeId,
  minHeight = 360,
}) {
  const [dragOverCol, setDragOverCol] = useState(null);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      {KANBAN_COLUMNS.map((col) => {
        const colTasks = tasks.filter((t) => t.status === col.key);
        const points = colTasks.reduce((sum, t) => sum + t.points, 0);
        const meta = COLUMN_META[col.key];
        const Icon = meta.icon;
        return (
          <div
            key={col.key}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOverCol(col.key);
            }}
            onDragLeave={() =>
              setDragOverCol((c) => (c === col.key ? null : c))
            }
            onDrop={(e) => {
              e.preventDefault();
              const taskId = e.dataTransfer.getData("text/plain");
              if (taskId) {
                onMove(taskId, col.key);
                if (swimlaneAssigneeId !== undefined)
                  onAssign(taskId, swimlaneAssigneeId);
              }
              setDragOverCol(null);
            }}
            style={{ minHeight }}
            className={`rounded-lg p-2.5 space-y-2 transition-all ${meta.bg} ${
              dragOverCol === col.key
                ? "ring-2 ring-primary ring-offset-1 ring-offset-background"
                : ""
            }`}
          >
            <div className="flex items-center justify-between px-0.5">
              <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                {Icon ? (
                  <Icon className={`h-3 w-3 shrink-0 ${meta.iconClass}`} />
                ) : (
                  <span
                    className={`h-1.5 w-1.5 rounded-full shrink-0 ${meta.iconClass}`}
                  />
                )}
                {col.label}{" "}
                <span className="text-muted-foreground font-normal">
                  {colTasks.length}
                </span>
              </span>
              <span className="text-[11px] text-muted-foreground">
                {points} SP
              </span>
            </div>
            {colTasks.map((task) => (
              <IssueCard
                key={task.id}
                task={task}
                member={memberFor(teamMembers, task.assigneeId)}
                requirements={requirements}
                onOpen={onOpen}
              />
            ))}
            {colTasks.length === 0 && (
              <div className="text-[11px] text-muted-foreground text-center py-4 border border-dashed border-border rounded-md">
                Drop here
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function IssueRow({
  id,
  title,
  requirementId,
  requirements,
  points,
  statusLabel,
  statusTone,
  member,
  isStory,
  jiraKey,
  jiraBaseUrl,
  onClick,
}) {
  return (
    <div
      onClick={onClick}
      className="flex items-center gap-3 px-3 py-2 hover:bg-muted/40 transition-colors cursor-pointer"
    >
      <IssueTypeIcon isStory={isStory} />
      <span className="text-xs text-muted-foreground font-medium w-20 shrink-0 truncate">
        {id}
      </span>
      <span className="text-sm text-foreground truncate flex-1 min-w-0">
        {title}
      </span>
      {jiraKey && (
        <a
          href={jiraBaseUrl ? `${jiraBaseUrl}/browse/${jiraKey}` : "#"}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-600 hover:underline dark:text-blue-400 shrink-0"
          title={`Open ${jiraKey} in Jira`}
        >
          <ExternalLink className="h-2.5 w-2.5" />
          {jiraKey}
        </a>
      )}
      {requirementId && (
        <span
          className={`hidden sm:inline-block text-[10px] font-medium px-1.5 py-0.5 rounded shrink-0 ${epicChipClass(requirementId, requirements)}`}
        >
          {requirementId}
        </span>
      )}
      {points != null && (
        <span className="h-5 min-w-5 px-1 rounded-full bg-muted text-[10px] font-semibold text-foreground flex items-center justify-center shrink-0">
          {points}
        </span>
      )}
      {statusLabel && (
        <Badge tone={statusTone} className="shrink-0">
          {statusLabel}
        </Badge>
      )}
      {member !== undefined &&
        (member ? (
          <AvatarComp name={member.name} size={24} />
        ) : (
          <span className="h-6 w-6 rounded-full border border-dashed border-border shrink-0" />
        ))}
    </div>
  );
}

function TaskDetailDialog({ task, onClose, teamMembers, onAssign, onMove }) {
  const team = useTeamPath();
  if (!task) return null;
  const member = memberFor(teamMembers, task.assigneeId);
  return (
    <Dialog open={!!task} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{task.id}</DialogTitle>
          <DialogDescription>{task.title}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-muted-foreground mb-1">Requirement</p>
              <p className="text-foreground font-medium">
                {task.requirementId || "—"}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Story points</p>
              <p className="text-foreground font-medium">{task.points} SP</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Status</p>
              <Select
                value={task.status}
                onValueChange={(v) => onMove(task.id, v)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {KANBAN_COLUMNS.map((c) => (
                    <SelectItem key={c.key} value={c.key}>
                      {c.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Assignee</p>
              <Select
                value={task.assigneeId || "unassigned"}
                onValueChange={(v) =>
                  onAssign(task.id, v === "unassigned" ? null : v)
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue>
                    {member ? member.name : "Unassigned"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="unassigned">Unassigned</SelectItem>
                  {teamMembers.map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {task.blockedReason && (
            <div className="p-3 rounded-lg border border-destructive/20 bg-destructive/5">
              <p className="text-xs font-semibold text-destructive mb-1">
                Blocked — dependency
              </p>
              <p className="text-xs text-muted-foreground">
                {task.blockedReason}
              </p>
            </div>
          )}

          <div>
            <p className="text-xs font-semibold text-muted-foreground mb-2">
              Team workload this sprint
            </p>
            <div className="space-y-2">
              {teamMembers.map((m) => (
                <div key={m.id} className="flex items-center gap-2">
                  <AvatarComp name={m.name} size={22} />
                  <span className="text-xs text-foreground w-24 truncate">
                    {m.name.split(" ")[0]}
                  </span>
                  <Progress
                    value={Math.min(100, (m.currentLoad / m.capacity) * 100)}
                    className={`h-1.5 flex-1 ${m.currentLoad > m.capacity ? "[&>div]:bg-destructive" : ""}`}
                  />
                  <span
                    className={`text-xs w-16 text-right shrink-0 ${m.currentLoad > m.capacity ? "text-destructive font-medium" : "text-muted-foreground"}`}
                  >
                    {m.currentLoad}/{m.capacity} SP
                  </span>
                </div>
              ))}
            </div>
          </div>

          {task.status !== "Done" && (
            <Button asChild variant="outline" size="sm" className="text-xs">
              <Link
                to={team(
                  `/tutor/chat?prompt=${encodeURIComponent(tutorPromptForTask(task))}`,
                )}
              >
                <Sparkles className="h-3.5 w-3.5" />
                Ask the tutor about this task
              </Link>
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function BoardToolbar({
  search,
  setSearch,
  groupBy,
  setGroupBy,
  teamMembers,
  filterAssignees,
  toggleAssignee,
  viewMode,
  setViewMode,
  onCompleteSprint,
}) {
  return (
    <div className="flex items-center gap-3 flex-wrap mb-4">
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search board"
          className="pl-8 h-8 text-xs w-[170px]"
        />
      </div>

      <div className="flex -space-x-2">
        {teamMembers.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => toggleAssignee(m.id)}
            title={m.name}
            className={`rounded-full cursor-pointer transition-transform outline-none ${filterAssignees.has(m.id) ? "ring-2 ring-primary z-10 scale-105" : "hover:scale-105"}`}
          >
            <AvatarComp name={m.name} size={28} className="ring-2 ring-card" />
          </button>
        ))}
      </div>

      <div className="ml-auto flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex items-center gap-1.5 px-2.5 h-8 rounded-md border border-border text-xs font-medium text-foreground hover:bg-accent transition-colors cursor-pointer"
            >
              Group: {groupBy === "assignee" ? "Assignee" : "None"}{" "}
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuRadioGroup value={groupBy} onValueChange={setGroupBy}>
              <DropdownMenuRadioItem value="none">None</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="assignee">
                Assignee
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        <div className="flex items-center rounded-md border border-border overflow-hidden">
          <button
            type="button"
            onClick={() => setViewMode("board")}
            title="Board view"
            className={`h-8 w-8 flex items-center justify-center cursor-pointer transition-colors ${viewMode === "board" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-accent"}`}
          >
            <LayoutGrid className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setViewMode("list")}
            title="List view"
            className={`h-8 w-8 flex items-center justify-center cursor-pointer transition-colors border-l border-border ${viewMode === "list" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-accent"}`}
          >
            <ListTodo className="h-3.5 w-3.5" />
          </button>
        </div>

        <Button size="sm" onClick={onCompleteSprint}>
          Complete sprint
        </Button>
      </div>
    </div>
  );
}

function BoardView({ onMove, onAssign }) {
  const { requirements, kanbanTasks, teamMembers, projectInfo } =
    usePlanningData();
  const [search, setSearch] = useState("");
  const [groupBy, setGroupBy] = useState("none");
  const [filterAssignees, setFilterAssignees] = useState(() => new Set());
  const [viewMode, setViewMode] = useState("board");
  const [openTask, setOpenTask] = useState(null);

  const toggleAssignee = (id) => {
    setFilterAssignees((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const totalPoints = kanbanTasks.reduce((s, t) => s + t.points, 0);
  const donePoints = kanbanTasks
    .filter((t) => t.status === "Done")
    .reduce((s, t) => s + t.points, 0);

  const filteredTasks = kanbanTasks.filter((t) => {
    const q = search.trim().toLowerCase();
    if (
      q &&
      !(t.title.toLowerCase().includes(q) || t.id.toLowerCase().includes(q))
    )
      return false;
    if (filterAssignees.size > 0 && !filterAssignees.has(t.assigneeId))
      return false;
    return true;
  });

  const membersWithLoad = teamMembers.map((m) => ({
    ...m,
    currentLoad: kanbanTasks
      .filter((t) => t.assigneeId === m.id && t.status !== "Done")
      .reduce((s, t) => s + t.points, 0),
  }));

  function handleCompleteSprint() {
    showToast.success("Sprint marked complete", {
      description: `${donePoints} of ${totalPoints} SP were completed in ${projectInfo.sprintName}.`,
    });
  }

  return (
    <>
      <BoardToolbar
        search={search}
        setSearch={setSearch}
        groupBy={groupBy}
        setGroupBy={setGroupBy}
        teamMembers={teamMembers}
        filterAssignees={filterAssignees}
        toggleAssignee={toggleAssignee}
        viewMode={viewMode}
        setViewMode={setViewMode}
        onCompleteSprint={handleCompleteSprint}
      />

      {viewMode === "list" ? (
        filteredTasks.length === 0 ? (
          <EmptyState
            title="No matching issues"
            description="Try a different search term or clear the assignee filter."
          />
        ) : (
          <Card className="p-0 overflow-hidden">
            <div className="divide-y divide-border">
              {filteredTasks.map((task) => (
                <IssueRow
                  key={task.id}
                  id={task.id}
                  title={task.title}
                  requirementId={task.requirementId}
                  requirements={requirements}
                  points={task.points}
                  statusLabel={task.status}
                  statusTone={STATUS_TONE[task.status]}
                  member={memberFor(teamMembers, task.assigneeId)}
                  isStory={Boolean(task.storyId)}
                  onClick={() => setOpenTask(task)}
                />
              ))}
            </div>
          </Card>
        )
      ) : groupBy === "assignee" ? (
        filteredTasks.length === 0 ? (
          <EmptyState
            title="No matching issues"
            description="Try a different search term or clear the assignee filter."
          />
        ) : (
          <div className="space-y-5">
            {[...teamMembers, { id: null, name: "Unassigned" }].map((m) => {
              const laneTasks = filteredTasks.filter(
                (t) => (t.assigneeId || null) === m.id,
              );
              if (laneTasks.length === 0) return null;
              return (
                <div key={m.id ?? "unassigned"}>
                  <div className="flex items-center gap-2 mb-2 px-0.5">
                    {m.id ? (
                      <AvatarComp name={m.name} size={22} />
                    ) : (
                      <span className="h-[22px] w-[22px] rounded-full bg-muted flex items-center justify-center shrink-0">
                        <Users className="h-3 w-3 text-muted-foreground" />
                      </span>
                    )}
                    <span className="text-xs font-semibold text-foreground">
                      {m.name}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {laneTasks.length} issue
                      {laneTasks.length === 1 ? "" : "s"}
                    </span>
                  </div>
                  <KanbanColumns
                    tasks={laneTasks}
                    teamMembers={teamMembers}
                    requirements={requirements}
                    onOpen={setOpenTask}
                    onMove={onMove}
                    onAssign={onAssign}
                    swimlaneAssigneeId={m.id}
                    minHeight={90}
                  />
                </div>
              );
            })}
          </div>
        )
      ) : (
        <KanbanColumns
          tasks={filteredTasks}
          teamMembers={teamMembers}
          requirements={requirements}
          onOpen={setOpenTask}
          onMove={onMove}
          onAssign={onAssign}
          minHeight={380}
        />
      )}

      <TaskDetailDialog
        task={openTask}
        onClose={() => setOpenTask(null)}
        teamMembers={membersWithLoad}
        onAssign={onAssign}
        onMove={onMove}
      />
    </>
  );
}

function BacklogView({ onRefreshed }) {
  const navigate = useNavigate();
  const team = useTeamPath();
  const {
    requirements,
    userStories,
    estimations,
    kanbanTasks,
    teamMembers,
    projectInfo,
  } = usePlanningData();
  const [openTask, setOpenTask] = useState(null);
  const [syncingBacklog, setSyncingBacklog] = useState(false);
  const [fetchingJira, setFetchingJira] = useState(false);
  const [resettingJira, setResettingJira] = useState(false);
  const [jiraStatus, setJiraStatus] = useState(null);

  useEffect(() => {
    jiraService
      .getStatus()
      .then((res) => setJiraStatus(res?.data ?? res))
      .catch(() => setJiraStatus({ configured: false }));
  }, []);

  // A story is eligible for the Sprint Creation Backlog if it has a saved estimate
  // (persisted in DB on StudentEffortEstimate or UserStory.student_story_points)
  const eligibleBacklogStories = [];
  for (const req of requirements) {
    for (const s of userStories[req.id] || []) {
      const pts =
        estimations[s.id]?.finalPoints ??
        estimations[s.id]?.studentPoints ??
        s.student_story_points ??
        null;

      if (req.status === "Passing" && pts != null) {
        eligibleBacklogStories.push({
          story: s,
          requirementId: req.id,
          points: pts,
        });
      }
    }
  }

  const eligibleTotalSP = eligibleBacklogStories.reduce(
    (sum, item) => sum + (Number(item.points) || 0),
    0,
  );

  async function handleSyncBacklog(force = false) {
    setSyncingBacklog(true);
    try {
      const storyRefs = eligibleBacklogStories.map(
        (item) => item.story.id || item.story.story_ref,
      );
      const storyPointsMap = {};
      eligibleBacklogStories.forEach((item) => {
        const ref = item.story.id || item.story.story_ref;
        if (item.points != null) {
          storyPointsMap[ref] = Number(item.points);
        }
      });

      const res = await jiraService.syncBacklog({
        force_resync: force,
        story_refs: storyRefs,
        story_points: storyPointsMap,
      });
      const data = res?.data ?? res;
      showToast.success("Backlog pushed to Jira!", {
        description: `Exported ${data?.stories_synced || 0} stories and ${data?.subtasks_created || 0} subtasks to Jira Backlog.`,
      });
      if (data?.status_warnings?.length) {
        showToast.error("Some new Jira items could not be moved to To Do", {
          description: data.status_warnings[0],
        });
      }
      jiraService
        .getStatus()
        .then((r) => setJiraStatus(r?.data ?? r))
        .catch(() => {});
    } catch (err) {
      showToast.error("Failed to push to Jira", {
        description:
          err?.response?.data?.detail ||
          err?.message ||
          "Please verify Jira credentials in backend/.env",
      });
    } finally {
      setSyncingBacklog(false);
    }
  }

  async function handleResetJiraLinks() {
    setResettingJira(true);
    try {
      const res = await jiraService.resetLinks();
      const data = res?.data ?? res;
      showToast.success("Jira links reset", {
        description:
          data?.message ||
          "Database Jira keys cleared. You can now re-push cleanly.",
      });
      jiraService
        .getStatus()
        .then((r) => setJiraStatus(r?.data ?? r))
        .catch(() => {});
    } catch (err) {
      showToast.error("Failed to reset Jira links", {
        description:
          err?.response?.data?.detail ||
          err?.message ||
          "Could not reset Jira links.",
      });
    } finally {
      setResettingJira(false);
    }
  }

  async function handleFetchJira() {
    setFetchingJira(true);
    try {
      const res = await jiraService.fetchLatest();
      const data = res?.data ?? res;
      await onRefreshed?.();
      showToast.success(
        data?.errors?.length
          ? "Jira refreshed with warnings"
          : "Jira data refreshed",
        {
          description: `${data?.stories_updated || 0} stories and ${data?.tasks_updated || 0} tasks updated locally.`,
        },
      );
    } catch (err) {
      showToast.error("Failed to refresh Jira data", {
        description:
          err?.response?.data?.detail ||
          err?.message ||
          "Please verify Jira credentials in backend/.env",
      });
    } finally {
      setFetchingJira(false);
    }
  }

  const totalPoints = kanbanTasks.reduce((s, t) => s + t.points, 0);

  const inSprintStoryIds = new Set(
    kanbanTasks.map((t) => t.storyId).filter(Boolean),
  );

  const membersWithLoad = teamMembers.map((m) => ({
    ...m,
    currentLoad: kanbanTasks
      .filter((t) => t.assigneeId === m.id && t.status !== "Done")
      .reduce((s, t) => s + t.points, 0),
  }));

  return (
    <div className="space-y-4">
      <Card className="hidden p-0 overflow-hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-border bg-muted/20 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-foreground">
              {projectInfo.sprintName}
            </h3>
            <span className="text-xs text-muted-foreground">
              {formatShortDate(projectInfo.sprintStartDate)} –{" "}
              {formatShortDate(projectInfo.sprintEndDate)}
            </span>
            <Badge tone="primary">{totalPoints} SP</Badge>
          </div>
          <Badge tone="success">Active Sprint</Badge>
        </div>
        {kanbanTasks.length === 0 ? (
          <EmptyState
            title="Sprint is empty"
            description="Confirm an effort estimate to send a task to this sprint."
          />
        ) : (
          <div className="divide-y divide-border">
            {kanbanTasks.map((task) => (
              <IssueRow
                key={task.id}
                id={task.id}
                title={task.title}
                requirementId={task.requirementId}
                requirements={requirements}
                points={task.points}
                statusLabel={task.status}
                statusTone={STATUS_TONE[task.status]}
                member={memberFor(teamMembers, task.assigneeId)}
                isStory={Boolean(task.storyId)}
                jiraKey={task.jira_issue_key || task.jiraKey}
                jiraBaseUrl={jiraStatus?.base_url}
                onClick={() => setOpenTask(task)}
              />
            ))}
          </div>
        )}
      </Card>

      {/* Sprint Creation Backlog: displays actual persisted user stories and estimates */}
      <Card className="p-0 overflow-hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-border bg-muted/20 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-foreground">
              Product Backlog
            </h3>
            <Badge tone="primary" className="text-xs">
              {eligibleTotalSP} SP
            </Badge>
            {jiraStatus?.connected && (
              <Badge
                tone="neutral"
                className="text-[10px] bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20"
              >
                Jira: {jiraStatus.project_key || "Connected"}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-muted-foreground mr-1 hidden sm:inline">
              {eligibleBacklogStories.length} estimated stor
              {eligibleBacklogStories.length === 1 ? "y" : "ies"}
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={resettingJira || syncingBacklog}
              onClick={handleResetJiraLinks}
              title="Clear Jira keys in database to start over and re-push fresh"
              className="text-xs gap-1.5 h-8 text-muted-foreground hover:text-foreground"
            >
              <RotateCcw className="h-3 w-3" />
              {resettingJira ? "Resetting..." : "Reset Jira Links"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={syncingBacklog || eligibleBacklogStories.length === 0}
              onClick={() => handleSyncBacklog(false)}
              className="text-xs gap-1.5 h-8 bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30"
            >
              <Send className="h-3 w-3" />
              {syncingBacklog ? "Pushing to Jira..." : "Push Backlog to Jira"}
            </Button>
            <Button
              size="sm"
              disabled={fetchingJira}
              onClick={handleFetchJira}
              className="text-xs gap-1.5 h-8"
            >
              <RefreshCw
                className={`h-3 w-3 ${fetchingJira ? "animate-spin" : ""}`}
              />
              {fetchingJira ? "Fetching Jira..." : "Fetch latest Jira data"}
            </Button>
          </div>
        </div>
        {eligibleBacklogStories.length === 0 ? (
          <EmptyState
            title="Product backlog is empty"
            description="Stories appear here after they pass planning and receive effort estimates."
            actionLabel="Go to Effort Estimation"
            onAction={() => navigate(team("/planning/requirements/estimation"))}
          />
        ) : (
          <div className="divide-y divide-border">
            {eligibleBacklogStories.map(({ story, requirementId, points }) => (
              <div key={story.id}>
                <IssueRow
                  id={story.id}
                  title={story.title}
                  requirementId={requirementId}
                  requirements={requirements}
                  points={points}
                  statusLabel="Estimated"
                  statusTone="success"
                  isStory
                  jiraKey={story.jira_issue_key || story.jiraKey}
                  jiraBaseUrl={jiraStatus?.base_url}
                  onClick={() =>
                    navigate(
                      team(
                        `/planning/requirements/estimation?req=${requirementId}`,
                      ),
                    )
                  }
                />
                {story.jira_issue_key && (
                  <div className="ml-10 mr-4 -mt-1 mb-2 text-[11px] text-muted-foreground">
                    Jira location:{" "}
                    <span className="font-medium text-foreground">
                      {story.jira_sprint_id
                        ? `Sprint ${story.jira_sprint_id}`
                        : "Backlog"}
                    </span>
                  </div>
                )}
                <div className="ml-10 mr-4 mb-3 rounded-lg border border-border/60 bg-muted/20 divide-y divide-border/60">
                  {(story.tasks || []).length === 0 ? (
                    <p className="px-3 py-2 text-[11px] text-muted-foreground italic">
                      No decomposition tasks added.
                    </p>
                  ) : (
                    story.tasks.map((task) => (
                      <div
                        key={task.id}
                        className="flex items-center gap-2 px-3 py-2 text-xs"
                      >
                        <SquareCheck className="h-3.5 w-3.5 text-primary shrink-0" />
                        <span className="font-medium text-foreground flex-1">
                          {task.title}
                        </span>
                        {task.jira_subtask_key && (
                          <a
                            href={
                              jiraStatus?.base_url
                                ? `${jiraStatus.base_url}/browse/${task.jira_subtask_key}`
                                : "#"
                            }
                            target="_blank"
                            rel="noreferrer"
                            className="text-[10px] text-blue-600 hover:underline dark:text-blue-400 font-medium shrink-0"
                            title={`Open ${task.jira_subtask_key} in Jira`}
                          >
                            {task.jira_subtask_key}
                          </a>
                        )}
                        <Badge tone="neutral" className="text-[10px]">
                          {task.priority || "medium"}
                        </Badge>
                        <Badge
                          tone={task.jira_sprint_id ? "primary" : "neutral"}
                          className="text-[10px]"
                        >
                          {task.jira_subtask_key
                            ? task.jira_sprint_id
                              ? `Sprint ${task.jira_sprint_id}`
                              : "Jira backlog"
                            : "Not synced"}
                        </Badge>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

const REPORTS_NAV = [
  { key: "sprint", label: "Sprint Report", icon: BarChart3 },
  { key: "burndown", label: "Burndown Chart", icon: TrendingDown },
  { key: "velocity", label: "Velocity Chart", icon: Gauge },
  { key: "status", label: "Status Breakdown", icon: LayoutGrid },
];

function SprintReportPanel() {
  const { kanbanTasks, requirements, userStories, estimations, projectInfo } =
    usePlanningData();
  const donePoints = kanbanTasks
    .filter((t) => t.status === "Done")
    .reduce((s, t) => s + t.points, 0);
  const inProgressPoints = kanbanTasks
    .filter((t) => t.status === "In Progress")
    .reduce((s, t) => s + t.points, 0);
  const todoPoints = kanbanTasks
    .filter((t) => t.status === "Todo")
    .reduce((s, t) => s + t.points, 0);
  const blockedCount = kanbanTasks.filter((t) => t.status === "Blocked").length;

  const passing = requirements.filter((r) => r.status === "Passing");
  let completed = 0,
    inDevelopment = 0,
    blocked = 0;
  for (const req of requirements) {
    if (req.status !== "Passing") {
      blocked++;
      continue;
    }
    const stories = userStories[req.id] || [];
    if (
      stories.length > 0 &&
      stories.every((s) => estimations[s.id]?.confirmed)
    )
      completed++;
    else inDevelopment++;
  }

  return (
    <div className="space-y-4">
      <Card>
        <h3 className="text-sm font-semibold text-foreground mb-1">
          Sprint Report
        </h3>
        <p className="text-xs text-muted-foreground mb-4">
          A snapshot of completed, in-progress and blocked work for{" "}
          {projectInfo.sprintName}.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard
            icon={BarChart3}
            label="Completed"
            value={`${donePoints} SP`}
            tone="success"
          />
          <StatCard
            icon={BarChart3}
            label="In Progress"
            value={`${inProgressPoints} SP`}
            tone="primary"
          />
          <StatCard
            icon={BarChart3}
            label="To Do"
            value={`${todoPoints} SP`}
            tone="warning"
          />
          <StatCard
            icon={AlertTriangle}
            label="Blocked"
            value={blockedCount}
            tone={blockedCount > 0 ? "danger" : "success"}
          />
        </div>
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-foreground mb-3">
          Requirement progress
        </h3>
        <div className="flex items-center gap-6 text-sm flex-wrap">
          <span className="flex items-center gap-1.5">
            <Badge tone="success">{completed}</Badge> Completed
          </span>
          <span className="flex items-center gap-1.5">
            <Badge tone="primary">{inDevelopment}</Badge> In development
          </span>
          <span className="flex items-center gap-1.5">
            <Badge tone="danger">{blocked}</Badge> Blocked
          </span>
          <span className="text-muted-foreground ml-auto">
            {passing.length + blocked} total
          </span>
        </div>
      </Card>
    </div>
  );
}

function BurndownPanel() {
  return (
    <Card>
      <h3 className="text-sm font-semibold text-foreground mb-1">
        Burndown Chart
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Tracks remaining story points against the ideal pace needed to finish
        everything by the end of the sprint.
      </p>
      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          <LineChart data={BURNDOWN_SEED}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="day"
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
            />
            <YAxis
              tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
              unit=" SP"
            />
            <RechartsTooltip
              contentStyle={{
                backgroundColor: "var(--popover)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Line
              type="monotone"
              dataKey="ideal"
              name="Ideal"
              stroke="var(--chart-2)"
              strokeDasharray="4 4"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual remaining"
              stroke="var(--chart-1)"
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function VelocityPanel() {
  return (
    <Card>
      <h3 className="text-sm font-semibold text-foreground mb-1">
        Velocity Chart
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Story points completed per sprint over time — use it to estimate how
        much the team can realistically commit to next.
      </p>
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer>
          <BarChart data={VELOCITY_TREND}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="sprint"
              tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
            />
            <YAxis tick={{ fill: "var(--muted-foreground)", fontSize: 12 }} />
            <RechartsTooltip
              contentStyle={{
                backgroundColor: "var(--popover)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Bar
              dataKey="velocity"
              name="Velocity"
              fill="var(--chart-1)"
              radius={[6, 6, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function StatusPanel() {
  const { kanbanTasks } = usePlanningData();
  const statusDistribution = KANBAN_COLUMNS.map((c) => ({
    status: c.label,
    points: kanbanTasks
      .filter((t) => t.status === c.key)
      .reduce((s, t) => s + t.points, 0),
  }));

  return (
    <Card>
      <h3 className="text-sm font-semibold text-foreground mb-1">
        Status Breakdown
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Story points currently sitting in each column of the board.
      </p>
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer>
          <BarChart data={statusDistribution}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="status"
              tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
            />
            <YAxis tick={{ fill: "var(--muted-foreground)", fontSize: 12 }} />
            <RechartsTooltip
              contentStyle={{
                backgroundColor: "var(--popover)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Bar
              dataKey="points"
              name="Story points"
              fill="var(--chart-3)"
              radius={[6, 6, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function flattenTasks(tasks, story) {
  return (tasks || []).flatMap((task) => [
    { ...task, story },
    ...flattenTasks(task.subtasks, story),
  ]);
}

const KANBAN_COLUMNS_CONFIG = [
  {
    key: "todo",
    label: "To Do",
    icon: Circle,
    iconClass: "text-slate-400",
    headerBorder: "border-slate-400 dark:border-slate-600",
    bgClass: "bg-slate-500/5 dark:bg-slate-900/20",
    emptyText: "No issues in To Do",
  },
  {
    key: "in_progress",
    label: "In Progress",
    icon: Clock,
    iconClass: "text-blue-500",
    headerBorder: "border-blue-500",
    bgClass: "bg-blue-500/5 dark:bg-blue-950/20",
    emptyText: "No issues in progress",
  },
  {
    key: "in_review",
    label: "In Review",
    icon: AlertTriangle,
    iconClass: "text-amber-500",
    headerBorder: "border-amber-500",
    bgClass: "bg-amber-500/5 dark:bg-amber-950/20",
    emptyText: "No issues awaiting review",
  },
  {
    key: "done",
    label: "Done",
    icon: CheckCircle2,
    iconClass: "text-emerald-500",
    headerBorder: "border-emerald-500",
    bgClass: "bg-emerald-500/5 dark:bg-emerald-950/20",
    emptyText: "No issues completed yet",
  },
];

function normalizeKanbanColumn(rawStatus) {
  const s = String(rawStatus || "")
    .toLowerCase()
    .trim();
  if (s === "done" || s === "complete" || s === "closed" || s === "resolved")
    return "done";
  if (
    s.includes("review") ||
    s.includes("qa") ||
    s.includes("testing") ||
    s.includes("verify")
  )
    return "in_review";
  if (
    s.includes("progress") ||
    s === "doing" ||
    s === "in dev" ||
    s === "started"
  )
    return "in_progress";
  return "todo";
}

function SprintSyncView({ onRefreshed }) {
  const { requirements, userStories, estimations, teamMembers } =
    usePlanningData();
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(false);
  const [transitioningKey, setTransitioningKey] = useState(null);
  const [viewMode, setViewMode] = useState("kanban"); // "kanban" | "table"
  const [entityType, setEntityType] = useState("stories"); // "stories" | "tasks"
  const [selectedSprintId, setSelectedSprintId] = useState("auto"); // "auto" | "all" | "backlog" | sprintId
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [expandedStories, setExpandedStories] = useState({});

  const requirementById = Object.fromEntries(
    requirements.map((req) => [req.id, req]),
  );
  const eligibleStories = Object.entries(userStories).flatMap(
    ([requirementId, stories]) =>
      (stories || []).filter((story) => {
        const points =
          estimations[story.id]?.finalPoints ??
          estimations[story.id]?.studentPoints ??
          story.student_story_points;
        return (
          requirementById[requirementId]?.status === "Passing" && points != null
        );
      }),
  );

  const linkedStories = eligibleStories.filter((story) => story.jira_issue_key);
  const allTasks = linkedStories.flatMap((story) =>
    flattenTasks(story.tasks, story),
  );

  // Auto-refresh once on mount
  useEffect(() => {
    fetchLatest(true);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function fetchLatest(silent = false) {
    setLoading(true);
    try {
      const response = await jiraService.fetchLatest();
      const data = response?.data ?? response;
      setSnapshot(data);
      await onRefreshed?.();
      if (!silent) {
        if (data?.errors?.length) {
          showToast.success("Jira refreshed with warnings", {
            description: `${data.stories_updated || 0} stories and ${data.tasks_updated || 0} tasks updated; ${data.errors.length} item(s) could not be read.`,
          });
        } else {
          showToast.success("Jira board refreshed", {
            description: `${data?.stories_updated || 0} stories and ${data?.tasks_updated || 0} tasks updated locally.`,
          });
        }
      }
    } catch (error) {
      if (!silent) {
        showToast.error("Could not fetch Jira data", {
          description:
            error?.response?.data?.detail ||
            error?.message ||
            "Verify the Jira connection in backend/.env and try again.",
        });
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleTransition(issueKey, targetStatus, isParentStory = false) {
    if (!issueKey || !targetStatus) return;
    const isDone = normalizeKanbanColumn(targetStatus) === "done";
    const acceptanceCriteriaConfirmed = isParentStory && isDone
      ? window.confirm("Confirm that all acceptance criteria and the Definition of Done have been verified. Unfinished Jira tasks will prevent completion.")
      : false;
    if (isParentStory && isDone && !acceptanceCriteriaConfirmed) return;
    setTransitioningKey(issueKey);
    try {
      const res = await jiraService.transitionIssue({
        issue_key: issueKey,
        target_status: targetStatus,
        acceptance_criteria_confirmed: acceptanceCriteriaConfirmed,
      });
      const data = res?.data ?? res;
      showToast.success(`Transitioned ${issueKey}`, {
        description: `Status changed to "${data?.jira_status || targetStatus}" on Jira and saved to database.`,
      });
      await fetchLatest(true);
    } catch (err) {
      showToast.error(`Could not move ${issueKey}`, {
        description:
          err?.response?.data?.detail ||
          err?.message ||
          `Failed to transition issue to "${targetStatus}". Check Jira workflow permissions.`,
      });
    } finally {
      setTransitioningKey(null);
    }
  }

  // Sprints discovered
  const sprints =
    snapshot?.sprints || (snapshot?.sprint ? [snapshot.sprint] : []);
  const activeSprint =
    sprints.find((s) => s.state === "active") || sprints[0] || null;

  // Resolve active sprint filter
  const resolvedSprintId =
    selectedSprintId === "auto"
      ? activeSprint?.jira_sprint_id
        ? String(activeSprint.jira_sprint_id)
        : "all"
      : selectedSprintId;

  const currentSprintObj =
    resolvedSprintId === "all" || resolvedSprintId === "backlog"
      ? null
      : sprints.find(
          (s) => String(s.jira_sprint_id) === String(resolvedSprintId),
        );

  // Filter items by sprint selection
  const sprintFilteredStories = linkedStories.filter((s) => {
    if (resolvedSprintId === "all") return true;
    if (resolvedSprintId === "backlog") return !s.jira_sprint_id;
    return String(s.jira_sprint_id) === String(resolvedSprintId);
  });

  const sprintFilteredTasks = allTasks.filter((t) => {
    if (resolvedSprintId === "all") return true;
    if (resolvedSprintId === "backlog")
      return !t.jira_sprint_id && !t.story?.jira_sprint_id;
    return (
      String(t.jira_sprint_id) === String(resolvedSprintId) ||
      String(t.story?.jira_sprint_id) === String(resolvedSprintId)
    );
  });

  // Calculate metrics
  const sprintTotalPoints = sprintFilteredStories.reduce(
    (sum, s) => sum + (Number(s.student_story_points) || 0),
    0,
  );
  const sprintDoneStories = sprintFilteredStories.filter(
    (s) => normalizeKanbanColumn(s.jira_status) === "done",
  );
  const sprintDonePoints = sprintDoneStories.reduce(
    (sum, s) => sum + (Number(s.student_story_points) || 0),
    0,
  );
  const sprintProgressPercent = sprintTotalPoints
    ? Math.round((sprintDonePoints / sprintTotalPoints) * 100)
    : 0;

  // Text/filter matches
  const term = search.trim().toLowerCase();
  const matches = (row) => {
    const status = (row.jira_status || row.status || "").toLowerCase();
    const priority = (row.priority || "").toLowerCase();
    const text = [
      row.story_ref,
      row.title,
      row.jira_issue_key,
      row.jira_subtask_key,
      row.story?.title,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return (
      (!term || text.includes(term)) &&
      (statusFilter === "all" || status === statusFilter.toLowerCase()) &&
      (priorityFilter === "all" || priority === priorityFilter.toLowerCase())
    );
  };

  const displayedStories = sprintFilteredStories.filter(matches);
  const displayedTasks = sprintFilteredTasks.filter(matches);
  const jiraUrl = snapshot?.jira_base_url;

  // Group into 4 columns
  const kanbanData = {
    todo: [],
    in_progress: [],
    in_review: [],
    done: [],
  };

  const itemsToGroup =
    entityType === "stories" ? displayedStories : displayedTasks;
  itemsToGroup.forEach((item) => {
    const colKey = normalizeKanbanColumn(item.jira_status || item.status);
    if (kanbanData[colKey]) {
      kanbanData[colKey].push(item);
    } else {
      kanbanData.todo.push(item);
    }
  });

  const toggleExpand = (id) => {
    setExpandedStories((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // The Sprint tab is intentionally empty when Jira has no linked sprint.
  // Backlog work stays visible only on the Backlog tab until a student places
  // it in a Jira sprint and starts/manages that sprint there.
  if (snapshot && sprints.length === 0) {
    return (
      <div className="space-y-4">
        <Card className="p-5 text-center">
          <Layers className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-foreground">
            No linked Jira sprint yet
          </h3>
          <p className="mt-1 text-xs text-muted-foreground max-w-lg mx-auto">
            Create and start a sprint in Jira, move the pushed user stories into
            it, then fetch Jira data here. Backlog work remains in the Backlog
            tab.
          </p>
          <div>
            <Button
              size="sm"
              onClick={() => fetchLatest(false)}
              disabled={loading}
              className="mt-4 gap-1.5"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
              />
              {loading ? "Syncing Jira..." : "Fetch latest Jira data"}
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* ── Top Control & Multi-Sprint Selector Toolbar ── */}
      <Card className="p-4 bg-card/95 border-border">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="space-y-1 max-w-full">
              <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                Jira Sprint Tabs
              </label>
              <div className="flex max-w-[620px] gap-1 overflow-x-auto pb-1">
                {sprints.map((sp) => {
                  const selected =
                    String(resolvedSprintId) === String(sp.jira_sprint_id);
                  return (
                    <button
                      key={sp.jira_sprint_id}
                      type="button"
                      onClick={() =>
                        setSelectedSprintId(String(sp.jira_sprint_id))
                      }
                      className={`shrink-0 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors ${selected ? "border-primary bg-primary/10 text-primary" : "border-border bg-background text-muted-foreground hover:text-foreground"}`}
                    >
                      {sp.name}{" "}
                      <span className="capitalize">
                        ({sp.state || "unknown"})
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Toggle between viewing Stories or Sub-tasks */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                Board Items
              </label>
              <div className="inline-flex rounded-lg border border-border p-0.5 bg-muted/40">
                <button
                  type="button"
                  onClick={() => setEntityType("stories")}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer ${
                    entityType === "stories"
                      ? "bg-card text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Stories ({displayedStories.length})
                </button>
                <button
                  type="button"
                  onClick={() => setEntityType("tasks")}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer ${
                    entityType === "tasks"
                      ? "bg-card text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Sub-tasks ({displayedTasks.length})
                </button>
              </div>
            </div>
          </div>

          {/* Right side: View Toggle & Sync Button */}
          <div className="flex items-center gap-2 flex-wrap self-end lg:self-center">
            <div className="inline-flex rounded-lg border border-border p-0.5 bg-muted/40 mr-1">
              <button
                type="button"
                onClick={() => setViewMode("kanban")}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer ${
                  viewMode === "kanban"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                title="Kanban Board view"
              >
                <LayoutGrid className="h-3.5 w-3.5" />
                Kanban
              </button>
              <button
                type="button"
                onClick={() => setViewMode("table")}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer ${
                  viewMode === "table"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                title="Table List view"
              >
                <ListTodo className="h-3.5 w-3.5" />
                Table
              </button>
            </div>

            <Button
              size="sm"
              onClick={() => fetchLatest(false)}
              disabled={loading}
              className="gap-1.5 text-xs h-9 cursor-pointer"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
              />
              {loading ? "Syncing Jira..." : "Sync from Jira"}
            </Button>
          </div>
        </div>

        {/* Sprint Header / Health Bar */}
        {currentSprintObj ? (
          <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-bold text-foreground">
                  {currentSprintObj.name}
                </h4>
                <Badge
                  tone={
                    currentSprintObj.state === "active"
                      ? "success"
                      : currentSprintObj.state === "future"
                        ? "primary"
                        : "neutral"
                  }
                  className="text-[10px] capitalize"
                >
                  {currentSprintObj.state || "Sprint"}
                </Badge>
                {jiraUrl && (
                  <a
                    href={`${jiraUrl}/jira/software/projects`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-blue-600 hover:underline dark:text-blue-400 inline-flex items-center gap-0.5 ml-1"
                    title="View board on Jira Cloud"
                  >
                    Open in Jira <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {currentSprintObj.start_date && currentSprintObj.end_date
                  ? `${formatShortDate(currentSprintObj.start_date)} – ${formatShortDate(currentSprintObj.end_date)}`
                  : "Sprint dates not set in Jira"}
              </p>
              {currentSprintObj.goal && (
                <p className="text-xs text-muted-foreground italic line-clamp-1">
                  Goal: {currentSprintObj.goal}
                </p>
              )}
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <div className="flex items-center justify-between text-xs font-medium">
                <span className="text-muted-foreground">
                  Sprint Story Points Progress
                </span>
                <span className="font-bold text-foreground">
                  {sprintDonePoints} / {sprintTotalPoints} SP (
                  {sprintProgressPercent}%)
                </span>
              </div>
              <Progress value={sprintProgressPercent} className="h-2" />
              <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-0.5">
                <span>{sprintFilteredStories.length} linked user stories</span>
                <span>{sprintFilteredTasks.length} decomposition tasks</span>
                <span>
                  {snapshot?.fetched_at
                    ? `Last synced: ${new Date(snapshot.fetched_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                    : "Live mirrored"}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-3 pt-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground flex-wrap gap-2">
            <span>
              Showing{" "}
              {resolvedSprintId === "backlog"
                ? "Jira Backlog stories"
                : "All sprints combined"}{" "}
              ({sprintFilteredStories.length} stories,{" "}
              {sprintFilteredTasks.length} tasks)
            </span>
            {snapshot?.fetched_at && (
              <span>
                Last synced:{" "}
                {new Date(snapshot.fetched_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            )}
          </div>
        )}
      </Card>

      {snapshot?.completion_conflicts?.length > 0 && (
        <Card className="border-destructive/40 bg-destructive/5 p-4">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
            <div>
              <h4 className="text-sm font-semibold text-destructive">Jira completion conflict</h4>
              <p className="mt-1 text-xs text-muted-foreground">
                Jira has marked a parent story Done while linked tasks are still open. The system will not treat these stories as validly complete.
              </p>
              <ul className="mt-2 space-y-1 text-xs text-foreground">
                {snapshot.completion_conflicts.map((conflict) => (
                  <li key={conflict.story_ref}>
                    <span className="font-medium">{conflict.story_ref}</span>: {conflict.open_tasks.join(", ") || "acceptance criteria require review"}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Card>
      )}

      {/* ── Search & Filter Bar ── */}
      <Card className="p-3 bg-card/60">
        <div className="flex flex-col sm:flex-row gap-2.5 items-center">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title, ref (STORY-001), or Jira key (SCRUM-26)..."
              className="h-8 pl-8 text-xs bg-background"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="h-8 w-full sm:w-36 text-xs bg-background">
              <SelectValue placeholder="Status filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="to do">To Do</SelectItem>
              <SelectItem value="in progress">In Progress</SelectItem>
              <SelectItem value="in review">In Review</SelectItem>
              <SelectItem value="done">Done</SelectItem>
            </SelectContent>
          </Select>
          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger className="h-8 w-full sm:w-32 text-xs bg-background">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All priorities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* ── VIEW MODE 1: KANBAN BOARD ── */}
      {viewMode === "kanban" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {KANBAN_COLUMNS_CONFIG.map((col) => {
            const ColumnIcon = col.icon;
            const items = kanbanData[col.key] || [];
            const colTotalPoints =
              entityType === "stories"
                ? items.reduce(
                    (s, it) => s + (Number(it.student_story_points) || 0),
                    0,
                  )
                : null;

            return (
              <div
                key={col.key}
                className={`flex flex-col rounded-xl border border-border bg-card/50 overflow-hidden ${col.bgClass}`}
              >
                {/* Column Header */}
                <div
                  className={`p-3 border-b border-border border-t-2 ${col.headerBorder} bg-card flex items-center justify-between`}
                >
                  <div className="flex items-center gap-2">
                    <ColumnIcon className={`h-4 w-4 ${col.iconClass}`} />
                    <span className="font-semibold text-xs text-foreground">
                      {col.label}
                    </span>
                    <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-muted text-muted-foreground">
                      {items.length}
                    </span>
                  </div>
                  {colTotalPoints != null && colTotalPoints > 0 && (
                    <Badge
                      tone="primary"
                      className="text-[10px] px-1.5 py-0 font-medium"
                    >
                      {colTotalPoints} SP
                    </Badge>
                  )}
                </div>

                {/* Column Cards */}
                <div className="p-2.5 space-y-3 flex-1 min-h-[380px]">
                  {items.length === 0 ? (
                    <div className="h-full min-h-[140px] flex items-center justify-center p-4 border border-dashed border-border/80 rounded-lg text-center">
                      <p className="text-xs text-muted-foreground/70 italic">
                        {col.emptyText}
                      </p>
                    </div>
                  ) : (
                    items.map((item) => {
                      const isStory = entityType === "stories";
                      const issueKey = isStory
                        ? item.jira_issue_key
                        : item.jira_subtask_key;
                      const isTransitioning = transitioningKey === issueKey;
                      const reqId =
                        item.requirementId ||
                        item.parentRequirementRef ||
                        item.story?.parentRequirementRef;
                      const tasks = item.tasks || [];
                      const doneTasks = tasks.filter(
                        (t) =>
                          normalizeKanbanColumn(t.jira_status || t.status) ===
                          "done",
                      ).length;
                      const isExpanded = Boolean(expandedStories[item.id]);
                      const assigneeName =
                        item.jira_assignee_display_name || "Unassigned";

                      return (
                        <div
                          key={item.id}
                          className="group relative rounded-xl border border-border/80 bg-card p-3 shadow-xs hover:border-primary/40 hover:shadow-md transition-all space-y-2.5"
                        >
                          {/* Card Header: Req pill, Jira key, Story points */}
                          <div className="flex items-center justify-between gap-1.5 flex-wrap">
                            <div className="flex items-center gap-1.5">
                              {reqId && (
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${epicChipClass(
                                    reqId,
                                    requirements,
                                  )}`}
                                >
                                  {reqId}
                                </span>
                              )}
                              {issueKey ? (
                                <a
                                  href={
                                    jiraUrl
                                      ? `${jiraUrl}/browse/${issueKey}`
                                      : "#"
                                  }
                                  target="_blank"
                                  rel="noreferrer"
                                  className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-blue-500/10 text-blue-600 hover:text-blue-700 dark:text-blue-400 border border-blue-500/20"
                                  title={`Open ${issueKey} in Jira Cloud`}
                                >
                                  {issueKey}
                                  <ExternalLink className="h-2.5 w-2.5 opacity-70" />
                                </a>
                              ) : (
                                <span className="text-[10px] font-mono text-muted-foreground">
                                  {item.story_ref || "Local"}
                                </span>
                              )}
                            </div>

                            {isStory && item.student_story_points != null && (
                              <Badge
                                tone="primary"
                                className="text-[10px] px-1.5 py-0 font-medium"
                              >
                                {item.student_story_points} SP
                              </Badge>
                            )}
                          </div>

                          {/* Card Title */}
                          <h5 className="text-xs font-medium text-foreground leading-snug line-clamp-2">
                            {item.title}
                          </h5>

                          {/* Subtasks Progress (for Stories) */}
                          {isStory && tasks.length > 0 && (
                            <div className="pt-1 space-y-1">
                              <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                                <span className="flex items-center gap-1">
                                  <SquareCheck className="h-3 w-3 text-primary" />
                                  Tasks: {doneTasks}/{tasks.length} done
                                </span>
                                <button
                                  type="button"
                                  onClick={() => toggleExpand(item.id)}
                                  className="text-primary hover:underline font-medium cursor-pointer"
                                >
                                  {isExpanded ? "Hide" : "Show"}
                                </button>
                              </div>
                              <Progress
                                value={Math.round(
                                  (doneTasks / tasks.length) * 100,
                                )}
                                className="h-1"
                              />

                              {/* Collapsible Subtasks preview */}
                              {isExpanded && (
                                <div className="mt-2 space-y-1.5 pt-1 border-t border-border/60">
                                  {tasks.map((task) => (
                                    <div
                                      key={task.id}
                                      className="flex items-center justify-between gap-1 p-1.5 rounded bg-muted/40 text-[11px]"
                                    >
                                      <div className="flex items-center gap-1.5 min-w-0">
                                        <SquareCheck className="h-3 w-3 text-muted-foreground shrink-0" />
                                        <span className="truncate">
                                          {task.title}
                                        </span>
                                      </div>
                                      <div className="flex items-center gap-1 shrink-0">
                                        {task.jira_subtask_key && (
                                          <a
                                            href={
                                              jiraUrl
                                                ? `${jiraUrl}/browse/${task.jira_subtask_key}`
                                                : "#"
                                            }
                                            target="_blank"
                                            rel="noreferrer"
                                            className="font-mono text-[9px] text-blue-600 dark:text-blue-400 hover:underline"
                                          >
                                            {task.jira_subtask_key}
                                          </a>
                                        )}
                                        <Badge
                                          tone={
                                            normalizeKanbanColumn(
                                              task.jira_status || task.status,
                                            ) === "done"
                                              ? "success"
                                              : "neutral"
                                          }
                                          className="text-[9px] px-1 py-0 capitalize"
                                        >
                                          {task.jira_status ||
                                            task.status ||
                                            "todo"}
                                        </Badge>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Card Footer: Assignee & Move Selector */}
                          <div className="pt-2 border-t border-border/60 flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5 min-w-0">
                              <AvatarComp name={assigneeName} size={18} />
                              <span
                                className="text-[11px] text-muted-foreground truncate max-w-[80px]"
                                title={assigneeName}
                              >
                                {assigneeName}
                              </span>
                            </div>

                            {/* Status Transition Control */}
                            {issueKey ? (
                              <div className="flex items-center gap-1">
                                {isTransitioning ? (
                                  <span className="flex items-center gap-1 text-[10px] text-primary font-medium">
                                    <RefreshCw className="h-3 w-3 animate-spin" />
                                    Moving...
                                  </span>
                                ) : (
                                  <Select
                                    value={
                                      col.key === "todo"
                                        ? "To Do"
                                        : col.key === "in_progress"
                                          ? "In Progress"
                                          : col.key === "in_review"
                                            ? "In Review"
                                            : "Done"
                                    }
                                    onValueChange={(val) =>
                                      handleTransition(issueKey, val, isStory)
                                    }
                                  >
                                    <SelectTrigger className="h-6 px-1.5 text-[10px] w-24 bg-muted/40 hover:bg-muted font-medium border-border/80">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="To Do">
                                        To Do
                                      </SelectItem>
                                      <SelectItem value="In Progress">
                                        In Progress
                                      </SelectItem>
                                      <SelectItem value="In Review">
                                        In Review
                                      </SelectItem>
                                      <SelectItem value="Done">Done</SelectItem>
                                    </SelectContent>
                                  </Select>
                                )}
                              </div>
                            ) : (
                              <Badge tone="neutral" className="text-[9px]">
                                Not on Jira
                              </Badge>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* ── VIEW MODE 2: DETAILED TABLES ── */
        <div className="space-y-4">
          <Card className="p-0 overflow-x-auto">
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <h3 className="text-sm font-semibold">
                User Stories ({displayedStories.length})
              </h3>
            </div>
            <table className="w-full min-w-[820px] text-xs">
              <thead className="bg-muted/30 text-muted-foreground">
                <tr>
                  <th className="text-left p-3">Ref</th>
                  <th className="text-left p-3">Story</th>
                  <th className="text-left p-3">Jira Key</th>
                  <th className="text-left p-3">Status</th>
                  <th className="text-left p-3">Sprint</th>
                  <th className="text-left p-3">Points</th>
                  <th className="text-left p-3">Priority</th>
                  <th className="text-left p-3">Assignee</th>
                  <th className="text-left p-3">Move Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {displayedStories.map((story) => (
                  <tr key={story.id}>
                    <td className="p-3 font-medium">{story.story_ref}</td>
                    <td className="p-3 max-w-[280px]">
                      <div className="truncate font-medium text-foreground">
                        {story.title}
                      </div>
                    </td>
                    <td className="p-3">
                      {story.jira_issue_key ? (
                        <a
                          href={
                            jiraUrl
                              ? `${jiraUrl}/browse/${story.jira_issue_key}`
                              : "#"
                          }
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 font-mono text-primary hover:underline font-medium"
                        >
                          {story.jira_issue_key}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="p-3">
                      <Badge
                        tone={
                          normalizeKanbanColumn(story.jira_status) === "done"
                            ? "success"
                            : normalizeKanbanColumn(story.jira_status) ===
                                "in_progress"
                              ? "primary"
                              : "neutral"
                        }
                      >
                        {story.jira_status || "To Do"}
                      </Badge>
                    </td>
                    <td className="p-3">
                      {story.jira_sprint_id
                        ? `Sprint ${story.jira_sprint_id}`
                        : "Jira backlog"}
                    </td>
                    <td className="p-3">{story.student_story_points ?? "—"}</td>
                    <td className="p-3 capitalize">{story.priority}</td>
                    <td className="p-3">
                      {story.jira_assignee_display_name || "Unassigned"}
                    </td>
                    <td className="p-3">
                      {story.jira_issue_key && (
                        <Select
                          value={story.jira_status || "To Do"}
                          onValueChange={(val) =>
                            handleTransition(story.jira_issue_key, val, true)
                          }
                          disabled={transitioningKey === story.jira_issue_key}
                        >
                          <SelectTrigger className="h-7 text-[11px] w-28">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="To Do">To Do</SelectItem>
                            <SelectItem value="In Progress">
                              In Progress
                            </SelectItem>
                            <SelectItem value="In Review">In Review</SelectItem>
                            <SelectItem value="Done">Done</SelectItem>
                          </SelectContent>
                        </Select>
                      )}
                    </td>
                  </tr>
                ))}
                {displayedStories.length === 0 && (
                  <tr>
                    <td
                      colSpan="9"
                      className="p-6 text-center text-muted-foreground"
                    >
                      No user stories match current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </Card>

          <Card className="p-0 overflow-x-auto">
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <h3 className="text-sm font-semibold">
                Tasks ({displayedTasks.length})
              </h3>
            </div>
            <table className="w-full min-w-[820px] text-xs">
              <thead className="bg-muted/30 text-muted-foreground">
                <tr>
                  <th className="text-left p-3">Parent</th>
                  <th className="text-left p-3">Task</th>
                  <th className="text-left p-3">Jira Key</th>
                  <th className="text-left p-3">Jira Status</th>
                  <th className="text-left p-3">Priority</th>
                  <th className="text-left p-3">Assignee</th>
                  <th className="text-left p-3">Move Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {displayedTasks.map((task) => (
                  <tr key={task.id}>
                    <td className="p-3 font-medium">{task.story?.story_ref}</td>
                    <td className="p-3 max-w-[280px]">
                      <div className="truncate font-medium text-foreground">
                        {task.title}
                      </div>
                    </td>
                    <td className="p-3">
                      {task.jira_subtask_key ? (
                        <a
                          href={
                            jiraUrl
                              ? `${jiraUrl}/browse/${task.jira_subtask_key}`
                              : "#"
                          }
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 font-mono text-primary hover:underline font-medium"
                        >
                          {task.jira_subtask_key}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="p-3">
                      <Badge
                        tone={
                          normalizeKanbanColumn(
                            task.jira_status || task.status,
                          ) === "done"
                            ? "success"
                            : "neutral"
                        }
                      >
                        {task.jira_status || task.status || "To Do"}
                      </Badge>
                    </td>
                    <td className="p-3 capitalize">{task.priority}</td>
                    <td className="p-3">
                      {task.jira_assignee_display_name || "Unassigned"}
                    </td>
                    <td className="p-3">
                      {task.jira_subtask_key && (
                        <Select
                          value={task.jira_status || "To Do"}
                          onValueChange={(val) =>
                            handleTransition(task.jira_subtask_key, val, false)
                          }
                          disabled={transitioningKey === task.jira_subtask_key}
                        >
                          <SelectTrigger className="h-7 text-[11px] w-28">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="To Do">To Do</SelectItem>
                            <SelectItem value="In Progress">
                              In Progress
                            </SelectItem>
                            <SelectItem value="In Review">In Review</SelectItem>
                            <SelectItem value="Done">Done</SelectItem>
                          </SelectContent>
                        </Select>
                      )}
                    </td>
                  </tr>
                ))}
                {displayedTasks.length === 0 && (
                  <tr>
                    <td
                      colSpan="7"
                      className="p-6 text-center text-muted-foreground"
                    >
                      No tasks match current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </Card>
        </div>
      )}
    </div>
  );
}

function ReportsView() {
  const [reportKey, setReportKey] = useState("sprint");

  return (
    <div className="flex flex-col sm:flex-row gap-4">
      <nav className="sm:w-[180px] shrink-0 space-y-0.5">
        {REPORTS_NAV.map((r) => {
          const Icon = r.icon;
          const active = reportKey === r.key;
          return (
            <button
              key={r.key}
              type="button"
              onClick={() => setReportKey(r.key)}
              className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-md text-xs font-medium text-left transition-colors cursor-pointer ${
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              }`}
            >
              <Icon className="h-3.5 w-3.5 shrink-0" /> {r.label}
            </button>
          );
        })}
      </nav>
      <div className="flex-1 min-w-0">
        {reportKey === "sprint" && <SprintReportPanel />}
        {reportKey === "burndown" && <BurndownPanel />}
        {reportKey === "velocity" && <VelocityPanel />}
        {reportKey === "status" && <StatusPanel />}
      </div>
    </div>
  );
}

export default function SprintManagement() {
  const queryClient = useQueryClient();
  const {
    projectInfo,
    teamMembers,
    kanbanTasks,
    requirements,
    userStories,
    estimations,
    loadKanbanTasks,
    loadStories,
    loadEstimations,
    moveKanbanTask,
    assignKanbanTask,
  } = usePlanningData();
  const { data: tasksResp } = useSprintTasks();
  const { data: storiesResp } = useStories();
  const { data: estimatesResp } = useEstimates();
  const updateTask = useUpdateSprintTask();
  const [tab, setTab] = useState("backlog");
  const [today] = useState(() => Date.now());
  const [consultOpen, setConsultOpen] = useState(false);
  const [scrumGuideOpen, setScrumGuideOpen] = useState(false);

  useEffect(() => {
    const items =
      tasksResp?.data?.items ||
      tasksResp?.data?.tasks ||
      tasksResp?.items ||
      tasksResp?.tasks;
    if (!Array.isArray(items)) return;
    const mapped = mapSprintTasks(items);
    loadKanbanTasks(mapped);
  }, [tasksResp]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const stories = storiesResp?.data?.stories || storiesResp?.stories;
    if (!Array.isArray(stories)) return;
    const mapped = mapStoryRows(stories);
    loadStories(mapped, { replace: true });
  }, [storiesResp]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const rows = estimatesResp?.data?.estimates || estimatesResp?.estimates;
    if (!Array.isArray(rows)) return;
    const estMap = {};
    for (const row of rows) {
      const storyRef = row.story_ref || row.user_story_id;
      if (!storyRef) continue;
      estMap[storyRef] = {
        studentPoints: row.estimated_story_points ?? row.story_points ?? null,
        finalPoints:
          row.final_story_points ??
          row.story_points ??
          row.estimated_story_points ??
          null,
        reason: row.estimation_basis ?? row.reason ?? "",
        confirmed: row.confirmed ?? false,
      };
    }
    loadEstimations(estMap);
  }, [estimatesResp]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleMove(taskId, newStatus) {
    moveKanbanTask(taskId, newStatus);
    updateTask.mutate({ id: taskId, patch: { status: newStatus } });
  }

  function handleAssign(taskId, assigneeId) {
    assignKanbanTask(taskId, assigneeId);
    updateTask.mutate({ id: taskId, patch: { assigned_to: assigneeId } });
  }

  async function refreshPlanningData() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["planning-stories"] }),
      queryClient.invalidateQueries({ queryKey: ["backlog-items"] }),
    ]);
  }

  const totalPoints = kanbanTasks.reduce((s, t) => s + t.points, 0);
  const donePoints = kanbanTasks
    .filter((t) => t.status === "Done")
    .reduce((s, t) => s + t.points, 0);
  const blockedCount = kanbanTasks.filter((t) => t.status === "Blocked").length;
  const progressPercent = totalPoints
    ? Math.round((donePoints / totalPoints) * 100)
    : 0;
  const daysLeft = Math.max(
    0,
    Math.ceil(
      (new Date(projectInfo.sprintEndDate).getTime() - today) / 86400000,
    ),
  );

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <GraduationCap className="h-3.5 w-3.5 text-primary" />
            <span>
              {COURSE_INFO.courseCode} · {COURSE_INFO.courseName}
            </span>
            <span className="text-border">/</span>
            <span className="text-foreground">Milestone M3</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            Sprint Execution &amp; Agile Burndown
            <Badge tone="primary" className="text-xs font-medium">
              Sprint 1 of 4 Active
            </Badge>
          </h1>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setScrumGuideOpen(true)}
            className="text-xs cursor-pointer gap-1.5"
          >
            <BookOpen className="h-3.5 w-3.5 text-primary" /> Scrum Standards
            Guide
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setConsultOpen(true)}
            className="text-xs cursor-pointer gap-1.5"
          >
            <UserCheck className="h-3.5 w-3.5 text-primary" /> Supervisor
            Advisory
          </Button>
        </div>
      </div>

      <Card className="p-5 relative overflow-hidden bg-card/90">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="space-y-2 min-w-0 max-w-2xl">
            <div className="flex items-center gap-2 flex-wrap text-xs text-muted-foreground">
              <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Active Sprint
              </span>
              <span>·</span>
              <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary font-bold">
                {COURSE_INFO.group.number} ({COURSE_INFO.group.code})
              </span>
              <span>·</span>
              <span className="font-semibold text-foreground">
                {COURSE_INFO.department}
              </span>
              <span>·</span>
              <span>
                {formatShortDate(projectInfo.sprintStartDate)} –{" "}
                {formatShortDate(projectInfo.sprintEndDate)} ·{" "}
                {projectInfo.sprintName} of {projectInfo.totalSprints}
              </span>
            </div>

            <h2 className="text-lg sm:text-xl font-semibold text-foreground tracking-tight">
              {projectInfo.sprintName} · Agile Task Board &amp; Burndown
            </h2>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Track real-time sprint execution across backlog user stories,
              subtasks, and Kanban columns. Drag cards between columns to update
              status — changes persist to the backend automatically.
            </p>

            <div className="flex items-center gap-4 flex-wrap pt-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <AvatarComp
                  name={COURSE_INFO.supervisor.name}
                  size={20}
                  className="ring-1 ring-border"
                />
                Supervisor: {COURSE_INFO.supervisor.name}
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5 text-primary" />
                {teamMembers.length} Members
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-amber-500" />
                {kanbanTasks.length} Tasks ({totalPoints} SP)
              </span>
              {blockedCount > 0 && (
                <>
                  <span className="h-1 w-1 rounded-full bg-border" />
                  <span className="flex items-center gap-1.5 text-destructive font-medium">
                    <AlertTriangle className="h-3.5 w-3.5" /> {blockedCount}{" "}
                    Blocked
                  </span>
                </>
              )}
              <span className="h-1 w-1 rounded-full bg-border" />
              <Badge tone="primary" className="text-[11px] px-2 py-0.5">
                {daysLeft === 0
                  ? "Ends today"
                  : `${daysLeft} day${daysLeft === 1 ? "" : "s"} remaining`}
              </Badge>
              <div className="flex -space-x-2 ml-1">
                {teamMembers.map((m) => (
                  <AvatarComp
                    key={m.id}
                    name={m.name}
                    size={22}
                    className="ring-2 ring-card"
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="flex flex-col items-center justify-center shrink-0 self-center sm:self-center px-3 py-1">
            <div
              className="relative flex items-center justify-center"
              style={{ width: 92, height: 92 }}
            >
              <svg
                className="w-full h-full -rotate-90 transform"
                viewBox="0 0 92 92"
              >
                <circle
                  cx="46"
                  cy="46"
                  r="38"
                  className="stroke-muted"
                  strokeWidth="7"
                  fill="transparent"
                />
                <circle
                  cx="46"
                  cy="46"
                  r="38"
                  className="stroke-primary transition-all duration-700 ease-out"
                  strokeWidth="7"
                  strokeDasharray={2 * Math.PI * 38}
                  strokeDashoffset={
                    2 * Math.PI * 38 * (1 - progressPercent / 100)
                  }
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-bold tracking-tight text-foreground">
                  {progressPercent}%
                </span>
              </div>
            </div>
            <span className="text-xs font-semibold text-muted-foreground mt-1.5">
              Sprint Burned
            </span>
          </div>
        </div>
      </Card>

      <WorkflowStepper current="sprint" />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="w-full h-auto justify-start flex-wrap gap-1 rounded-none bg-transparent p-0 border-b border-border">
          <TabsTrigger
            value="sprint"
            className="rounded-none border-b-2 border-transparent px-3 py-2.5 text-sm font-medium gap-1.5 text-muted-foreground hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none cursor-pointer"
          >
            <LayoutGrid className="h-3.5 w-3.5" />
            Active Sprint Kanban
          </TabsTrigger>
          <TabsTrigger
            value="backlog"
            className="rounded-none border-b-2 border-transparent px-3 py-2.5 text-sm font-medium gap-1.5 text-muted-foreground hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none cursor-pointer"
          >
            <Layers className="h-3.5 w-3.5" />
            Product Backlog &amp; Export
          </TabsTrigger>
          <TabsTrigger
            value="reports"
            className="rounded-none border-b-2 border-transparent px-3 py-2.5 text-sm font-medium gap-1.5 text-muted-foreground hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none cursor-pointer"
          >
            <BarChart3 className="h-3.5 w-3.5" />
            Agile Reports &amp; Burndown
          </TabsTrigger>
        </TabsList>
        <TabsContent value="sprint" className="mt-4">
          <SprintSyncView onRefreshed={refreshPlanningData} />
        </TabsContent>
        <TabsContent value="backlog" className="mt-4">
          <BacklogView onRefreshed={refreshPlanningData} />
        </TabsContent>
        <TabsContent value="reports" className="mt-4">
          <ReportsView />
        </TabsContent>
      </Tabs>

      <DartButton context="sprint" />

      <SupervisorConsultationModal
        open={consultOpen}
        onOpenChange={setConsultOpen}
        requirements={requirements}
      />

      <Dialog open={scrumGuideOpen} onOpenChange={setScrumGuideOpen}>
        <DialogContent className="sm:max-w-[620px] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1 rounded bg-primary/10 text-primary">
                <BookOpen className="h-4 w-4" />
              </span>
              <DialogTitle className="text-lg font-bold">
                Scrum &amp; Sprint Execution Standards
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              Academic guidelines used for Milestone M3 sprint evaluation and
              agile ceremony compliance.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-xl border border-border bg-card space-y-1">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-foreground text-xs flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-primary" />{" "}
                  Definition of Done (DoD)
                </h4>
                <Badge tone="primary" className="text-[10px] px-1.5 py-0">
                  Criterion 1
                </Badge>
              </div>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                A user story or task is only marked Done when code is reviewed,
                unit/integration tests pass, and INVEST acceptance criteria
                (Given/When/Then) are confirmed.
              </p>
            </div>

            <div className="p-3 rounded-xl border border-border bg-card space-y-1">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-foreground text-xs flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-primary" />{" "}
                  Work-In-Progress (WIP) Limits
                </h4>
                <Badge tone="primary" className="text-[10px] px-1.5 py-0">
                  Criterion 2
                </Badge>
              </div>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                Limit active tasks in &apos;In Progress&apos; per team member to
                prevent context switching and bottlenecks during sprint
                execution.
              </p>
            </div>

            <div className="p-3 rounded-xl border border-border bg-card space-y-1">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-foreground text-xs flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-primary" />{" "}
                  Impediment &amp; Blocked Escalation
                </h4>
                <Badge tone="primary" className="text-[10px] px-1.5 py-0">
                  Criterion 3
                </Badge>
              </div>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                Tasks blocked for more than 24 hours must be annotated with a
                clear reason and escalated to Dr. Amara Silva or DART
                arbitration.
              </p>
            </div>

            <div className="p-3 rounded-xl border border-border bg-card space-y-1">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-foreground text-xs flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-primary" /> Velocity
                  Consistency &amp; Burndown
                </h4>
                <Badge tone="primary" className="text-[10px] px-1.5 py-0">
                  Criterion 4
                </Badge>
              </div>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                Burndown should track reasonably close to the ideal guideline.
                Sudden drop-offs at sprint end without steady progression will
                be flagged.
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
