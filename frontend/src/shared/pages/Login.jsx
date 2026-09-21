import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GraduationCap, BookOpen, BarChart3, Bot, ShieldCheck, AlertCircle } from 'lucide-react'
import { useAuth } from '../auth/useAuth.js'
import { DEMO_ACCOUNTS, findAccount } from '../auth/credentials.js'
import Button from '../components/Button.jsx'
import './Login.css'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    const account = findAccount(email, password)
    if (!account) {
      setError('Invalid email or password. Try one of the demo accounts on the right.')
      return
    }
    setError('')
    login(account)
    navigate(`/${account.role}`, { replace: true })
  }

  function fillDemo(account) {
    setEmail(account.email)
    setPassword(account.password)
    setError('')
  }

  return (
    <div className="login">
      <section className="login__brand-panel">
        <div className="login__brand">
          <GraduationCap size={26} strokeWidth={2.2} />
          <span>EduFlow</span>
        </div>
        <h1 className="login__brand-title">
          One learning platform for<br />the whole capstone team.
        </h1>
        <p className="login__brand-subtitle">
          Requirements planning, performance tracking, an AI tutor and automated security review —
          built by four teammates as one consistent product.
        </p>
        <ul className="login__feature-list">
          <li>
            <BookOpen size={18} strokeWidth={2} /> Project Planning &amp; Requirements
          </li>
          <li>
            <BarChart3 size={18} strokeWidth={2} /> Performance Assessment
          </li>
          <li>
            <Bot size={18} strokeWidth={2} /> Adaptive AI Tutor
          </li>
          <li>
            <ShieldCheck size={18} strokeWidth={2} /> AEGIS Security Review
          </li>
        </ul>
      </section>

      <section className="login__form-panel">
        <div className="login__form-card">
          <h2>Welcome back</h2>
          <p className="login__form-subtitle">Sign in to continue to your dashboard.</p>

          <form onSubmit={handleSubmit} className="login__form">
            <label className="login__field">
              <span>Email</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@lms.edu"
                autoComplete="username"
              />
            </label>
            <label className="login__field">
              <span>Password</span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </label>

            {error && (
              <p className="login__error">
                <AlertCircle size={15} strokeWidth={2} />
                {error}
              </p>
            )}

            <Button type="submit" className="btn--full" size="lg">
              Sign in
            </Button>
          </form>

          <div className="login__demo">
            <p className="login__demo-title">Demo accounts</p>
            {DEMO_ACCOUNTS.map((acc) => (
              <button key={acc.role} type="button" className="login__demo-account" onClick={() => fillDemo(acc)}>
                <span className="login__demo-role">{acc.role}</span>
                <span className="login__demo-creds">
                  {acc.email} / {acc.password}
                </span>
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
