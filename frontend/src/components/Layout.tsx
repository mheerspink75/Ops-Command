import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import OrgSelector from './OrgSelector'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-accent/20 text-accent'
        : 'text-gray-400 hover:text-gray-200 hover:bg-surface-overlay'
    }`

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-56 bg-surface-raised border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-lg font-bold text-white">
            <span className="text-accent">Ops</span>Command
          </h1>
          <p className="text-xs text-gray-500 mt-1">Incident Response</p>
        </div>
        <nav className="flex-1 p-3 space-y-1" aria-label="Main navigation">
          <NavLink to="/" end className={navLinkClass}>
            Dashboard
          </NavLink>
          <NavLink to="/incidents" className={navLinkClass}>
            Incidents
          </NavLink>
          <NavLink to="/metrics" className={navLinkClass}>
            Metrics
          </NavLink>
        </nav>
        <div className="p-3 border-t border-gray-800">
          <div className="text-sm text-gray-400 mb-2">
            <span className="font-medium text-gray-300">{user?.username}</span>
            <br />
            <span className="text-xs">{user?.email}</span>
          </div>
          <button
            onClick={handleLogout}
            className="w-full btn-secondary text-sm"
            aria-label="Sign out"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 overflow-auto flex flex-col">
        <header className="border-b border-gray-800 bg-surface-raised/50 px-6 py-3 flex items-center justify-between">
          <OrgSelector />
          <span className="text-xs text-gray-500">
            {new Date().toLocaleDateString(undefined, {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            })}
          </span>
        </header>
        <main className="flex-1">
          <div className="p-6 max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
