import { useState } from 'react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  useTeamDetail,
  useAddTeamMember,
  useRemoveTeamMember,
  useTriggerAgentJob,
} from '@/shared/hooks/useTeamManagement'
import {
  ShieldAlert,
  BarChart3,
  UserPlus,
  Trash2,
  GitBranch,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Crown,
} from 'lucide-react'

export default function TeamRosterDrawer({ open, onOpenChange, teamId }) {
  const { data: team, isLoading } = useTeamDetail(teamId)
  const addMemberMutation = useAddTeamMember(teamId)
  const removeMemberMutation = useRemoveTeamMember(teamId)
  const triggerJobMutation = useTriggerAgentJob()

  const [newStudentId, setNewStudentId] = useState('')
  const [newRole, setNewRole] = useState('member')

  const handleAddMember = (e) => {
    e.preventDefault()
    if (!newStudentId.trim()) return

    addMemberMutation.mutate(
      {
        student_id: newStudentId.trim().toUpperCase(),
        role: newRole,
      },
      {
        onSuccess: () => {
          setNewStudentId('')
        },
      }
    )
  }

  const handleRemoveMember = (studentId) => {
    if (confirm(`Remove student ${studentId} from this team?`)) {
      removeMemberMutation.mutate(studentId)
    }
  }

  const handleTriggerSecretScan = () => {
    if (!team) return
    triggerJobMutation.mutate({
      task_name: 'security.scan_repository_secrets',
      queue: 'security',
      payload: {
        repo_url: team.repo_url || 'https://github.com/sliit-y4/selvia',
        team_id: team.id,
      },
    })
  }

  const handleTriggerAssessment = () => {
    if (!team) return
    triggerJobMutation.mutate({
      task_name: 'performance.assess_student',
      queue: 'performance',
      payload: {
        student_id: team.leader_student_id || 'IT210001',
        batch_id: team.batch_id,
        sprint_id: 'sprint-1',
      },
    })
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-md w-full overflow-y-auto flex flex-col justify-between">
        <div>
          <SheetHeader className="border-b border-border pb-4">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-primary px-2 py-0.5 rounded bg-primary/10">
                {team?.team_code || 'TEAM'}
              </span>
              <Badge variant="outline" className="text-[11px] capitalize">
                {team?.status || 'active'}
              </Badge>
            </div>
            <SheetTitle className="text-lg font-bold">{team?.name || 'Team Details'}</SheetTitle>
            <SheetDescription className="text-xs">
              Batch: <span className="font-mono text-foreground font-semibold">{team?.batch_id}</span>
            </SheetDescription>
          </SheetHeader>

          {isLoading ? (
            <div className="p-8 text-center text-xs text-muted-foreground">Loading roster...</div>
          ) : !team ? (
            <div className="p-8 text-center text-xs text-muted-foreground">Team not found.</div>
          ) : (
            <div className="space-y-6 pt-4 text-xs">
              {/* Repository & Agent Trigger Actions */}
              <div className="p-3.5 rounded-xl border border-border bg-card shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground flex items-center gap-1.5 font-medium">
                    <GitBranch className="h-3.5 w-3.5" />
                    Git Repository
                  </span>
                  {team.repo_url ? (
                    <a
                      href={team.repo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline flex items-center gap-1 font-mono text-[11px]"
                    >
                      Open <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : (
                    <span className="text-muted-foreground text-[11px]">Not configured</span>
                  )}
                </div>

                <div className="flex gap-2 pt-1">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="flex-1 text-[11px] h-8"
                    onClick={handleTriggerSecretScan}
                    disabled={triggerJobMutation.isPending}
                  >
                    <ShieldAlert className="h-3.5 w-3.5 mr-1 text-amber-500" />
                    Secret Scan
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="flex-1 text-[11px] h-8"
                    onClick={handleTriggerAssessment}
                    disabled={triggerJobMutation.isPending}
                  >
                    <BarChart3 className="h-3.5 w-3.5 mr-1 text-blue-500" />
                    Assess Team
                  </Button>
                </div>
              </div>

              {/* Members Roster List */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold uppercase tracking-wider text-[11px] text-muted-foreground">
                    Enrolled Students ({team.members?.length || 0})
                  </h4>
                </div>

                <div className="space-y-2">
                  {team.members?.map((m) => {
                    const student = m.student
                    const hasGithub = Boolean(student?.github_username)
                    const isLeader = m.role === 'leader' || team.leader_student_id === m.student_id

                    return (
                      <div
                        key={m.id || m.student_id}
                        className="p-3 rounded-xl border border-border bg-card flex items-center justify-between gap-3 shadow-2xs"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-foreground truncate">
                              {student?.name || m.student_id}
                            </span>
                            {isLeader && (
                              <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20">
                                <Crown className="h-3 w-3" /> Leader
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] font-mono text-muted-foreground mt-0.5">
                            {m.student_id} • {student?.email || 'No email registered'}
                          </p>

                          {/* GitHub link status badge */}
                          <div className="mt-1.5 flex items-center gap-1 text-[11px]">
                            {hasGithub ? (
                              <span className="inline-flex items-center gap-1 text-emerald-500 font-mono">
                                <CheckCircle2 className="h-3 w-3" />
                                @{student.github_username}
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-amber-500">
                                <AlertCircle className="h-3 w-3" />
                                GitHub Unlinked
                              </span>
                            )}
                          </div>
                        </div>

                        {!isLeader && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-destructive shrink-0"
                            onClick={() => handleRemoveMember(m.student_id)}
                            title="Remove student from team"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Add Member Section */}
              <form onSubmit={handleAddMember} className="pt-2 border-t border-border space-y-2">
                <label className="block font-medium text-foreground text-[11px]">
                  Add Student to Team
                </label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Student ID (e.g. IT210099)"
                    value={newStudentId}
                    onChange={(e) => setNewStudentId(e.target.value)}
                    className="h-8 text-xs font-mono"
                    required
                  />
                  <Button
                    type="submit"
                    size="sm"
                    className="h-8 text-xs"
                    disabled={addMemberMutation.isPending}
                  >
                    <UserPlus className="h-3.5 w-3.5 mr-1" />
                    Add
                  </Button>
                </div>
                <p className="text-[10px] text-muted-foreground">
                  Enforces academic constraint: student cannot already be in another team in this batch.
                </p>
              </form>
            </div>
          )}
        </div>

        <div className="pt-4 border-t border-border">
          <Button
            type="button"
            variant="outline"
            className="w-full text-xs"
            onClick={() => onOpenChange(false)}
          >
            Close Roster Drawer
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
