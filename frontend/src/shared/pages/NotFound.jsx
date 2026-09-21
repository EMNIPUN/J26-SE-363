import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div style={{ padding: 56, textAlign: 'center' }}>
      <h1>404</h1>
      <p>That page doesn't exist yet.</p>
      <Link to="/">Back to home</Link>
    </div>
  )
}
