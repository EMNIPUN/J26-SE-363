import PropTypes from 'prop-types'
import { CalendarRange } from 'lucide-react'
import { Select, SelectContent, SelectItem, SelectTrigger } from '@/components/ui/select'

const day = (iso) => (iso ? new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '')

/** The sprint picker: a styled menu (not the browser's own list) that shows each sprint's dates. */
export default function SprintSelect({ sprints, value, onChange }) {
  const last = sprints[sprints.length - 1]?.id
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger
        aria-label="Sprint"
        className="h-10 w-auto min-w-48 gap-3 rounded-xl border-border/80 bg-card px-3 text-sm font-medium shadow-sm transition-all hover:border-primary/50 hover:shadow data-[state=open]:border-primary data-[state=open]:ring-2 data-[state=open]:ring-primary/20"
      >
        {/* a div, not a span: the shared trigger clamps its direct span child to one line, which breaks a row of items */}
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10 text-primary"><CalendarRange className="h-3.5 w-3.5" aria-hidden="true" /></span>
          <span className="font-normal text-muted-foreground">Sprint</span>
          <span className="text-foreground">{value}</span>
        </div>
      </SelectTrigger>
      <SelectContent align="end" className="min-w-64 rounded-xl border-border/70 p-1.5 shadow-2xl">
        {sprints.map((s) => (
          <SelectItem key={s.id} value={s.id} className="cursor-pointer rounded-lg py-2 pl-9 pr-3 focus:bg-primary/10">
            <span className="flex flex-col gap-0.5 text-left">
              <span className="flex items-center gap-2 text-sm font-medium text-foreground">{s.id}{s.id === last && <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">latest</span>}</span>
              <span className="text-xs text-muted-foreground">{day(s.start)} to {day(s.end)}</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
SprintSelect.propTypes = { sprints: PropTypes.array.isRequired, value: PropTypes.string, onChange: PropTypes.func.isRequired }
