import { useEffect, useState, type ReactNode } from 'react'
import { Check, Copy, Search, ShieldMinus, Users } from 'lucide-react'
import { adminAPI, getApiErrorMessage } from '../../api/client'
import type { SubscriberResponse } from '../../api/client'
import { DashboardLayout } from '../../components/layout/DashboardLayout'
import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/Card'
import { Input } from '../../components/ui/Input'
import { Modal } from '../../components/ui/Modal'
import { formatDate, formatDateTime } from '../../lib/format'

function DetailField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400">{label}</p>
      <div className="mt-1.5 break-words text-sm text-white">{children}</div>
    </div>
  )
}

function CopyableUsername({
  value,
  isCopied,
  onCopy,
  mode = 'table',
  valueClassName = 'break-all text-sm text-white',
}: {
  value: string
  isCopied: boolean
  onCopy: () => void
  mode?: 'table' | 'modal'
  valueClassName?: string
}) {
  if (mode === 'modal') {
    return (
      <div className="flex items-center gap-2">
        <span className="break-all text-sm text-white">{value}</span>
        <button
          type="button"
          className={`shrink-0 p-1 transition-colors ${
            isCopied ? 'text-emerald-300' : 'text-slate-300 hover:text-slate-100'
          }`}
          onClick={(event) => {
            event.stopPropagation()
            onCopy()
          }}
          title={isCopied ? 'Copied!' : 'Copy username'}
        >
          {isCopied ? <Check className="size-4" /> : <Copy className="size-4" />}
        </button>
      </div>
    )
  }

  return (
    <div className="flex min-w-0 items-center gap-2">
      <button
        type="button"
        className={`shrink-0 p-1 transition-colors ${
          isCopied ? 'text-emerald-300' : 'text-slate-300 hover:text-slate-100'
        }`}
        onClick={(event) => {
          event.stopPropagation()
          onCopy()
        }}
        title={isCopied ? 'Copied!' : 'Copy username'}
      >
        {isCopied ? <Check className="size-4" /> : <Copy className="size-4" />}
      </button>
      <div className={`min-w-0 ${valueClassName}`}>{value}</div>
    </div>
  )
}

