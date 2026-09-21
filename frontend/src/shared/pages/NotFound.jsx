import { Link } from 'react-router-dom'
import Button from '../components/Button.jsx'

export default function NotFound() {
  return (
    <div style={{ minHeight: '60svh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, textAlign: 'center' }}>
      <h1 style={{ fontSize: 48 }}>404</h1>
      <p style={{ color: 'var(--color-text-muted)' }}>That page doesn't exist yet.</p>
      <Button as={Link} to="/" size="md">
        Back to home
      </Button>
    </div>
  )
}
