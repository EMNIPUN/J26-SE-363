import { Avatar as ShadcnAvatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useAvatarImage } from '../hooks/useAvatarImage.js'

function getInitials(name = '') {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')
}

/**
 * A person's picture, or their initials while it loads or when they have none. `picture` is what
 * the Core API sends: a web address (from their sign-in provider) or an API path (an upload).
 */
export default function Avatar({ name = '', size = 36, className = '', picture = null }) {
  const fromApi = useAvatarImage(picture)
  const src = typeof picture === 'string' && picture.startsWith('/') ? fromApi : picture

  return (
    <ShadcnAvatar
      className={`inline-flex items-center justify-center font-medium bg-primary/10 text-primary border border-border shrink-0 ${className}`}
      style={{ width: size, height: size, fontSize: size * 0.38 }}
    >
      {src && <AvatarImage src={src} alt="" referrerPolicy="no-referrer" />}
      <AvatarFallback className="bg-inherit text-inherit font-semibold text-xs">
        {getInitials(name)}
      </AvatarFallback>
    </ShadcnAvatar>
  )
}
