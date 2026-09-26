import { useState, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Users2, Search, Check, ChevronDown, Sparkles } from 'lucide-react'
import { useScope } from '../context/useScope.js'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

export default function ScopeSelector() {
  const navigate = useNavigate()
  const location = useLocation()

  const {
    isStudent,
    groups,
    selectedGroupId,
    selectedGroup,
    setGroupId,
  } = useScope()

  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')

  // Filter groups by code, name, or project title
  const filteredGroups = useMemo(() => {
    if (!search.trim()) return groups
    const query = search.toLowerCase()
    return groups.filter(
      (g) =>
        g.code?.toLowerCase().includes(query) ||
        g.name?.toLowerCase().includes(query) ||
        g.projectTitle?.toLowerCase().includes(query),
    )
  }, [groups, search])

  // -------------------------------------------------------------
  // Student View: Clean, non-interactive active team badge
  // -------------------------------------------------------------
  if (isStudent) {
    return (
      <div className="hidden sm:inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary border border-primary/20 text-xs font-semibold shadow-2xs">
        <Users2 className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate max-w-[200px]">
          {selectedGroup?.code || 'Team'} — {selectedGroup?.name || 'My Project'}
        </span>
      </div>
    )
  }

  // -------------------------------------------------------------
  // Instructor / Admin View: Searchable Team Selector Dropdown
  // -------------------------------------------------------------
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Select Active Team"
          className="flex items-center gap-2 h-9 px-3 rounded-lg border border-border bg-card/90 hover:bg-accent hover:text-accent-foreground text-xs font-medium transition-all duration-150 cursor-pointer shadow-2xs group"
        >
          <div className="flex h-5 w-5 items-center justify-center rounded-md bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
            <Users2 className="h-3.5 w-3.5" />
          </div>

          <div className="flex items-center gap-1.5 text-left">
            <span className="font-semibold text-foreground">
              {selectedGroup?.code || 'Select Team'}
            </span>
            <span className="hidden lg:inline text-muted-foreground font-normal truncate max-w-[150px]">
              • {selectedGroup?.name || ''}
            </span>
          </div>

          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground group-hover:text-foreground transition-transform duration-150" />
        </button>
      </PopoverTrigger>

      <PopoverContent
        align="start"
        sideOffset={6}
        className="w-80 sm:w-96 p-0 shadow-lg border-border"
      >
        {/* Search Header */}
        <div className="p-2.5 border-b border-border bg-muted/30">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search group code or project..."
              className="h-8 pl-8 text-xs bg-background"
              autoFocus
            />
          </div>
        </div>

        {/* Groups List */}
        <div className="max-h-72 overflow-y-auto p-1.5 space-y-1 column-scroll-contain">
          {filteredGroups.length === 0 ? (
            <div className="py-6 text-center text-xs text-muted-foreground">
              No matching research teams found
            </div>
          ) : (
            filteredGroups.map((group) => {
              const isSelected = group.id === selectedGroupId
              return (
                <button
                  key={group.id}
                  type="button"
                  onClick={() => {
                    setGroupId(group.id)
                    setOpen(false)
                    setSearch('')
                    if (location.pathname.includes('/teams/')) {
                      const newPath = location.pathname.replace(/\/teams\/[^/]+/, `/teams/${group.code}`)
                      navigate(`${newPath}${location.search}`)
                    }
                  }}
                  className={`w-full text-left p-2 rounded-md text-xs transition-colors flex items-start justify-between gap-2 cursor-pointer ${
                    isSelected
                      ? 'bg-primary/10 text-primary font-medium border border-primary/20'
                      : 'hover:bg-accent text-foreground'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <Badge
                        variant={isSelected ? 'default' : 'secondary'}
                        className="text-[10px] px-1.5 py-0 font-mono font-semibold"
                      >
                        {group.code}
                      </Badge>
                      <span className="font-semibold truncate">
                        {group.name}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground line-clamp-1">
                      {group.projectTitle}
                    </p>
                  </div>

                  {isSelected && (
                    <Check className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                  )}
                </button>
              )
            })
          )}
        </div>

        {/* Footer info */}
        <div className="px-3 py-2 bg-muted/40 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
          <span>Active Supervised Cohort</span>
          <span className="inline-flex items-center gap-1 font-medium text-foreground">
            <Sparkles className="h-3 w-3 text-amber-500" />
            2026 Batch
          </span>
        </div>
      </PopoverContent>
    </Popover>
  )
}
