import { useState } from 'react'
import PropTypes from 'prop-types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { assessmentApi } from './assessmentApi.js'

const visible = (field, answers) => !field.visible_if || answers[field.visible_if.field] === field.visible_if.equals

export default function ReviewForm({ review, onChanged }) {
  const [answers, setAnswers] = useState({})
  const [busy, setBusy] = useState(false)
  const set = (id, value) => setAnswers((old) => ({ ...old, [id]: value }))
  const submit = async () => {
    setBusy(true)
    try { await assessmentApi.answer(review.id, answers); onChanged?.() } finally { setBusy(false) }
  }
  return <div className="space-y-3">
    {(review.form?.blocks || []).map((block, i) => <div key={i} className="rounded border p-2 text-sm">
      {block.title && <p className="font-medium">{block.title}</p>}
      {block.type === 'facts' && block.items?.map((item) => <p key={item.label} className="text-muted-foreground">{item.label}: {item.value}</p>)}
      {block.type === 'note' && <p>{block.text}</p>}
    </div>)}
    {(review.form?.fields || []).filter((f) => visible(f, answers)).map((field) => <label key={field.id} className="block space-y-1 text-sm">
      <span>{field.label}{field.required && ' *'}</span>
      {field.type === 'author_map' ? <div className="space-y-1">{(field.authors || []).map((author, i) => <div key={author.author} className="flex gap-2 items-center"><span className="flex-1">{author.author}</span><select className="rounded border bg-background p-1" value={answers[field.id]?.[i]?.student_id || ''} onChange={(e) => { const next = [...(answers[field.id] || [])]; next[i] = { author: author.author, student_id: e.target.value }; set(field.id, next) }}><option value="">Unmapped</option>{(field.students || []).map((student) => <option key={student.id} value={student.id}>{student.name}</option>)}</select></div>)}</div> :
        field.type === 'choice' ? <select className="w-full rounded border bg-background p-2" value={answers[field.id] || ''} onChange={(e) => set(field.id, e.target.value)}>
        <option value="">Choose…</option>{field.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select> : field.type === 'multi_choice' ? <div className="flex flex-wrap gap-2">{field.options?.map((o) => <label key={o.value} className="flex items-center gap-1"><input type="checkbox" checked={(answers[field.id] || []).includes(o.value)} onChange={(e) => set(field.id, e.target.checked ? [...(answers[field.id] || []), o.value] : (answers[field.id] || []).filter((v) => v !== o.value))} />{o.label}</label>)}</div> :
        field.type === 'textarea' ? <Textarea value={answers[field.id] || ''} placeholder={field.placeholder} onChange={(e) => set(field.id, e.target.value)} /> :
        field.type === 'confirm' ? <input type="checkbox" checked={!!answers[field.id]} onChange={(e) => set(field.id, e.target.checked)} /> :
          <Input type={field.type === 'mark' || field.type === 'number' || field.type === 'slider' ? 'number' : 'text'} min={field.min} max={field.max} value={answers[field.id] ?? ''} onChange={(e) => set(field.id, field.type === 'mark' || field.type === 'number' ? Number(e.target.value) : e.target.value)} />}
    </label>)}
    <Button size="sm" disabled={busy} onClick={submit}>Submit answer</Button>
  </div>
}
ReviewForm.propTypes = { review: PropTypes.object, onChanged: PropTypes.func }
