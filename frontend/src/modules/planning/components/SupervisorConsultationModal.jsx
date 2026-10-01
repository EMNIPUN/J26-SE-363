import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'
import { UserCheck, Calendar, Clock, MapPin, Mail, Send, CheckCircle2 } from 'lucide-react'
import Badge from '../../../shared/components/Badge.jsx'
import AvatarComp from '../../../shared/components/Avatar.jsx'
import { COURSE_INFO } from '../data/lmsAcademicData.js'

export default function SupervisorConsultationModal({ open, onOpenChange, requirements = [] }) {
  const [topic, setTopic] = useState('DART Arbitration & Scope Refinement')
  const [selectedReq, setSelectedReq] = useState('REQ-104')
  const [slot, setSlot] = useState('Tue 14:30 - 15:00')
  const [notes, setNotes] = useState(
    'We would like supervisor guidance on resolving the compound requirement flag (REQ-104) and splitting it into atomic user stories before the Sprint 5 freeze.',
  )
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    setSubmitting(true)

    setTimeout(() => {
      setSubmitting(false)
      toast.success('Consultation request sent to Dr. Amara Silva', {
        description: `Scheduled for ${slot} · Agenda confirmed. Calendar invitation dispatched.`,
      })
      onOpenChange(false)
    }, 600)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[540px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded bg-primary/10 text-primary">
              <UserCheck className="h-4 w-4" />
            </span>
            <DialogTitle className="text-lg font-bold">Academic Supervisor Consultation</DialogTitle>
          </div>
          <DialogDescription className="text-xs">
            Schedule an advisory session or request formal rubric sign-off with your designated supervisor.
          </DialogDescription>
        </DialogHeader>

        {/* Supervisor Profile Card */}
        <div className="p-3.5 rounded-xl border border-border bg-muted/30 flex items-start gap-3.5 my-1">
          <AvatarComp name={COURSE_INFO.supervisor.name} size={42} className="ring-2 ring-primary/20 shrink-0" />
          <div className="min-w-0 flex-1 text-xs">
            <div className="flex items-center justify-between gap-2">
              <p className="font-bold text-foreground text-sm">{COURSE_INFO.supervisor.name}</p>
              <Badge tone="success" className="text-[10px] px-1.5 py-0">
                Office Hours Active
              </Badge>
            </div>
            <p className="text-muted-foreground">{COURSE_INFO.supervisor.title}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-2 gap-y-1 mt-2 text-[11px] text-muted-foreground/90">
              <span className="flex items-center gap-1.5">
                <MapPin className="h-3 w-3 text-primary" /> {COURSE_INFO.supervisor.office}
              </span>
              <span className="flex items-center gap-1.5">
                <Mail className="h-3 w-3 text-primary" /> {COURSE_INFO.supervisor.email}
              </span>
              <span className="flex items-center gap-1.5 sm:col-span-2">
                <Clock className="h-3 w-3 text-primary" /> {COURSE_INFO.supervisor.officeHours}
              </span>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          <div>
            <label className="font-semibold text-foreground block mb-1">Consultation Topic</label>
            <Input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., SRS Quality Gate Review, DART Arbitration, Sprint Sizing"
              className="text-xs h-9"
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="font-semibold text-foreground block mb-1">Target Requirement (Optional)</label>
              <Select value={selectedReq} onValueChange={setSelectedReq}>
                <SelectTrigger className="text-xs h-9">
                  <SelectValue placeholder="Select requirement" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">General Architecture / Process</SelectItem>
                  {requirements.map((r) => (
                    <SelectItem key={r.id} value={r.id}>
                      {r.id}: {r.title.slice(0, 30)}...
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="font-semibold text-foreground block mb-1">Preferred Time Slot</label>
              <Select value={slot} onValueChange={setSlot}>
                <SelectTrigger className="text-xs h-9">
                  <SelectValue placeholder="Select available slot" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Tue 14:00 - 14:30">Tuesday · 14:00 - 14:30</SelectItem>
                  <SelectItem value="Tue 14:30 - 15:00">Tuesday · 14:30 - 15:00</SelectItem>
                  <SelectItem value="Thu 14:00 - 14:30">Thursday · 14:00 - 14:30</SelectItem>
                  <SelectItem value="Thu 15:00 - 15:30">Thursday · 15:00 - 15:30</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <label className="font-semibold text-foreground block mb-1">Meeting Agenda &amp; Questions</label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Detail the specific questions, architecture decisions, or arbitration conflicts you need advice on..."
              rows={3}
              className="text-xs leading-relaxed"
              required
            />
          </div>

          <div className="p-2.5 rounded-lg bg-primary/5 border border-primary/10 text-[11px] text-muted-foreground flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
            <span>
              All 4 team members of Group 07 will receive an automatic calendar invite upon supervisor confirmation.
            </span>
          </div>

          <DialogFooter className="pt-2 gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              className="text-xs cursor-pointer"
            >
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={submitting} className="text-xs cursor-pointer gap-1.5">
              <Send className="h-3.5 w-3.5" />
              {submitting ? 'Sending Request...' : 'Confirm Consultation Request'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
