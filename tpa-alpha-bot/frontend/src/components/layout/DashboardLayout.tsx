import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { BarChart3, Gift, LogOut, Menu, Settings, Shield, Users, X } from 'lucide-react'
import { cn } from '../../lib/utils'

interface NavItem {
  label: string
  href: string
  icon: ReactNode
}

const navItems: NavItem[] = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: <BarChart3 className="size-4" />,
  },
  {
    label: 'Subscribers',
    href: '/subscribers',
    icon: <Users className="size-4" />,
  },
  {
    label: 'Affiliates',
    href: '/affiliates',
    icon: <Gift className="size-4" />,
  },
  {
    label: 'Settings',
    href: '/settings',
    icon: <Settings className="size-4" />,
  },
]

function Sidebar({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) {
  const location = useLocation()

  const handleLogout = () => {
    localStorage.removeItem('admin_token')
    localStorage.removeItem('token_expires_at')
    window.location.href = '/login'
  }

  return (
    <>
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-[16rem] flex-col border-r border-white/10 bg-slate-950/96 backdrop-blur-xl transition-transform duration-300 lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="border-b border-white/10 px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-2xl bg-accent text-accent-foreground shadow-lg shadow-accent/20">
              <Shield className="size-5" />
            </div>
            <p className="text-base font-semibold tracking-[-0.02em] text-white">TPA Alpha</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {navItems.map((item) => {
            const isActive = location.pathname === item.href || (item.href === '/dashboard' && location.pathname === '/')

            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={onClose}
                className={cn(
                  'group flex items-center gap-3 rounded-2xl px-3.5 py-3 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-accent/12 text-white shadow-sm shadow-accent/10'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'
                )}
              >
                <span className={cn('transition-colors', isActive ? 'text-accent' : 'text-current')}>
                  {item.icon}
                </span>
                <span className="min-w-0 flex-1 truncate">{item.label}</span>
              </Link>
            )
          })}
        </nav>

        <div className="border-t border-white/10 p-3">
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-2xl px-3.5 py-3 text-left text-sm font-medium text-slate-400 transition-colors hover:bg-white/5 hover:text-white"
          >
            <LogOut className="size-4" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {open ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          aria-label="Close navigation"
          onClick={onClose}
        />
      ) : null}
    </>
  )
}

interface LayoutProps {
  children: ReactNode
  title?: string
  actions?: ReactNode
}

export function DashboardLayout({
  children,
  title,
  actions,
}: LayoutProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="fixed inset-0 bg-[linear-gradient(180deg,#05070b_0%,#070a0f_55%,#05070b_100%)]" />
      <div className="fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.012)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.012)_1px,transparent_1px)] bg-[size:72px_72px] opacity-8" />

      <Sidebar open={open} onClose={() => setOpen(false)} />

      <div className="relative min-w-0 overflow-x-hidden lg:ml-[16rem]">
        <header className="sticky top-0 z-20 border-b border-white/10 bg-slate-950/82 backdrop-blur-xl">
          <div className="flex min-h-[4.75rem] items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setOpen((current) => !current)}
                className="inline-flex size-10 items-center justify-center rounded-2xl border border-white/10 bg-white/6 text-white transition hover:bg-white/10 lg:hidden"
                aria-label={open ? 'Close navigation' : 'Open navigation'}
              >
                {open ? <X className="size-5" /> : <Menu className="size-5" />}
              </button>

              {title ? <h1 className="text-2xl font-semibold tracking-[-0.03em] text-white sm:text-[2rem]">{title}</h1> : null}
            </div>

            {actions ? <div className="flex shrink-0 items-center gap-3">{actions}</div> : null}
          </div>
        </header>

        <main className="relative min-w-0 overflow-x-hidden px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <div className="mx-auto w-full max-w-6xl min-w-0">{children}</div>
        </main>
      </div>
    </div>
  )
}
