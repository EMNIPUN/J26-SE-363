import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { GraduationCap, Search, Bell, LogOut, ChevronDown } from 'lucide-react'
import { useAuth } from '../auth/useAuth.js'
import Avatar from '../components/Avatar.jsx'
import Badge from '../components/Badge.jsx'
import './TopNavbar.css'

const ROLE_TONE = { student: 'primary', instructor: 'success', admin: 'warning' }

export default function TopNavbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    function onClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="top-navbar">
      <div className="top-navbar__brand">
        <GraduationCap size={22} strokeWidth={2.2} />
        <span>EduFlow</span>
      </div>

      <div className="top-navbar__search">
        <Search size={16} strokeWidth={2} />
        <input type="text" placeholder="Search projects, students, requirements..." />
      </div>

      <div className="top-navbar__right">
        <button type="button" className="top-navbar__icon-btn" aria-label="Notifications">
          <Bell size={18} strokeWidth={2} />
          <span className="top-navbar__dot" />
        </button>

        <div className="top-navbar__menu" ref={menuRef}>
          <button type="button" className="top-navbar__user" onClick={() => setMenuOpen((o) => !o)}>
            <Avatar name={user?.name} size={32} />
            <div className="top-navbar__user-info">
              <span className="top-navbar__user-name">{user?.name}</span>
              <Badge tone={ROLE_TONE[user?.role] ?? 'neutral'}>{user?.role}</Badge>
            </div>
            <ChevronDown size={15} strokeWidth={2} />
          </button>

          {menuOpen && (
            <div className="top-navbar__dropdown">
              <button type="button" className="top-navbar__dropdown-item" onClick={handleLogout}>
                <LogOut size={16} strokeWidth={2} />
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
