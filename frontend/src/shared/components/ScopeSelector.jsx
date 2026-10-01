import { useState, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { FolderKanban, Search, Check, ChevronDown, Users2 } from 'lucide-react'
import { useScope } from '../context/useScope.js'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Input } from '@/components/ui/input'

export default function ScopeSelector() {
  const navigate = useNavigate()
  const location = useLocation()
  const { groups, selectedGroupId, selectedGroup, setGroupId } = useScope()

  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')

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

  const handleSelectGroup = (group) => {
    setGroupId(group.id)
    setOpen(false)
    setSearch('')

    if (location.pathname.includes('/teams/')) {
      const newPath = location.pathname.replace(/\/teams\/[^/]+/, `/teams/${group.code}`)
      navigate(`${newPath}${location.search}`)
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`Current project: ${selectedGroup?.name || 'none'}. Change project`}
          title={selectedGroup?.projectTitle}
          className="flex h-10 min-w-0 max-w-[180px] lg:max-w-[260px] items-center gap-2 rounded-lg border border-border bg-background px-2.5 text-left text-xs transition-all duration-150 hover:bg-muted/60 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-ring group"
        >
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border bg-muted/50 text-muted-foreground">
            <FolderKanban className="h-3.5 w-3.5" />
          </div>

          <div className="min-w-0 leading-tight">
            <span className="hidden lg:block truncate font-semibold text-foreground">
              {selectedGroup?.name || 'Select project'}
            </span>
            <span className="block truncate font-mono text-[11px] font-semibold text-foreground lg:font-medium lg:text-muted-foreground">
              {selectedGroup?.code || 'Team'}
            </span>
          </div>

          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground group-hover:text-foreground transition-colors duration-150" />
        </button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={6}
        className="w-[min(92vw,420px)] p-0 shadow-lg border-border"
      >
        <div className="p-2.5 border-b border-border bg-muted/30">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search project or group..."
              className="h-8 pl-8 text-xs bg-background"
              autoFocus
            />
          </div>
        </div>

        <div className="max-h-72 overflow-y-auto p-1.5 space-y-1 column-scroll-contain">
          {filteredGroups.length === 0 ? (
            <div className="py-6 text-center text-xs text-muted-foreground">
              No matching projects found
            </div>
          ) : (
            filteredGroups.map((group) => {
              const isSelected = group.id === selectedGroupId
              return (
                <button
                  key={group.id}
                  type="button"
                  onClick={() => handleSelectGroup(group)}
                  className={`w-full text-left p-2 rounded-md text-xs transition-colors flex items-start justify-between gap-2 cursor-pointer ${
                    isSelected
                      ? 'bg-muted text-foreground font-medium'
                      : 'hover:bg-accent text-foreground'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="mb-0.5 flex items-center gap-2">
                      <span className="font-mono text-[10px] font-semibold text-muted-foreground">
                        {group.code}
                      </span>
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

        <div className="px-3 py-2 bg-muted/40 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
          <span>Current project context</span>
          <span className="inline-flex items-center gap-1 font-medium text-foreground">
            <Users2 className="h-3 w-3 text-muted-foreground" />
            {filteredGroups.length} groups
          </span>
        </div>
      </PopoverContent>
    </Popover>
  )
}
