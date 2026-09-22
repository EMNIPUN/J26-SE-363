import { Avatar as ShadcnAvatar, AvatarFallback } from '@/components/ui/avatar'

function getInitials(name = '') {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')
}

export default function Avatar({ name = '', size = 36, className = '' }) {
  return (
    <ShadcnAvatar
      className={`inline-flex items-center justify-center font-medium bg-primary/10 text-primary border border-border shrink-0 ${className}`}
      style={{ width: size, height: size, fontSize: size * 0.38 }}
    >
      <AvatarFallback className="bg-primary/10 text-primary font-semibold text-xs">
        {getInitials(name)}
      </AvatarFallback>
    </ShadcnAvatar>
  )
}

