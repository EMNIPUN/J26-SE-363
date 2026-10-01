import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Bell, ArrowRight, ShieldAlert, CheckCircle2, Info, MessageSquare } from 'lucide-react'
import Card from '../../../shared/components/Card.jsx'
import Badge from '../../../shared/components/Badge.jsx'
import AvatarComp from '../../../shared/components/Avatar.jsx'
import { SUPERVISOR_NOTICES, COURSE_INFO } from '../data/lmsAcademicData.js'

export default function SupervisorNoticeBoard({ onConsultClick }) {
  const [notices] = useState(SUPERVISOR_NOTICES)

  return (
    <Card className="p-5 flex flex-col">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="p-1 rounded bg-primary/10 text-primary">
            <Bell className="h-4 w-4" />
          </span>
          <h3 className="text-base font-semibold text-foreground">Academic Guidance &amp; Notices</h3>
        </div>
        <button
          type="button"
          onClick={onConsultClick}
          className="text-xs font-medium text-primary hover:underline inline-flex items-center gap-1 cursor-pointer"
        >
          <MessageSquare className="h-3.5 w-3.5" /> Book Advisory
        </button>
      </div>

      <div className="space-y-3 flex-1">
        {notices.map((n) => {
          const isCritical = n.type === 'critical'
          const isSuccess = n.type === 'success'

          return (
            <div
              key={n.id}
              className={`p-3 rounded-xl border transition-all ${
                isCritical
                  ? 'border-amber-500/30 bg-amber-500/5'
                  : isSuccess
                    ? 'border-emerald-500/25 bg-emerald-500/5'
                    : 'border-border/60 bg-muted/20'
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-1.5">
                  {isCritical ? (
                    <ShieldAlert className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
                  ) : isSuccess ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  ) : (
                    <Info className="h-3.5 w-3.5 text-primary shrink-0" />
                  )}
                  <span className="text-xs font-bold text-foreground">{n.title}</span>
                </div>
                <Badge
                  tone={isCritical ? 'warning' : isSuccess ? 'success' : 'neutral'}
                  className="text-[10px] px-1.5 py-0"
                >
                  {n.author}
                </Badge>
              </div>

              <p className="text-xs text-foreground/90 leading-relaxed mb-2">{n.content}</p>

              <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t border-border/40">
                <span>{n.date}</span>
                {n.actionUrl && (
                  <Link
                    to={n.actionUrl}
                    className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-1"
                  >
                    {n.actionText} <ArrowRight className="h-3 w-3" />
                  </Link>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
