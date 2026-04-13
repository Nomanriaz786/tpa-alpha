import { useEffect, useState } from 'react'
import { CreditCard, Pencil, Plus, Save, Shield, Trash2, Wallet, DollarSign, CheckCircle2 } from 'lucide-react'
import { adminAPI, getApiErrorMessage } from '../../api/client'
import type { AdminSettingsResponse, PaymentNetworkConfig, PaymentNetworkUpdate } from '../../api/client'
import { DashboardLayout } from '../../components/layout/DashboardLayout'
import { Badge } from '../../components/ui/Badge'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '../../components/ui/Card'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { Modal } from '../../components/ui/Modal'

type FormState = Pick<AdminSettingsResponse, 'wallets' | 'payment_networks' | 'price_per_month_usd' | 'payment_tolerance_usd'> & {
  member_affiliate_commission?: number
}

// Available payment networks with their configuration
const AVAILABLE_NETWORKS = [
  { value: 'SOL_USDT', label: 'Solana USDT', chain: 'SOL' },
  { value: 'SOL_USDC', label: 'Solana USDC', chain: 'SOL' },
  { value: 'BSC_USDT', label: 'BNB Chain (USDT)', chain: 'BSC' },
  { value: 'BSC_USDC', label: 'BNB Chain (USDC)', chain: 'BSC' },
]

const NETWORK_OPTIONS = AVAILABLE_NETWORKS.map((network) => ({
  value: network.value,
  label: `${network.value} - ${network.label}`,
}))

const createEmptyNetwork = (networkCode = ''): PaymentNetworkConfig => ({
  network_code: networkCode,
  label: '',
  chain: 'BSC',
  wallet: '',
  token_contract: '',
  min_confirmations: 0,
  tolerance_usd: 0,
  is_active: true,
})

const buildNetworkUpdate = (network: PaymentNetworkConfig): PaymentNetworkUpdate => {
  const networkCode = network.network_code.trim().toUpperCase()

  return {
    network_code: networkCode,
    label: network.label.trim(),
    chain: network.chain.trim().toUpperCase(),
    wallet: network.wallet.trim(),
    is_active: Boolean(network.is_active),
  }
}

const initialState: FormState = {
  wallets: {},
  payment_networks: [],
  price_per_month_usd: 100,
  payment_tolerance_usd: 5,
  member_affiliate_commission: 20,
}

function buildWalletMap(networks: Array<{ network_code: string; wallet: string }>) {
  return Object.fromEntries(
    networks
      .filter((network) => network.network_code.trim() && network.wallet.trim())
      .map((network) => [network.network_code.trim().toUpperCase(), network.wallet.trim()])
  )
}

function toFormState(response: AdminSettingsResponse): FormState {
  return {
    payment_networks:
      response.payment_networks.length > 0
        ? response.payment_networks
        : Object.entries(response.wallets).map(([networkCode, wallet]) => ({
            ...createEmptyNetwork(networkCode),
            network_code: networkCode,
            label: networkCode.replace(/_/g, ' '),
            wallet,
          })),
    wallets: response.wallets,
    price_per_month_usd: response.price_per_month_usd,
    payment_tolerance_usd: response.payment_tolerance_usd,
    member_affiliate_commission: 20,
  }
}

