import TutorAvatar from './TutorAvatar.jsx'

const DOT_DELAYS = ['0ms', '150ms', '300ms']

export default function TypingIndicator() {
  return (
    <li className="flex items-center gap-2.5">
      <TutorAvatar />
      <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm bg-muted px-3.5 py-3">
        <span className="sr-only">The Tutor is typing</span>
        {DOT_DELAYS.map((delay) => (
          <span
            key={delay}
            className="h-1.5 w-1.5 rounded-full bg-muted-foreground/70 motion-safe:animate-bounce"
            style={{ animationDelay: delay }}
            aria-hidden="true"
          />
        ))}
      </div>
    </li>
  )
}
