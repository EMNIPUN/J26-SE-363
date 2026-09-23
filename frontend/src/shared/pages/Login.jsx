import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  Eye,
  EyeOff,
  Lock,
  Mail,
  ArrowRight,
  GraduationCap,
  UserCheck,
  Shield,
} from 'lucide-react'
import { useAuth } from '../auth/useAuth.js'
import { DEMO_ACCOUNTS, findAccount } from '../auth/credentials.js'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import MentorLogo from '../components/MentorLogo.jsx'
import ThemeToggle from '../components/ThemeToggle.jsx'

const ROLE_OPTIONS = [
  { role: 'student', label: 'Student', icon: GraduationCap },
  { role: 'instructor', label: 'Instructor', icon: UserCheck },
  { role: 'admin', label: 'Admin', icon: Shield },
]

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(true)
  const [selectedRole, setSelectedRole] = useState(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    setTimeout(() => {
      const account = findAccount(email, password)
      if (!account) {
        setError('Invalid email or password. Select a demo role above.')
        setIsLoading(false)
        return
      }
      login(account)
      navigate(`/${account.role}`, { replace: true })
    }, 200)
  }

  function handleSelectRole(roleName) {
    const acc = DEMO_ACCOUNTS.find((a) => a.role === roleName)
    if (!acc) return
    setSelectedRole(roleName)
    setEmail(acc.email)
    setPassword(acc.password)
    setError('')
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-background text-foreground">
      {/* ------------------------------------------------------------- */}
      {/* LEFT: Clean, Premium Brand Showcase                          */}
      {/* ------------------------------------------------------------- */}
      <section className="relative hidden lg:flex lg:w-[48%] xl:w-[50%] bg-zinc-950 text-white p-12 xl:p-16 flex-col justify-between overflow-hidden border-r border-border select-none">
        {/* Subtle grid background */}
        <div
          className="absolute inset-0 opacity-[0.07] pointer-events-none"
          style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, rgba(255,255,255,0.4) 1px, transparent 0)`,
            backgroundSize: '32px 32px',
          }}
        />

        {/* Ambient atmospheric glow - consistent soft white shading near logo in both themes */}
        <div className="absolute -top-32 -left-32 w-96 h-96 bg-white/[0.12] rounded-full blur-[128px] pointer-events-none" />
        <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-white/[0.04] rounded-full blur-[128px] pointer-events-none" />

        {/* Brand Header */}
        <div className="relative z-10 flex items-center gap-3">
          <MentorLogo size={38} showText={true} className="text-white" textClassName="text-white" />
        </div>

        {/* Value Proposition */}
        <div className="relative z-10 max-w-lg space-y-6 my-auto py-8">
          <h1 className="text-3xl xl:text-4xl font-extrabold tracking-tight text-white leading-tight">
            Intelligent project planning and continuous mentoring.
          </h1>

          <p className="text-base text-zinc-400 leading-relaxed font-normal">
            Streamlining software project tracking, automated quality gates, and real-time team mentoring into a single unified workspace.
          </p>

          {/* Testimonial / Highlight Card */}
          <div className="rounded-xl bg-white/[0.05] border border-white/10 p-5 backdrop-blur-sm space-y-3">
            <p className="text-sm text-zinc-300 italic leading-relaxed">
              &ldquo;MENTOR brings project requirements, team contributions, and intelligent tutoring together with seamless clarity.&rdquo;
            </p>
            <div className="flex items-center gap-3 pt-1 border-t border-white/5">
              <div className="h-7 w-7 rounded-full bg-primary/30 border border-white/20 flex items-center justify-center text-xs font-bold text-white">
                M
              </div>
              <div className="text-xs">
                <p className="font-semibold text-white">Engineering Workspace</p>
                <p className="text-zinc-500 text-[11px]">Continuous Quality Assurance</p>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Footer */}
        <div className="relative z-10 pt-4 border-t border-white/10 flex items-center justify-between text-xs text-zinc-500">
          <span>&copy; {new Date().getFullYear()} MENTOR. All rights reserved.</span>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* RIGHT: Professional Authentication Panel                     */}
      {/* ------------------------------------------------------------- */}
      <section className="flex-1 flex flex-col justify-between p-6 sm:p-10 lg:p-14 xl:p-16 bg-card/40">
        {/* Top Header / Theme Toggle */}
        <div className="flex items-center justify-between w-full">
          <div className="lg:hidden flex items-center gap-2">
            <MentorLogo size={32} showText={true} className="text-foreground" />
          </div>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>

        {/* Centered Sign-In Box */}
        <div className="w-full max-w-[400px] mx-auto my-auto space-y-6 py-6">
          <div className="space-y-1.5">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Sign in to MENTOR
            </h2>
            <p className="text-sm text-muted-foreground">
              Welcome back! Please enter your details to continue.
            </p>
          </div>

          {/* Quick Demo Role Selector */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-muted-foreground uppercase tracking-wider text-[11px]">
                Demo Role Quick Select
              </span>
              <span className="text-muted-foreground text-[11px]">One-click fill</span>
            </div>

            <div className="grid grid-cols-3 gap-2">
              {ROLE_OPTIONS.map((item) => {
                const Icon = item.icon
                const isSelected = selectedRole === item.role

                return (
                  <button
                    key={item.role}
                    type="button"
                    onClick={() => handleSelectRole(item.role)}
                    className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg border text-xs font-semibold transition-all duration-150 cursor-pointer outline-none ${
                      isSelected
                        ? 'border-primary bg-primary text-primary-foreground shadow-xs'
                        : 'border-border bg-card hover:bg-accent text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" strokeWidth={2} />
                    <span>{item.label}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Divider */}
          <div className="relative flex items-center justify-center">
            <div className="border-t border-border w-full" />
            <span className="bg-card px-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground absolute">
              or continue with email
            </span>
          </div>

          {/* Sign In Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground uppercase tracking-wider">
                Email address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    setSelectedRole(null)
                  }}
                  placeholder="name@organization.com"
                  autoComplete="username"
                  className="pl-10 h-10 bg-background/50 border-input"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-foreground uppercase tracking-wider">
                  Password
                </label>
                <span className="text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
                  Forgot password?
                </span>
              </div>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    setSelectedRole(null)
                  }}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className="pl-10 pr-10 h-10 bg-background/50 border-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs">
              <label className="flex items-center gap-2 cursor-pointer select-none text-muted-foreground hover:text-foreground">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-3.5 w-3.5 rounded border-border accent-primary cursor-pointer"
                />
                <span>Remember this device</span>
              </label>
            </div>

            {error && (
              <div className="flex items-center gap-2.5 p-3 text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded-lg animate-fade-rise">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <Button
              type="submit"
              disabled={isLoading}
              size="lg"
              className="w-full h-10 text-sm font-semibold cursor-pointer group shadow-xs transition-all duration-150"
            >
              <span>{isLoading ? 'Signing in...' : 'Sign in'}</span>
              {!isLoading && (
                <ArrowRight className="h-4 w-4 ml-1.5 transition-transform duration-150 group-hover:translate-x-0.5" />
              )}
            </Button>
          </form>
        </div>

        {/* Footer */}
        <footer className="w-full pt-4 border-t border-border flex flex-col sm:flex-row items-center justify-between text-xs text-muted-foreground gap-2">
          <span>&copy; {new Date().getFullYear()} MENTOR Platform. All rights reserved.</span>
          <span className="text-[11px] text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
            Privacy &amp; Terms
          </span>
        </footer>
      </section>
    </div>
  )
}



