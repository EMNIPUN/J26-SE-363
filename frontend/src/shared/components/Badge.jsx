import './Badge.css'

const TONES = ['neutral', 'primary', 'success', 'warning', 'danger']

export default function Badge({ tone = 'neutral', children }) {
  const t = TONES.includes(tone) ? tone : 'neutral'
  return <span className={`badge badge--${t}`}>{children}</span>
}