function SubscriberDetailModal({
  subscriber,
  isRevoking,
  isTradingViewCopied,
  onClose,
  onCopyTradingView,
  onRevoke,
}: {
  subscriber: SubscriberResponse
  isRevoking: boolean
  isTradingViewCopied: boolean
  onClose: () => void
  onCopyTradingView: (subscriber: SubscriberResponse) => void
  onRevoke: (id: string) => void
}) {
  return (
    <Modal
      open
      onClose={onClose}
      titleLabel="Subscriber record"
      title={subscriber.discord_username}
      subtitle={<span className="font-mono text-xs text-slate-300">TV {subscriber.tradingview_username}</span>}
      maxWidthClassName="max-w-3xl"
      footer={
        <div className="flex justify-end">
          <Button
            type="button"
            variant="outline"
            isLoading={isRevoking}
            className="border-destructive/35 bg-destructive/10 text-destructive hover:bg-destructive/15"
            onClick={() => onRevoke(subscriber.id)}
          >
            <ShieldMinus className="mr-2 size-4" />
            Revoke access
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-4 rounded-2xl border border-white/10 bg-white/5 p-3">
          <div className="min-w-0">
            <p className="text-xs font-medium text-slate-400">Subscriber ID</p>
            <p className="mt-1 break-all text-sm text-white">{subscriber.id}</p>
          </div>
          <Badge variant={subscriber.is_active ? 'success' : 'warning'}>
            {subscriber.is_active ? 'Active' : 'Inactive'}
          </Badge>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <DetailField label="Discord ID">{subscriber.discord_id}</DetailField>
          <DetailField label="TradingView username">
            <CopyableUsername
              value={subscriber.tradingview_username}
              isCopied={isTradingViewCopied}
              onCopy={() => onCopyTradingView(subscriber)}
              mode="modal"
            />
          </DetailField>
          <DetailField label="Months paid">{subscriber.months_paid}</DetailField>
          <DetailField label="Email">{subscriber.email ?? 'No email on file'}</DetailField>
          <DetailField label="Expires">
            {subscriber.expires_at ? formatDate(subscriber.expires_at) : 'No expiry set'}
          </DetailField>
          <DetailField label="Created">{formatDateTime(subscriber.created_at)}</DetailField>
          <DetailField label="Referral code">
            {subscriber.owned_referral_code ?? 'No referral code'}
          </DetailField>
          <div className="xl:col-span-3">
            <DetailField label="Referral link">
              {subscriber.owned_referral_link ? (
                <span className="break-all text-slate-200">{subscriber.owned_referral_link}</span>
              ) : (
                'No referral link'
              )}
            </DetailField>
          </div>
        </div>
      </div>
    </Modal>
  )
}

export default function SubscribersPage() {
  const [subscribers, setSubscribers] = useState<SubscriberResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [activeOnly, setActiveOnly] = useState(false)
  const [revokeTarget, setRevokeTarget] = useState<string | null>(null)
  const [selectedSubscriberId, setSelectedSubscriberId] = useState<string | null>(null)
  const [copiedTradingViewSubscriberId, setCopiedTradingViewSubscriberId] = useState<string | null>(null)

  useEffect(() => {
    const fetchSubscribers = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await adminAPI.getSubscribers(1, search.trim() || undefined, activeOnly)
        setSubscribers(response.items || [])
      } catch (err) {
        setError(getApiErrorMessage(err, 'Failed to load subscribers'))
      } finally {
        setLoading(false)
      }
    }

    void fetchSubscribers()
  }, [search, activeOnly])

  useEffect(() => {
    if (!selectedSubscriberId) {
      return
    }

    if (!subscribers.some((subscriber) => subscriber.id === selectedSubscriberId)) {
      setSelectedSubscriberId(null)
    }
  }, [selectedSubscriberId, subscribers])

  useEffect(() => {
    if (!copiedTradingViewSubscriberId) {
      return
    }

    const timeout = window.setTimeout(() => {
      setCopiedTradingViewSubscriberId(null)
    }, 2000)

    return () => window.clearTimeout(timeout)
  }, [copiedTradingViewSubscriberId])

  const selectedSubscriber = subscribers.find((subscriber) => subscriber.id === selectedSubscriberId) ?? null

  const handleCopyTradingViewUsername = async (subscriber: SubscriberResponse) => {
    if (!subscriber.tradingview_username) {
      return
    }

    try {
      await navigator.clipboard.writeText(subscriber.tradingview_username)
      setCopiedTradingViewSubscriberId(subscriber.id)
    } catch {
      setError('Unable to copy TradingView username. Please copy it manually.')
    }
  }

  const handleRevoke = async (id: string) => {
    const confirmed = window.confirm('Revoke this subscription and remove active access?')
    if (!confirmed) {
      return
    }

    setRevokeTarget(id)
    setError(null)
    try {
      await adminAPI.revokeSubscriber(id)
      setSubscribers((current) => current.filter((subscriber) => subscriber.id !== id))
      if (selectedSubscriberId === id) {
        setSelectedSubscriberId(null)
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to revoke subscription'))
    } finally {
      setRevokeTarget(null)
    }
  }

  return (
    <DashboardLayout title="Subscribers">
      <div className="space-y-6">
        {error ? (
          <Alert variant="destructive" title="Subscriber view unavailable">
            {error}
          </Alert>
        ) : null}

        <Card className="border-white/10 bg-white/5">
          <CardHeader className="pb-4">
            <CardTitle className="text-white">Find subscribers</CardTitle>
            <CardDescription>Search by Discord, TradingView, or email.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-[1fr_auto_auto]">
              <div className="relative">
                <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-slate-500" />
                <Input
                  id="subscriber-search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search subscribers"
                  className="h-12 border-white/10 bg-slate-950/70 pl-11 text-white placeholder:text-slate-500"
                />
              </div>
              <Button
                type="button"
                variant={activeOnly ? 'default' : 'outline'}
                className={
                  activeOnly
                    ? 'h-12 bg-accent text-accent-foreground hover:bg-accent/90'
                    : 'h-12 border-white/10 bg-white/5 text-white hover:bg-white/10'
                }
                onClick={() => setActiveOnly((current) => !current)}
              >
                {activeOnly ? 'Active' : 'All'}
              </Button>
              <div className="rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 text-sm text-slate-300">
                {subscribers.length} member{subscribers.length === 1 ? '' : 's'}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-white/5">
          <CardHeader className="pb-4">
            <CardTitle className="text-white">Subscriber records</CardTitle>
            <CardDescription>Compact summary rows. Click a row to open details.</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="overflow-hidden rounded-[1.6rem] border border-white/10 bg-slate-950/55">
                <table className="w-full table-fixed border-collapse">
                  <thead className="bg-white/4">
                    <tr>
                      <th className="w-[22%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                        Member
                      </th>
                      <th className="w-[22%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                        TradingView
                      </th>
                      <th className="w-[12%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                        Status
                      </th>
                      <th className="w-[10%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                        Access
                      </th>
                      <th className="w-[17%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                        Expires
                      </th>
                      <th className="w-[17%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                        Added
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10">
                    {Array.from({ length: 4 }).map((_, index) => (
                      <tr key={index}>
                        <td className="px-5 py-5 align-top">
                          <div className="h-4 w-40 animate-pulse rounded bg-white/10" />
                        </td>
                        <td className="px-5 py-5 align-top">
                          <div className="h-7 w-20 animate-pulse rounded-full bg-white/10" />
                        </td>
                        <td className="px-5 py-5 align-top">
                          <div className="h-4 w-36 animate-pulse rounded bg-white/10" />
                        </td>
                        <td className="px-5 py-5 align-top">
                          <div className="h-4 w-12 animate-pulse rounded bg-white/10" />
                        </td>
                        <td className="px-5 py-5 align-top">
                          <div className="h-4 w-28 animate-pulse rounded bg-white/10" />
                        </td>
                        <td className="px-5 py-5 align-top">
                          <div className="h-4 w-32 animate-pulse rounded bg-white/10" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

            {!loading && subscribers.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 bg-white/3 p-10 text-center">
                <Users className="mx-auto size-8 text-slate-500" />
                <p className="mt-4 text-lg font-semibold text-white">No subscribers yet.</p>
                <p className="mt-2 text-sm text-muted-foreground">Try a different search.</p>
              </div>
            ) : null}

            {!loading && subscribers.length > 0 ? (
              <div className="overflow-hidden rounded-[1.6rem] border border-white/10 bg-slate-950/55">
                <table className="w-full table-fixed border-collapse">
                  <thead className="bg-white/4">
                    <tr>
                      <th className="w-[22%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                        Member
                      </th>
                      <th className="w-[22%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                        TradingView
                      </th>
                      <th className="w-[12%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                        Status
                      </th>
                      <th className="w-[10%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                        Access
                      </th>
                      <th className="w-[17%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                        Expires
                      </th>
                      <th className="w-[17%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                        Added
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10">
                    {subscribers.map((subscriber) => {
                      const isSelected = selectedSubscriberId === subscriber.id
                      const isTradingViewCopied = copiedTradingViewSubscriberId === subscriber.id

                      return (
                        <tr
                          key={subscriber.id}
                          role="button"
                          tabIndex={0}
                          aria-pressed={isSelected}
                          className={
                            isSelected
                              ? 'cursor-pointer bg-accent/10 transition-colors'
                              : 'cursor-pointer transition-colors hover:bg-white/[0.03]'
                          }
                          onClick={() => setSelectedSubscriberId(subscriber.id)}
                          onKeyDown={(event) => {
                            if (event.target !== event.currentTarget) {
                              return
                            }

                            if (event.key === 'Enter' || event.key === ' ') {
                              event.preventDefault()
                              setSelectedSubscriberId(subscriber.id)
                            }
                          }}
                        >
                          <td className="px-5 py-5 align-top">
                            <p className="truncate text-sm font-semibold text-white">
                              {subscriber.discord_username}
                            </p>
                          </td>
                          <td className="px-5 py-5 align-top">
                            <CopyableUsername
                              value={subscriber.tradingview_username}
                              isCopied={isTradingViewCopied}
                              onCopy={() => {
                                void handleCopyTradingViewUsername(subscriber)
                              }}
                              valueClassName="truncate text-sm font-semibold text-white"
                            />
                          </td>
                          <td className="px-5 py-5 align-top">
                            <Badge variant={subscriber.is_active ? 'success' : 'warning'}>
                              {subscriber.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </td>
                          <td className="px-5 py-5 align-top text-sm text-white">
                            {subscriber.months_paid}
                          </td>
                          <td className="px-5 py-5 align-top text-sm text-white">
                            {subscriber.expires_at ? formatDate(subscriber.expires_at) : 'No expiry'}
                          </td>
                          <td className="px-5 py-5 align-top text-sm text-slate-300">
                            {formatDateTime(subscriber.created_at)}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      {selectedSubscriber ? (
        <SubscriberDetailModal
          subscriber={selectedSubscriber}
          isRevoking={revokeTarget === selectedSubscriber.id}
          isTradingViewCopied={copiedTradingViewSubscriberId === selectedSubscriber.id}
          onClose={() => setSelectedSubscriberId(null)}
          onCopyTradingView={handleCopyTradingViewUsername}
          onRevoke={handleRevoke}
        />
      ) : null}
    </DashboardLayout>
  )
}
