import { useEffect, useState } from 'react'
import {
  DollarSign,
  FolderClock,
  TrendingUp,
  UserCheck,
  Users,
} from 'lucide-react'
import { adminAPI } from '../../api/client'
import type { DashboardResponse } from '../../api/client'
import { DashboardLayout } from '../../components/layout/DashboardLayout'
import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/Card'
import { formatCurrency, formatDateTime } from '../../lib/format'

function MetricCard({
  title,
  value,
  icon,
}: {
  title: string
  value: string
  icon: React.ReactNode
}) {
  return (
    <Card className="border-white/10 bg-white/5 shadow-xl shadow-black/10">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
              {title}
            </p>
            <p className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-white">{value}</p>
          </div>
          <div className="flex size-12 items-center justify-center rounded-2xl border border-accent/20 bg-accent/12 text-accent">
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const response = await adminAPI.getDashboard()
        setData(response)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard')
      } finally {
        setLoading(false)
      }
    }

    void fetchDashboard()
  }, [])

  const retentionRate =
    data && data.stats.total_subscribers > 0
      ? Math.round((data.stats.active_subscribers / data.stats.total_subscribers) * 100)
      : 0

  return (
    <DashboardLayout
      title="Dashboard"
      actions={
        <Button
          type="button"
          variant="outline"
          className="border-white/10 bg-white/6 text-white hover:bg-white/10"
          onClick={() => window.location.reload()}
        >
          Refresh data
        </Button>
      }
    >
      {loading ? (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="h-44 animate-pulse rounded-[1.75rem] border border-white/10 bg-white/5"
            />
          ))}
        </div>
      ) : null}

      {error ? (
        <Alert variant="destructive" title="Dashboard unavailable" className="max-w-3xl">
          {error}
        </Alert>
      ) : null}

      {!loading && !error && data ? (
        <div className="space-y-8">
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              title="Total members"
              value={String(data.stats.total_subscribers)}
              icon={<Users className="size-5" />}
            />
            <MetricCard
              title="Active access"
              value={String(data.stats.active_subscribers)}
              icon={<UserCheck className="size-5" />}
            />
            <MetricCard
              title="30-day revenue"
              value={formatCurrency(data.stats.monthly_revenue_usd)}
              icon={<DollarSign className="size-5" />}
            />
            <MetricCard
              title="Unpaid commissions"
              value={formatCurrency(data.stats.unpaid_commissions_usd)}
              icon={<FolderClock className="size-5" />}
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <Card className="border-white/10 bg-white/5">
              <CardHeader className="pb-4">
                <CardTitle className="text-white">Recent subscriber activity</CardTitle>
                <CardDescription>Latest member records.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {data.recent_subscribers.length > 0 ? (
                  data.recent_subscribers.map((subscriber) => (
                    <div
                      key={subscriber.id}
                      className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-slate-950/55 p-4 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="space-y-1">
                        <p className="font-semibold text-white">{subscriber.discord_username}</p>
                        <p className="text-sm text-slate-300">
                          TradingView: {subscriber.tradingview_username}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Added {formatDateTime(subscriber.created_at)}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant={subscriber.is_active ? 'success' : 'warning'}>
                          {subscriber.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {subscriber.months_paid} month{subscriber.months_paid === 1 ? '' : 's'}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl border border-dashed border-white/10 bg-white/3 p-8 text-center text-sm text-muted-foreground">
                    No subscriber records yet.
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="space-y-6">
              <Card className="border-white/10 bg-white/5">
                <CardHeader className="pb-4">
                  <CardTitle className="text-white">Health indicators</CardTitle>
                  <CardDescription>Quick signals.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-2xl border border-white/10 bg-slate-950/55 p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">Retention</p>
                        <p className="mt-2 text-2xl font-black text-white">{retentionRate}%</p>
                      </div>
                      <TrendingUp className="size-5 text-accent" />
                    </div>
                    <div className="mt-4 h-2 rounded-full bg-white/10">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-accent to-primary"
                        style={{ width: `${Math.min(retentionRate, 100)}%` }}
                      />
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-slate-950/55 p-4">
                    <p className="text-sm text-muted-foreground">Revenue per member</p>
                    <p className="mt-2 text-2xl font-black text-white">
                      {formatCurrency(
                        data.stats.total_subscribers > 0
                          ? data.stats.monthly_revenue_usd / data.stats.total_subscribers
                          : 0
                      )}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">Last 30 days.</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      ) : null}
    </DashboardLayout>
  )
}
