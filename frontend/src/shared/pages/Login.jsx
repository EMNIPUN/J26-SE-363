import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, Layers, BarChart3, Bot, ShieldCheck } from 'lucide-react'
import { useAuth } from '../auth/useAuth.js'
import { DEMO_ACCOUNTS, findAccount } from '../auth/credentials.js'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import MentorLogo from '../components/MentorLogo.jsx'

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
      setError('Invalid email or password. Try one of the demo accounts below.')
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
    <div className="min-h-screen flex flex-col lg:flex-row bg-background">
      {/* Brand Panel */}
      <section className="lg:w-1/2 bg-muted/20 p-8 sm:p-12 lg:p-16 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-border">
        <div>
          <div className="mb-8">
            <MentorLogo size={42} showText={true} textClassName="text-xl" />
          </div>

          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold mb-4">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Multi-Agent Engineering Network</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground max-w-lg leading-tight">
            Task Orchestration, Learning &amp; Review.
          </h1>
          <p className="mt-4 text-base text-muted-foreground max-w-md leading-relaxed">
            MENTOR is a multi-agent engineering system that orchestrates software project tasks, evaluates student contributions, provides adaptive learning support, and performs security review.
          </p>
        </div>

        <ul className="mt-8 space-y-3.5 text-sm text-foreground/90 font-medium">
          <li className="flex items-center gap-3">
            <div className="p-1.5 rounded-md bg-primary/10 text-primary">
              <Layers className="h-4 w-4" />
            </div>
            <span><strong>Task Orchestration</strong> — Requirements &amp; project structuring</span>
          </li>
          <li className="flex items-center gap-3">
            <div className="p-1.5 rounded-md bg-primary/10 text-primary">
              <BarChart3 className="h-4 w-4" />
            </div>
            <span><strong>Evaluation</strong> — Student contributions &amp; performance</span>
          </li>
          <li className="flex items-center gap-3">
            <div className="p-1.5 rounded-md bg-primary/10 text-primary">
              <Bot className="h-4 w-4" />
            </div>
            <span><strong>Adaptive Learning</strong> — Intelligent AI Mentor assistance</span>
          </li>
          <li className="flex items-center gap-3">
            <div className="p-1.5 rounded-md bg-primary/10 text-primary">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <span><strong>Review</strong> — Automated software &amp; security review</span>
          </li>
        </ul>
      </section>

      {/* Form Panel */}
      <section className="flex-1 flex items-center justify-center p-6 sm:p-12">
        <Card className="w-full max-w-md shadow-md border-border bg-card">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-bold tracking-tight">Welcome back</CardTitle>
            <CardDescription>
              Sign in to continue to your dashboard.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">Email</label>
                <Input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@lms.edu"
                  autoComplete="username"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">Password</label>
                <Input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <Button type="submit" className="w-full" size="lg">
                Sign in
              </Button>
            </form>

            <div className="pt-4 border-t border-border">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2.5">
                Quick Demo Accounts
              </p>
              <div className="grid grid-cols-1 gap-2">
                {DEMO_ACCOUNTS.map((acc) => (
                  <button
                    key={acc.role}
                    type="button"
                    className="flex items-center justify-between p-2.5 rounded-lg border border-border bg-muted/30 hover:bg-accent hover:text-accent-foreground text-left transition-colors cursor-pointer text-xs"
                    onClick={() => fillDemo(acc)}
                  >
                    <span className="font-semibold capitalize text-foreground">{acc.role}</span>
                    <span className="text-muted-foreground font-mono">
                      {acc.email}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}

