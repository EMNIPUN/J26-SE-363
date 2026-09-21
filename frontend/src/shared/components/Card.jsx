import { Card as ShadcnCard } from '@/components/ui/card'

export default function Card({ className = '', children, ...props }) {
  return (
    <ShadcnCard className={`p-6 shadow-sm border border-border bg-card text-card-foreground ${className}`} {...props}>
      {children}
    </ShadcnCard>
  )
}

