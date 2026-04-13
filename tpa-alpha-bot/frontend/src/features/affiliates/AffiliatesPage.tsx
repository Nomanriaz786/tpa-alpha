import { useEffect, useState, type ReactNode } from 'react'
import { Gift, Plus, Search, Trash2 } from 'lucide-react'
import { adminAPI, getApiErrorMessage } from '../../api/client'
import type { AffiliateResponse, AffiliateDetailResponse, CreateAffiliateRequest, SubscriberResponse } from '../../api/client'
import { DashboardLayout } from '../../components/layout/DashboardLayout'
import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/Card'
import { ConfirmationDialog } from '../../components/ui/ConfirmationDialog'
import { Input } from '../../components/ui/Input'
import { Modal } from '../../components/ui/Modal'
import { formatDateTime, formatPercent } from '../../lib/format'

const initialAffiliate: CreateAffiliateRequest = {
  code: '',
  name: '',
  type: 'promo',
  discount_percent: 0,
  usage_limit: undefined,
  is_active: true,
}

function DetailField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400">{label}</p>
      <div className="mt-1.5 break-words text-sm text-white">{children}</div>
    </div>
  )
}

function AffiliateDetailModal({
  affiliate,
  detail,
  members,
  isDeleting,
  isLoadingDetail,
  detailError,
  onClose,
  onDelete,
  onMarkPaid,
}: {
  affiliate: AffiliateResponse
  detail: AffiliateDetailResponse | null
  members: SubscriberResponse[]
  isDeleting: boolean
  isLoadingDetail: boolean
  detailError: string | null
  onClose: () => void
  onDelete: (id: string) => void
  onMarkPaid?: (affiliateId: string) => Promise<void>
}) {
  const [markingPaid, setMarkingPaid] = useState(false)
  const [showMarkPaidConfirm, setShowMarkPaidConfirm] = useState(false)

  const handleMarkPaidClick = () => {
    setShowMarkPaidConfirm(true)
  }

  const handleMarkPaidConfirm = async () => {
    if (!onMarkPaid) return
    
    setMarkingPaid(true)
    try {
      await onMarkPaid(affiliate.id)
      setShowMarkPaidConfirm(false)
    } finally {
      setMarkingPaid(false)
    }
  }
  return (
    <Modal
      open
      onClose={onClose}
      titleLabel="Affiliate code details"
      title={affiliate.name || affiliate.code}
      subtitle={<span className="font-mono text-xs text-slate-300">{affiliate.code}</span>}
      maxWidthClassName="max-w-4xl"
      footer={
        <div className="flex items-center justify-between gap-3">
          {detail && (
            <Button
              type="button"
              variant={Number(detail.total_commissions_owed) > 0 ? "default" : "outline"}
              isLoading={markingPaid}
              disabled={!onMarkPaid || Number(detail.total_commissions_owed) === 0}
              onClick={handleMarkPaidClick}
              className="gap-2"
            >
              💰 Mark ${Number(detail.total_commissions_owed).toFixed(2)} as Paid
            </Button>
          )}
          <ConfirmationDialog
            open={showMarkPaidConfirm}
            title="Mark as Paid"
            message={`Mark all unpaid commissions (${Number(detail?.total_commissions_owed || 0).toFixed(2)}) as paid?`}
            confirmText="Mark Paid"
            isLoading={markingPaid}
            onConfirm={handleMarkPaidConfirm}
            onCancel={() => setShowMarkPaidConfirm(false)}
          />
          <div className="flex-1" />
          <Button
            type="button"
            variant="outline"
            isLoading={isDeleting}
            className="border-destructive/35 bg-destructive/10 text-destructive hover:bg-destructive/15"
            onClick={() => onDelete(affiliate.id)}
          >
            <Trash2 className="mr-2 size-4" />
            Delete code
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-4 rounded-2xl border border-white/10 bg-white/5 p-3">
          <div className="min-w-0">
            <p className="text-xs font-medium text-slate-400">Affiliate ID</p>
            <p className="mt-1 break-all text-sm text-white">{affiliate.id}</p>
          </div>
          <Badge variant={affiliate.is_active ? 'success' : 'warning'}>
            {affiliate.is_active ? 'Active' : 'Inactive'}
          </Badge>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <DetailField label="Type">
            {affiliate.type === 'member' ? 'Member link' : 'Promo code'}
          </DetailField>
          <DetailField label="Added">{formatDateTime(affiliate.created_at)}</DetailField>
          <DetailField label="Discount">{formatPercent(affiliate.discount_percent)}</DetailField>
          <DetailField label="Commission">{formatPercent(affiliate.commission_percent)}</DetailField>
          <DetailField label="Owner">
            {affiliate.discord_id ? `Owner ID ${affiliate.discord_id}` : 'Admin-managed code'}
          </DetailField>
          <div className="xl:col-span-3">
            <DetailField label="Affiliate link">
              {affiliate.affiliate_link ? (
                <span className="break-all text-slate-200">{affiliate.affiliate_link}</span>
              ) : (
                'No affiliate link available'
              )}
            </DetailField>
          </div>
          <div className="xl:col-span-3">
            <DetailField label="Payout Wallet">
              {affiliate.payout_wallet ? (
                <span className="break-all font-mono text-slate-200">{affiliate.payout_wallet}</span>
              ) : (
                <span className="text-slate-500">No payout wallet configured</span>
              )}
            </DetailField>
          </div>
          {affiliate.type === 'promo' && (
            <div className="xl:col-span-3">
              <DetailField label="Usage Limit">
                {affiliate.usage_limit ? (
                  <span className="font-mono text-slate-200">{affiliate.usage_limit} users max</span>
                ) : (
                  <span className="text-slate-500">Unlimited</span>
                )}
              </DetailField>
            </div>
          )}
        </div>

        {isLoadingDetail ? (
          <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
            <p className="text-sm text-slate-400">Loading commission data...</p>
          </div>
        ) : detailError ? (
          <div className="rounded-2xl border border-red-400/20 bg-red-400/10 p-4">
            <p className="text-sm text-red-300">⚠️ {detailError}</p>
          </div>
        ) : detail ? (
          <>
            <div className="border-t border-white/10 pt-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400 mb-3">
                {detail.type === 'promo' ? 'Promo Code Usage' : 'Commission Tracking'}
              </p>
              <div className="grid gap-3 sm:grid-cols-3">
                {detail.type === 'promo' ? (
                  <>
                    <div className="rounded-2xl border border-purple-400/20 bg-purple-400/10 p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-purple-400">Members Used</p>
                      <p className="mt-2 text-2xl font-bold text-purple-200">{detail.usage_count}</p>
                    </div>
                    <div className="rounded-2xl border border-indigo-400/20 bg-indigo-400/10 p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-indigo-400">Limit</p>
                      <p className="mt-2 text-2xl font-bold text-indigo-200">
                        {detail.usage_limit ? detail.usage_limit : '∞'}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-pink-400/20 bg-pink-400/10 p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-pink-400">Available</p>
                      <p className="mt-2 text-2xl font-bold text-pink-200">
                        {detail.usage_limit ? Math.max(0, detail.usage_limit - detail.usage_count) : '∞'}
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-emerald-400">Active Members</p>
                      <p className="mt-2 text-2xl font-bold text-emerald-200">{detail.active_members}</p>
                    </div>
                    <div className="rounded-2xl border border-yellow-400/20 bg-yellow-400/10 p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-yellow-400">Owed</p>
                      <p className="mt-2 text-xl font-bold text-yellow-200">${Number(detail.total_commissions_owed).toFixed(2)}</p>
                    </div>
                    <div className="rounded-2xl border border-blue-400/20 bg-blue-400/10 p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-blue-400">Paid</p>
                      <p className="mt-2 text-xl font-bold text-blue-200">${Number(detail.total_commissions_paid).toFixed(2)}</p>
                    </div>
                  </>
                )}
              </div>
            </div>

            {members.length > 0 ? (
              <div className="border-t border-white/10 pt-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400 mb-3">Members Using This Code ({members.length})</p>
                <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-950/40">
                  <table className="w-full text-sm">
                    <thead className="bg-white/5 border-b border-white/10">
                      <tr>
                        <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase text-slate-400">Discord</th>
                        <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase text-slate-400">TradingView</th>
                        <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase text-slate-400">Commission Wallet</th>
                        <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase text-slate-400">Status</th>
                        <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase text-slate-400">Expires</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/10">
                      {members.map((member) => (
                        <tr key={member.id} className="hover:bg-white/5">
                          <td className="px-3 py-2 text-xs text-white truncate">{member.discord_username}</td>
                          <td className="px-3 py-2 text-xs text-slate-300 truncate">{member.tradingview_username}</td>
                          <td className="px-3 py-2 text-xs text-slate-400 truncate font-mono">
                            {member.commission_wallet ? (
                              <div title={member.commission_wallet} className="space-y-0.5">
                                <div>{member.commission_wallet.slice(0, 6)}...{member.commission_wallet.slice(-4)}</div>
                                {member.network && <div className="text-[9px] text-slate-500">{member.network}</div>}
                              </div>
                            ) : (
                              <span className="text-slate-500">—</span>
                            )}
                          </td>
                          <td className="px-3 py-2">
                            <Badge variant={member.is_active ? 'success' : 'warning'} className="text-xs">
                              {member.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </td>
                          <td className="px-3 py-2 text-xs text-slate-400">
                            {member.expires_at ? new Date(member.expires_at).toLocaleDateString() : 'N/A'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </Modal>
  )
}

export default function AffiliatesPage() {
  const [affiliates, setAffiliates] = useState<AffiliateResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [newAffiliate, setNewAffiliate] = useState<CreateAffiliateRequest>(initialAffiliate)
  const [detailAffiliateId, setDetailAffiliateId] = useState<string | null>(null)
  const [detailData, setDetailData] = useState<AffiliateDetailResponse | null>(null)
  const [detailMembers, setDetailMembers] = useState<SubscriberResponse[]>([])
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAffiliates = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await adminAPI.getAffiliates(1, search.trim() || undefined)
        setAffiliates(response.items || [])
      } catch (err) {
        setError(getApiErrorMessage(err, 'Failed to load affiliates'))
      } finally {
        setLoading(false)
      }
    }

    void fetchAffiliates()
  }, [search])

  useEffect(() => {
    if (!detailAffiliateId) {
      return
    }

    if (!affiliates.some((affiliate) => affiliate.id === detailAffiliateId)) {
      setDetailAffiliateId(null)
    }
  }, [affiliates, detailAffiliateId])

  useEffect(() => {
    const fetchDetailData = async () => {
      if (!detailAffiliateId) {
        return
      }

      setLoadingDetail(true)
      setDetailError(null)
      try {
        const [detail, members] = await Promise.all([
          adminAPI.getAffiliateDetail(detailAffiliateId),
          adminAPI.getAffiliateMembers(detailAffiliateId),
        ])
        setDetailData(detail)
        setDetailMembers(members.items || [])
      } catch (err) {
        const errorMsg = getApiErrorMessage(err, 'Failed to load affiliate details')
        setDetailError(errorMsg)
        console.error('Failed to load affiliate detail:', err)
      } finally {
        setLoadingDetail(false)
      }
    }

    void fetchDetailData()
  }, [detailAffiliateId])

  const detailAffiliate = affiliates.find((affiliate) => affiliate.id === detailAffiliateId) ?? null

  const handleCreate = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const created = await adminAPI.createAffiliate({
        ...newAffiliate,
        code: newAffiliate.code.trim(),
        name: newAffiliate.name?.trim() || undefined,
      })
      setAffiliates((current) => [created, ...current])
      setDetailAffiliateId(created.id)
      setNewAffiliate(initialAffiliate)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to create affiliate'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleModalClose = () => {
    setDetailAffiliateId(null)
    setDetailData(null)
    setDetailMembers([])
    setDetailError(null)
  }

  const handleMarkPaid = async (affiliateId: string) => {
    setError(null)
    try {
      await adminAPI.markAffiliateCommissionsPaid(affiliateId)
      // Refresh the detail data
      const [detail, members] = await Promise.all([
        adminAPI.getAffiliateDetail(affiliateId),
        adminAPI.getAffiliateMembers(affiliateId),
      ])
      setDetailData(detail)
      setDetailMembers(members.items || [])
      setError(null)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to mark commissions as paid'))
    }
  }

  const handleDeleteClick = (id: string) => {
    setDeleteTarget(id)
    setShowDeleteConfirm(true)
  }

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return

    setIsDeleting(true)
    setError(null)
    try {
      await adminAPI.deleteAffiliate(deleteTarget)
      setAffiliates((current) => current.filter((affiliate) => affiliate.id !== deleteTarget))
      if (detailAffiliateId === deleteTarget) {
        setDetailAffiliateId(null)
        setDetailData(null)
        setDetailMembers([])
        setDetailError(null)
      }
      // Close the confirmation dialog immediately
      setShowDeleteConfirm(false)
      // Clear delete state after a short delay to allow UI to update
      setTimeout(() => {
        setDeleteTarget(null)
        setIsDeleting(false)
      }, 300)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to delete affiliate'))
      setIsDeleting(false)
    }
  }

  const handleDelete = (id: string) => {
    handleDeleteClick(id)
  }

  return (
    <DashboardLayout title="Affiliates">
      <div className="space-y-6">
        {error ? (
          <Alert variant="destructive" title="Affiliate action failed">
            {error}
          </Alert>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
          <Card className="min-w-0 border-white/10 bg-white/5">
            <CardHeader className="pb-4">
              <CardTitle className="text-white">Create promo code</CardTitle>
              <CardDescription>Admin-owned or member-linked.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  id="affiliate-code"
                  label="Code"
                  value={newAffiliate.code}
                  onChange={(event) =>
                    setNewAffiliate((current) => ({
                      ...current,
                      code: event.target.value.replace(/\s+/g, '').toUpperCase(),
                    }))
                  }
                  placeholder="TPA20"
                  className="h-12 border-white/10 bg-slate-950/70 text-white placeholder:text-slate-500"
                />
                <Input
                  id="affiliate-name"
                  label="Name"
                  value={newAffiliate.name}
                  onChange={(event) =>
                    setNewAffiliate((current) => ({ ...current, name: event.target.value }))
                  }
                  placeholder="Spring campaign"
                  className="h-12 border-white/10 bg-slate-950/70 text-white placeholder:text-slate-500"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  id="affiliate-discount"
                  label="Discount %"
                  type="number"
                  min="0"
                  max="100"
                  value={newAffiliate.discount_percent}
                  onChange={(event) =>
                    setNewAffiliate((current) => ({
                      ...current,
                      discount_percent: Number(event.target.value || 0),
                    }))
                  }
                  className="h-12 border-white/10 bg-slate-950/70 text-white"
                />
              </div>

              <Input
                id="affiliate-usage-limit"
                label="Usage Limit (max members, leave empty for unlimited)"
                type="number"
                min="1"
                value={newAffiliate.usage_limit || ''}
                onChange={(event) =>
                  setNewAffiliate((current) => ({
                    ...current,
                    usage_limit: event.target.value ? Number(event.target.value) : undefined,
                  }))
                }
                className="h-12 border-white/10 bg-slate-950/70 text-white"
              />

              <Button
                type="button"
                size="lg"
                isLoading={submitting}
                disabled={!newAffiliate.code.trim()}
                className="h-12 w-full bg-accent text-accent-foreground hover:bg-accent/90"
                onClick={handleCreate}
              >
                <Plus className="mr-2 size-4" />
                Create code
              </Button>
            </CardContent>
          </Card>

          <Card className="min-w-0 border-white/10 bg-white/5">
            <CardHeader className="pb-4">
              <CardTitle className="text-white">Affiliate codes</CardTitle>
              <CardDescription>Compact summary rows. Click a row to open details.</CardDescription>
            </CardHeader>
            <CardContent className="min-w-0 space-y-4">
              <div className="relative">
                <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-slate-500" />
                <Input
                  id="affiliate-search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search codes"
                  className="h-12 border-white/10 bg-slate-950/70 pl-11 text-white placeholder:text-slate-500"
                />
              </div>

              {loading ? (
                <div className="overflow-hidden rounded-[1.6rem] border border-white/10 bg-slate-950/55">
                  <table className="w-full table-fixed border-collapse">
                    <thead className="bg-white/4">
                      <tr>
                        <th className="w-[22%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                          Name
                        </th>
                        <th className="w-[16%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                          Code
                        </th>
                        <th className="w-[12%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                          Type
                        </th>
                        <th className="w-[12%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                          Members
                        </th>
                        <th className="w-[16%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                          Owed
                        </th>
                        <th className="w-[12%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/10">
                      {Array.from({ length: 3 }).map((_, index) => (
                        <tr key={index}>
                          <td className="px-5 py-5 align-top">
                            <div className="h-4 w-36 animate-pulse rounded bg-white/10" />
                          </td>
                          <td className="px-5 py-5 align-top">
                            <div className="h-4 w-24 animate-pulse rounded bg-white/10" />
                          </td>
                          <td className="px-5 py-5 align-top">
                            <div className="h-7 w-24 animate-pulse rounded-full bg-white/10" />
                          </td>
                          <td className="px-5 py-5 align-top">
                            <div className="h-4 w-12 animate-pulse rounded bg-white/10" />
                          </td>
                          <td className="px-5 py-5 align-top">
                            <div className="h-4 w-20 animate-pulse rounded bg-white/10" />
                          </td>
                          <td className="px-5 py-5 align-top">
                            <div className="h-7 w-20 animate-pulse rounded-full bg-white/10" />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}

              {!loading && affiliates.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-white/10 bg-white/3 p-10 text-center">
                  <Gift className="mx-auto size-8 text-slate-500" />
                  <p className="mt-4 text-lg font-semibold text-white">No codes yet.</p>
                  <p className="mt-2 text-sm text-muted-foreground">Create one to get started.</p>
                </div>
              ) : null}

              {!loading && affiliates.length > 0 ? (
                <div className="overflow-hidden rounded-[1.6rem] border border-white/10 bg-slate-950/55">
                  <table className="w-full table-fixed border-collapse">
                    <thead className="bg-white/4">
                      <tr>
                        <th className="w-[30%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                          Name
                        </th>
                        <th className="w-[25%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                          Code
                        </th>
                        <th className="w-[18%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                          Type
                        </th>
                        <th className="w-[27%] px-5 py-4 text-left text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/10">
                      {affiliates.map((affiliate) => {
                        const isActiveRow = detailAffiliateId === affiliate.id

                        return (
                          <tr
                            key={affiliate.id}
                            role="button"
                            tabIndex={0}
                            aria-pressed={isActiveRow}
                            className={
                              isActiveRow
                                ? 'cursor-pointer bg-accent/10 transition-colors'
                                : 'cursor-pointer transition-colors hover:bg-white/[0.03]'
                            }
                            onClick={() => setDetailAffiliateId(affiliate.id)}
                            onKeyDown={(event) => {
                              if (event.key === 'Enter' || event.key === ' ') {
                                event.preventDefault()
                                setDetailAffiliateId(affiliate.id)
                              }
                            }}
                          >
                            <td className="px-5 py-5 align-top">
                              <p className="truncate text-sm font-semibold text-white">
                                {affiliate.name || affiliate.code}
                              </p>
                            </td>
                            <td className="px-5 py-5 align-top">
                              <p className="truncate font-mono text-sm text-white">{affiliate.code}</p>
                            </td>
                            <td className="px-5 py-5 align-top">
                              <Badge variant="secondary" className="whitespace-nowrap">
                                {affiliate.type === 'member' ? 'Member link' : 'Promo code'}
                              </Badge>
                            </td>
                            <td className="px-5 py-5 align-top">
                              <Badge variant={affiliate.is_active ? 'success' : 'warning'} className="whitespace-nowrap">
                                {affiliate.is_active ? 'Active' : 'Inactive'}
                              </Badge>
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
      </div>

      {detailAffiliate ? (
        <AffiliateDetailModal
          affiliate={detailAffiliate}
          detail={detailData}
          members={detailMembers}
          isLoadingDetail={loadingDetail}
          detailError={detailError}
          isDeleting={isDeleting && deleteTarget === detailAffiliate.id}
          onClose={handleModalClose}
          onDelete={handleDelete}
          onMarkPaid={handleMarkPaid}
        />
      ) : null}

      <ConfirmationDialog
        open={showDeleteConfirm}
        title="Delete affiliate code"
        message={`Are you sure you want to delete this affiliate code? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDangerous={true}
        isLoading={isDeleting}
        onConfirm={handleDeleteConfirm}
        onCancel={() => {
          if (!isDeleting) {
            setShowDeleteConfirm(false)
            setDeleteTarget(null)
          }
        }}
      />
    </DashboardLayout>
  )
}