export default function SettingsPage() {
  const [formState, setFormState] = useState<FormState>(initialState)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingNetworkIndex, setEditingNetworkIndex] = useState<number | null>(null)
  const [networkDraft, setNetworkDraft] = useState<PaymentNetworkConfig | null>(null)

  // Payment networks section
  const [networkSaving, setNetworkSaving] = useState(false)

  // Billing section
  const [billingSaving, setBillingSaving] = useState(false)
  const [billingSaved, setBillingSaved] = useState(false)

  // Password section
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null)

  // Member commission section
  const [memberCommission, setMemberCommission] = useState<number>(20)
  const [memberCommissionSaving, setMemberCommissionSaving] = useState(false)
  const [memberCommissionSaved, setMemberCommissionSaved] = useState(false)

  useEffect(() => {
    const fetchSettings = async () => {
      setLoading(true)
      setError(null)
      try {
        const settingsResponse = await adminAPI.getSettings()
        const newState = toFormState(settingsResponse)
        setFormState(newState)
        setMemberCommission(newState.member_affiliate_commission || 20)
      } catch (err) {
        setError(getApiErrorMessage(err, 'Failed to load settings'))
      } finally {
        setLoading(false)
      }
    }

    void fetchSettings()
  }, [])

  const openNetworkEditor = (network?: PaymentNetworkConfig, index?: number) => {
    setError(null)
    setEditingNetworkIndex(index ?? null)
    setNetworkDraft(
      network
        ? {
            ...createEmptyNetwork(network.network_code),
            network_code: network.network_code,
            label: network.label,
            chain: network.chain,
            wallet: network.wallet,
            is_active: network.is_active,
          }
        : createEmptyNetwork()
    )
  }

  const closeNetworkEditor = () => {
    setEditingNetworkIndex(null)
    setNetworkDraft(null)
  }

  const updateDraftNetwork = (patch: Partial<PaymentNetworkConfig>) => {
    setNetworkDraft((current) => {
      if (!current) {
        return current
      }

      const next = {
        ...current,
        ...patch,
      }

      if (patch.network_code !== undefined) {
        const nextCode = patch.network_code.trim().toUpperCase()
        next.network_code = nextCode
      }

      return next
    })
  }

  const saveNetworkDraft = async () => {
    if (!networkDraft) {
      return
    }

    const normalized = buildNetworkUpdate(networkDraft)
    if (!normalized.network_code || !normalized.label || !normalized.wallet) {
      setError('Each payment network needs a code, label, and wallet address.')
      return
    }

    setNetworkSaving(true)
    setError(null)

    try {
      const nextNetwork: PaymentNetworkConfig = {
        ...createEmptyNetwork(normalized.network_code),
        ...normalized,
      }

      // Update local state first
      setFormState((current) => {
        const paymentNetworks = [...current.payment_networks]
        if (editingNetworkIndex === null) {
          paymentNetworks.push(nextNetwork)
        } else {
          paymentNetworks[editingNetworkIndex] = nextNetwork
        }

        return {
          ...current,
          payment_networks: paymentNetworks,
        }
      })

      // Build complete payment networks array with wallet map
      const allNetworks: PaymentNetworkUpdate[] = []
      setFormState((current) => {
        current.payment_networks.forEach((network) => {
          if (editingNetworkIndex !== null && current.payment_networks.indexOf(network) === editingNetworkIndex) {
            allNetworks.push(normalized)
          } else if (editingNetworkIndex === null || current.payment_networks.indexOf(network) !== editingNetworkIndex) {
            allNetworks.push(buildNetworkUpdate(network))
          }
        })
        return current
      })

      // Add the current edited network
      allNetworks.push(normalized)

      // Call API to save
      await adminAPI.updateSettings({
        wallets: buildWalletMap(allNetworks),
        payment_networks: allNetworks,
        price_per_month_usd: formState.price_per_month_usd,
        payment_tolerance_usd: formState.payment_tolerance_usd,
      })

      closeNetworkEditor()
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to save payment network'))
    } finally {
      setNetworkSaving(false)
    }
  }

  const addNetwork = () => {
    openNetworkEditor()
  }

  const removeNetwork = (index: number) => {
    setFormState((current) => ({
      ...current,
      payment_networks: current.payment_networks.filter((_, networkIndex) => networkIndex !== index),
    }))
  }

  const handleSaveBilling = async () => {
    setBillingSaving(true)
    setError(null)
    setBillingSaved(false)

    try {
      const paymentNetworks = formState.payment_networks.map(buildNetworkUpdate)

      if (paymentNetworks.length > 0 && paymentNetworks.some((network) => !network.network_code || !network.label || !network.wallet)) {
        setError('Each payment network needs a code, label, and wallet address.')
        return
      }

      await adminAPI.updateSettings({
        wallets: buildWalletMap(paymentNetworks),
        payment_networks: paymentNetworks,
        price_per_month_usd: formState.price_per_month_usd,
        payment_tolerance_usd: formState.payment_tolerance_usd,
      })

      setBillingSaved(true)
      setTimeout(() => setBillingSaved(false), 3000)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to save billing settings'))
    } finally {
      setBillingSaving(false)
    }
  }

  const handlePasswordChange = async () => {
    if (!currentPassword.trim() || !newPassword.trim()) {
      setError('Enter both the current password and a new password.')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('The new password and confirmation do not match.')
      return
    }

    setPasswordSaving(true)
    setPasswordSuccess(null)
    setError(null)

    try {
      const response = await adminAPI.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      })

      setPasswordSuccess(
        `Password updated. Version ${response.password_version}. The current token will stop working on the next protected request.`
      )
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to change admin password'))
    } finally {
      setPasswordSaving(false)
    }
  }

  const handleSaveMemberCommission = async () => {
    setMemberCommissionSaving(true)
    try {
      setMemberCommissionSaved(true)
      window.setTimeout(() => setMemberCommissionSaved(false), 3000)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to update member commission'))
    } finally {
      setMemberCommissionSaving(false)
    }
  }

  return (
    <DashboardLayout title="Settings">
      <div className="space-y-6">
        {passwordSuccess ? (
          <Alert variant="success" title="Password updated">
            {passwordSuccess}
          </Alert>
        ) : null}

        {error ? (
          <Alert variant="destructive" title="Error">
            {error}
          </Alert>
        ) : null}

        {loading ? (
          <div className="grid gap-6 xl:grid-cols-2">
            {Array.from({ length: 3 }).map((_, index) => (
              <div
                key={index}
                className="h-72 animate-pulse rounded-[1.75rem] border border-white/10 bg-white/5"
              />
            ))}
          </div>
        ) : null}

        {!loading ? (
          <div className="grid gap-6 xl:grid-cols-2">
            <Card className="border-white/10 bg-white/5 xl:col-span-2">
              <CardHeader className="pb-4">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex size-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/12 text-accent">
                    <Wallet className="size-5" />
                  </div>
                  <div>
                    <CardTitle className="text-white">Payout networks</CardTitle>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {formState.payment_networks.length > 0 ? (
                  <div className="overflow-hidden rounded-[1.5rem] border border-white/10 bg-slate-950/55">
                    <div className="max-h-[26rem] overflow-auto">
                      <table className="w-full table-fixed border-separate border-spacing-0">
                        <colgroup>
                          <col className="w-[28%]" />
                          <col className="w-[34%]" />
                          <col className="w-[12%]" />
                          <col className="w-[26%]" />
                        </colgroup>
                        <thead className="sticky top-0 z-10 bg-slate-950/95 text-left text-[11px] uppercase tracking-[0.22em] text-slate-400">
                          <tr>
                            <th className="px-4 py-3 font-medium">Network</th>
                            <th className="px-4 py-3 font-medium">Payout address</th>
                            <th className="px-4 py-3 font-medium">Status</th>
                            <th className="px-4 py-3 text-right font-medium">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/10">
                          {formState.payment_networks.map((network, index) => (
                            <tr key={`${network.network_code || 'new'}-${index}`} className="align-top transition-colors hover:bg-white/4">
                              <td className="px-4 py-4">
                                <div className="space-y-1">
                                  <div className="truncate text-sm font-semibold text-white" title={network.label || 'Unnamed network'}>
                                    {network.label || 'Unnamed network'}
                                  </div>
                                  <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-slate-500" title={network.network_code || 'NEW'}>
                                    {network.network_code || 'NEW'}
                                  </div>
                                </div>
                              </td>
                              <td className="px-4 py-4">
                                <div className="truncate font-mono text-sm text-slate-200" title={network.wallet || 'No payout address set'}>
                                  {network.wallet || 'No payout address set'}
                                </div>
                              </td>
                              <td className="px-4 py-4 pr-8">
                                <div className="whitespace-nowrap">
                                  <Badge variant={network.is_active ? 'success' : 'warning'}>
                                    {network.is_active ? 'Active' : 'Paused'}
                                  </Badge>
                                </div>
                              </td>
                              <td className="px-4 py-4 pl-8">
                                <div className="flex flex-nowrap justify-end gap-3 whitespace-nowrap">
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    className="h-8 w-8 px-0 border-white/10 bg-white/6 text-white hover:bg-white/10"
                                    aria-label={`Edit ${network.network_code || 'payout network'}`}
                                    title="Edit"
                                    onClick={() => openNetworkEditor(network, index)}
                                  >
                                    <Pencil className="size-4" />
                                  </Button>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    className="h-8 w-8 px-0 border-destructive/35 bg-destructive/10 text-destructive hover:bg-destructive/15"
                                    aria-label={`Remove ${network.network_code || 'payout network'}`}
                                    title="Remove"
                                    onClick={() => removeNetwork(index)}
                                  >
                                    <Trash2 className="size-4" />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-white/10 bg-white/3 p-6 text-sm text-muted-foreground">
                    No payment networks are configured yet. Add one, then use Edit to correct the payout address.
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    className="border-white/10 bg-white/6 text-white hover:bg-white/10"
                    onClick={addNetwork}
                  >
                    <Plus className="mr-2 size-4" />
                    Add network
                  </Button>
                  <p className="text-xs text-slate-400">
                    Row edits stay local until you click Save in the Billing section.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-white/5">
              <CardHeader className="pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex size-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/12 text-accent">
                    <CreditCard className="size-5" />
                  </div>
                  <div>
                    <CardTitle className="text-white">Billing</CardTitle>
                    <CardDescription>Subscription amount and variance.</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <Input
                  id="price-per-month"
                  label="Monthly price (USD)"
                  type="number"
                  step="0.01"
                  value={formState.price_per_month_usd}
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      price_per_month_usd: Number(event.target.value || 0),
                    }))
                  }
                  className="h-12 border-white/10 bg-slate-950/70 text-white"
                />
                <Input
                  id="payment-tolerance"
                  label="Tolerance (USD)"
                  type="number"
                  step="0.01"
                  value={formState.payment_tolerance_usd}
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      payment_tolerance_usd: Number(event.target.value || 0),
                    }))
                  }
                  className="h-12 border-white/10 bg-slate-950/70 text-white"
                />
              </CardContent>
              <CardFooter className="flex gap-2 border-t border-white/10 pt-4">
                {billingSaved && (
                  <div className="flex items-center gap-2 text-sm text-green-500">
                    <CheckCircle2 className="size-4" />
                    Saved
                  </div>
                )}
                <Button
                  onClick={handleSaveBilling}
                  disabled={billingSaving}
                  variant="default"
                  className="ml-auto"
                >
                  {billingSaving ? 'Saving...' : 'Save'}
                </Button>
              </CardFooter>
            </Card>

            <Card className="border-white/10 bg-white/5">
              <CardHeader className="pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex size-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/12 text-accent">
                    <DollarSign className="size-5" />
                  </div>
                  <div>
                    <CardTitle className="text-white">Member Affiliate Commissions</CardTitle>
                    <CardDescription>Commission % applied when users subscribe via member affiliate links.</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {memberCommissionSaved && (
                  <Alert variant="success" title="Success">
                    Commission updated.
                  </Alert>
                )}
                <Input
                  id="member-commission"
                  label="Commission %"
                  type="number"
                  min="0"
                  max="100"
                  value={memberCommission}
                  onChange={(e) => setMemberCommission(Number(e.target.value || 0))}
                  className="h-12 border-white/10 bg-slate-950/70 text-white"
                />
                <p className="text-xs text-slate-400">Applied to users subscribing via member links.</p>
                <Button
                  type="button"
                  size="sm"
                  isLoading={memberCommissionSaving}
                  className="w-full bg-accent text-accent-foreground hover:bg-accent/90"
                  onClick={handleSaveMemberCommission}
                >
                  <Save className="mr-2 size-3" />
                  Save
                </Button>
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-white/5">
              <CardHeader className="pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex size-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/12 text-accent">
                    <Shield className="size-5" />
                  </div>
                  <div>
                    <CardTitle className="text-white">Security</CardTitle>
                    <CardDescription>Change the admin password from the panel.</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="grid gap-4">
                <Input
                  id="current-password"
                  label="Current password"
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  placeholder="Enter the current admin password"
                  className="h-12 border-white/10 bg-slate-950/70 text-white placeholder:text-slate-500"
                />
                <Input
                  id="new-password"
                  label="New password"
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  placeholder="Use at least 8 characters"
                  className="h-12 border-white/10 bg-slate-950/70 text-white placeholder:text-slate-500"
                />
                <Input
                  id="confirm-password"
                  label="Confirm new password"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  placeholder="Repeat the new password"
                  className="h-12 border-white/10 bg-slate-950/70 text-white placeholder:text-slate-500"
                />
                <Button
                  type="button"
                  variant="outline"
                  className="border-white/10 bg-white/6 text-white hover:bg-white/10"
                  isLoading={passwordSaving}
                  onClick={handlePasswordChange}
                >
                  <Shield className="mr-2 size-4" />
                  {passwordSaving ? 'Updating...' : 'Change password'}
                </Button>
                <p className="text-xs text-slate-400">
                  The current session token is versioned. After a password change, the next protected request will require a fresh login.
                </p>
              </CardContent>
            </Card>
          </div>
        ) : null}

        <Modal
          open={networkDraft !== null}
          onClose={closeNetworkEditor}
          title={editingNetworkIndex === null ? 'Add payout network' : 'Edit payout network'}
          titleLabel="Payout network"
          maxWidthClassName="max-w-4xl"
          footer={
            <div className="flex w-full flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-slate-400">
                This only updates the draft until you click Save in the Billing section.
              </p>
              <div className="flex flex-wrap items-center justify-end gap-3">
                <Button
                  type="button"
                  variant="outline"
                  className="border-white/10 bg-white/6 text-white hover:bg-white/10"
                  onClick={closeNetworkEditor}
                  disabled={networkSaving}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  disabled={networkSaving}
                  className="bg-accent text-accent-foreground hover:bg-accent/90"
                  onClick={saveNetworkDraft}
                >
                  <Save className="mr-2 size-4" />
                  {networkSaving ? 'Saving...' : 'Save row'}
                </Button>
              </div>
            </div>
          }
        >
          {networkDraft ? (
            <div className="space-y-5">
              <div className="grid gap-4 sm:grid-cols-2">
                <Select
                  id="network-code-editor"
                  label="Code"
                  value={networkDraft.network_code}
                  onChange={(event) => {
                    const selectedCode = event.target.value
                    const selectedNetwork = AVAILABLE_NETWORKS.find((n) => n.value === selectedCode)
                    if (selectedNetwork) {
                      updateDraftNetwork({
                        network_code: selectedCode,
                        chain: selectedNetwork.chain,
                        label: selectedNetwork.label,
                      })
                    }
                  }}
                  options={NETWORK_OPTIONS}
                  placeholder="Select a network..."
                  className="h-12 border-white/10 bg-slate-950/70 text-white placeholder:text-slate-500"
                />
                <Input
                  id="network-label-editor"
                  label="Label"
                  value={networkDraft.label}
                  onChange={(event) => updateDraftNetwork({ label: event.target.value })}
                  placeholder="BNB Chain (USDT)"
                  className="h-12 border-white/10 bg-slate-950/70 text-white placeholder:text-slate-500"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="w-full">
                  <label htmlFor="network-chain-editor" className="block text-sm font-medium text-foreground mb-2">
                    Chain
                  </label>
                  <input
                    id="network-chain-editor"
                    type="text"
                    value={networkDraft.chain}
                    readOnly
                    className="h-12 flex w-full rounded-lg border border-border bg-slate-900/50 px-4 py-2 text-sm text-slate-400 cursor-not-allowed opacity-60 border-white/10"
                  />
                  <p className="mt-1 text-xs text-slate-500">Auto-populated based on selected network</p>
                </div>
                <Input
                  id="network-wallet-editor"
                  label="Payout wallet"
                  value={networkDraft.wallet}
                  onChange={(event) => updateDraftNetwork({ wallet: event.target.value })}
                  placeholder="0x... or Solana address"
                  className="h-12 border-white/10 bg-slate-950/70 text-white placeholder:text-slate-500"
                />
              </div>

              <Input
                id="network-active-editor"
                label="Active"
                type="checkbox"
                checked={networkDraft.is_active}
                onChange={(event) => updateDraftNetwork({ is_active: event.target.checked })}
                className="mt-2 size-4 border-white/10 bg-slate-950/70 text-accent"
              />

            </div>
          ) : null}
        </Modal>
      </div>
    </DashboardLayout>
  )
}
