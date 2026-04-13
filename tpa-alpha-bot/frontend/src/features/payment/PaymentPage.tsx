import { useEffect, useState } from 'react'
import { AxiosError } from 'axios'
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Copy,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react'
import { getApiErrorMessage, paymentAPI } from '../../api/client'
import type { NetworkInfo, PaymentInitiateResponse, PaymentStatusResponse } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { Card, CardContent } from '../../components/ui/Card'
import { Input } from '../../components/ui/Input'

type PaymentStep = 'form' | 'payment' | 'confirm'

const initialFormData = {
  discord_id: '',
  discord_username: '',
  tradingview_username: '',
  email: '',
  affiliate_code: '',
  network: '',
  sender_wallet: '',
}

function StepPill({
  index,
  title,
  isActive,
  isComplete,
}: {
  index: number
  title: string
  isActive: boolean
  isComplete: boolean
}) {
  return (
    <div
      className={[
        'rounded-2xl border px-4 py-3 transition-all',
        isActive
          ? 'border-accent/50 bg-accent/12 shadow-lg shadow-accent/10'
          : 'border-border/70 bg-card/55',
      ].join(' ')}
    >
      <div className="flex items-center gap-3">
        <div
          className={[
            'flex size-9 items-center justify-center rounded-full border text-sm font-semibold',
            isComplete
              ? 'border-success/40 bg-success/20 text-success'
              : isActive
                ? 'border-accent/40 bg-accent text-accent-foreground'
                : 'border-border bg-background/70 text-muted-foreground',
          ].join(' ')}
        >
          {isComplete ? <CheckCircle2 className="size-4" /> : index}
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground">{title}</p>
        </div>
      </div>
    </div>
  )
}

export default function PaymentPage() {
  const [step, setStep] = useState<PaymentStep>('form')
  const [networks, setNetworks] = useState<NetworkInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [networksLoading, setNetworksLoading] = useState(false)
  const [copiedWallet, setCopiedWallet] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [paymentData, setPaymentData] = useState<PaymentInitiateResponse | null>(null)
  const [statusData, setStatusData] = useState<PaymentStatusResponse | null>(null)
  const [pendingId, setPendingId] = useState('')
  const [proofInput, setProofInput] = useState('')
  const [proofAccepted, setProofAccepted] = useState(false)
  const [queryLocked, setQueryLocked] = useState({
    discord_id: false,
    discord_username: false,
    affiliate_code: false,
  })

  const [formData, setFormData] = useState(initialFormData)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const discordId = params.get('discord_id') ?? ''
    const discordUsername = params.get('discord_username') ?? ''
    const affiliateCode = (params.get('affiliate_code') ?? '').trim().toUpperCase()

    if (discordId || discordUsername || affiliateCode) {
      setFormData((prev) => ({
        ...prev,
        discord_id: discordId || prev.discord_id,
        discord_username: discordUsername || prev.discord_username,
        affiliate_code: affiliateCode || prev.affiliate_code,
      }))
      setQueryLocked({
        discord_id: Boolean(discordId),
        discord_username: Boolean(discordUsername),
        affiliate_code: Boolean(affiliateCode),
      })
    }

    void loadNetworks()
  }, [])

  const currentNetwork = networks.find((network) => network.id === formData.network)

  const loadNetworks = async () => {
    setNetworksLoading(true)
    setError(null)
    try {
      const nets = await paymentAPI.getNetworks()
      setNetworks(nets)
      if (nets.length > 0) {
        setFormData((prev) => ({
          ...prev,
          network: prev.network || nets[0].id,
        }))
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to load networks'))
    } finally {
      setNetworksLoading(false)
    }
  }

  const handleInitiatePayment = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const response = await paymentAPI.initiate({
        ...formData,
        tradingview_username: formData.tradingview_username.trim(),
        email: formData.email.trim() || undefined,
        affiliate_code: formData.affiliate_code.trim() || undefined,
        sender_wallet: formData.sender_wallet.trim(),
      })
      setPaymentData(response)
      setPendingId(response.pending_id)
      setProofInput('')
      setProofAccepted(false)
      setStatusData(null)
      setCopiedWallet(false)
      setStep('payment')
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to initiate payment'))
    } finally {
      setLoading(false)
    }
  }

  const handleCheckStatus = async () => {
    if (!pendingId) return

    setLoading(true)
    setError(null)

    try {
      const response = await paymentAPI.checkStatus(pendingId)
      setStatusData(response)
      setStep('confirm')
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to check payment status'))
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitProof = async () => {
    if (!pendingId || !proofInput.trim()) {
      setError('Please paste your transaction hash or explorer URL first.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      await paymentAPI.submitProof(pendingId, proofInput.trim())
      setProofAccepted(true)
    } catch (err) {
      const axiosError = err as AxiosError
      if (axiosError.response?.status === 422) {
        setError('Invalid transaction hash or URL.')
      } else {
        setError(getApiErrorMessage(err, 'Failed to submit payment proof'))
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCopyWallet = async () => {
    if (!paymentData?.wallet_to_pay) return

    try {
      await navigator.clipboard.writeText(paymentData.wallet_to_pay)
      setCopiedWallet(true)
      window.setTimeout(() => setCopiedWallet(false), 2000)
    } catch {
      setError('Unable to copy wallet address. Please copy it manually.')
    }
  }

  const handleStartOver = () => {
    setStep('form')
    setPaymentData(null)
    setStatusData(null)
    setPendingId('')
    setProofInput('')
    setProofAccepted(false)
    setCopiedWallet(false)
    setError(null)
    setFormData((prev) => ({
      ...initialFormData,
      discord_id: queryLocked.discord_id ? prev.discord_id : '',
      discord_username: queryLocked.discord_username ? prev.discord_username : '',
      affiliate_code: queryLocked.affiliate_code ? prev.affiliate_code : '',
      network: networks[0]?.id ?? '',
    }))
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <div className="absolute inset-0 bg-[linear-gradient(180deg,#05070b_0%,#070a0f_55%,#05070b_100%)]" />
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.012)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.012)_1px,transparent_1px)] bg-[size:72px_72px] opacity-10" />

      <div className="relative mx-auto min-h-screen w-full max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/10 px-4 py-2 text-sm font-medium text-accent">
            <ShieldCheck className="size-4" />
            Member checkout
          </div>
          <p className="mt-6 font-semibold uppercase tracking-[0.28em] text-accent/80">
            TPA Alpha
          </p>
          <h1 className="mx-auto mt-4 max-w-4xl text-4xl font-semibold leading-[0.98] tracking-[-0.045em] text-white sm:text-5xl md:text-6xl">
            Activate your subscription.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">
            Add your details, send payment, and check status here.
          </p>
        </div>

        <div className="mb-8 rounded-[1.75rem] border border-white/10 bg-black/20 p-5 backdrop-blur-xl">
          <div className="grid gap-4 sm:grid-cols-3">
            <StepPill index={1} title="Details" isActive={step === 'form'} isComplete={step !== 'form'} />
            <StepPill index={2} title="Payment" isActive={step === 'payment'} isComplete={step === 'confirm'} />
            <StepPill index={3} title="Done" isActive={step === 'confirm'} isComplete={false} />
          </div>
        </div>

        <Card className="overflow-hidden rounded-[2rem] border-white/10 bg-slate-950/78 shadow-2xl shadow-black/40 backdrop-blur-xl">
              <CardContent className="p-0">
                {error ? (
                  <div className="border-b border-destructive/20 bg-destructive/10 px-6 py-4 text-sm text-destructive sm:px-8">
                    {error}
                  </div>
                ) : null}

                {step === 'form' ? (
                  <form onSubmit={handleInitiatePayment} className="space-y-8 p-6 sm:p-8">
                    <div className="flex flex-col gap-4 border-b border-border/70 pb-6 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-accent/80">Member details</p>
                        <h2 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-white">Complete the form</h2>
                        <p className="mt-3 max-w-lg text-sm leading-7 text-muted-foreground">Enter the details needed to start checkout.</p>
                      </div>
                      <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300">
                        {networksLoading ? (
                          <span className="inline-flex items-center gap-2">
                            <RefreshCw className="size-4 animate-spin" />
                            Loading
                          </span>
                        ) : (
                          <span>{networks.length} network{networks.length === 1 ? '' : 's'}</span>
                        )}
                      </div>
                    </div>

                    <div className="grid gap-5 md:grid-cols-2">
                      <Input
                        id="discord_id"
                        label="Discord ID"
                        value={formData.discord_id}
                        onChange={(e) => setFormData({ ...formData, discord_id: e.target.value })}
                        placeholder="Discord member ID"
                        readOnly={queryLocked.discord_id}
                        required
                        className="h-12 border-white/10 bg-white/5 text-white placeholder:text-slate-500"
                      />

                      <Input
                        id="discord_username"
                        label="Discord Username"
                        value={formData.discord_username}
                        onChange={(e) => setFormData({ ...formData, discord_username: e.target.value })}
                        placeholder="username"
                        readOnly={queryLocked.discord_username}
                        required
                        className="h-12 border-white/10 bg-white/5 text-white placeholder:text-slate-500"
                      />

                      <Input
                        id="tradingview_username"
                        label="TradingView Username"
                        value={formData.tradingview_username}
                        onChange={(e) => setFormData({ ...formData, tradingview_username: e.target.value })}
                        placeholder="Your TradingView handle"
                        required
                        className="h-12 border-white/10 bg-white/5 text-white placeholder:text-slate-500"
                      />

                      <Input
                        id="email"
                        label="Email"
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        placeholder="Optional receipt email"
                        className="h-12 border-white/10 bg-white/5 text-white placeholder:text-slate-500"
                      />

                      <div>
                        <Input
                          id="affiliate_code"
                          label="Referral Code"
                          value={formData.affiliate_code}
                          onChange={(e) =>
                            setFormData({ ...formData, affiliate_code: e.target.value.toUpperCase() })
                          }
                          placeholder="Optional referral code"
                          readOnly={queryLocked.affiliate_code}
                          className="h-12 border-white/10 bg-white/5 text-white placeholder:text-slate-500"
                        />
                        <p className="mt-2 text-xs text-muted-foreground">
                          {queryLocked.affiliate_code
                            ? 'Applied from your referral link.'
                            : 'Leave blank unless you have a code.'}
                        </p>
                      </div>

                      <div className="w-full">
                        <label htmlFor="network" className="mb-2 block text-sm font-medium text-foreground">
                          Payment Network
                        </label>
                        <div className="relative">
                          <select
                            id="network"
                            value={formData.network}
                            onChange={(e) => setFormData({ ...formData, network: e.target.value })}
                            required
                            className="h-12 w-full appearance-none rounded-lg border border-white/10 bg-white/5 px-4 pr-10 text-sm text-white outline-none transition focus:ring-2 focus:ring-ring"
                          >
                            <option value="" disabled className="text-slate-950">
                              Select a network
                            </option>
                            {networks.map((network) => (
                              <option key={network.id} value={network.id} className="text-slate-950">
                                {network.label}
                              </option>
                            ))}
                          </select>
                          <div className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-slate-400">
                            <ArrowRight className="size-4 rotate-90" />
                          </div>
                        </div>
                        {currentNetwork ? (
                          <p className="mt-2 text-xs leading-6 text-muted-foreground">
                            Chain: <span className="font-medium text-slate-200">{currentNetwork.chain}</span>
                          </p>
                        ) : null}
                      </div>
                    </div>

                    <Input
                      id="sender_wallet"
                      label="Your Wallet Address"
                      value={formData.sender_wallet}
                      onChange={(e) => setFormData({ ...formData, sender_wallet: e.target.value })}
                      placeholder="Paste the wallet address you will send from"
                      required
                      className="h-12 border-white/10 bg-white/5 text-white placeholder:text-slate-500"
                    />

                    <div className="rounded-2xl border border-accent/15 bg-accent/10 p-4">
                      <div className="flex items-start gap-3">
                        <ShieldCheck className="mt-0.5 size-5 text-accent" />
                        <div>
                          <p className="font-semibold text-white">Check your usernames before continuing.</p>
                        </div>
                      </div>
                    </div>

                    <Button
                      type="submit"
                      size="lg"
                      isLoading={loading}
                      className="h-14 w-full bg-accent text-accent-foreground shadow-xl shadow-accent/20 hover:bg-accent/90"
                    >
                      {loading ? 'Preparing checkout...' : 'Continue to Payment'}
                    </Button>
                  </form>
                ) : null}

                {step === 'payment' && paymentData ? (
                  <div className="space-y-8 p-6 sm:p-8">
                    <div className="border-b border-border/70 pb-6">
                      <p className="text-sm font-semibold uppercase tracking-[0.22em] text-accent/80">Payment</p>
                      <h2 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-white">Send the exact amount</h2>
                      <p className="mt-3 text-sm leading-7 text-muted-foreground">Paste proof after you send payment.</p>
                    </div>

                    <div className="grid gap-4 md:grid-cols-3">
                      <div className="rounded-2xl border border-white/10 bg-white/5 p-5 md:col-span-2">
                        <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Amount due</p>
                        <div className="mt-4 flex flex-wrap items-end gap-3">
                          <span className="text-4xl font-bold tracking-[-0.035em] text-white">
                            ${paymentData.amount_usd.toFixed(2)}
                          </span>
                          <span className="pb-1 text-base font-semibold text-accent">
                            {paymentData.network}
                          </span>
                        </div>
                        {paymentData.discount_applied > 0 ? (
                          <p className="mt-3 text-sm text-success">
                            Discount applied: ${paymentData.discount_applied.toFixed(2)}
                          </p>
                        ) : null}
                      </div>

                      <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                        <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Pending ID</p>
                        <p className="mt-4 break-all text-sm font-medium text-slate-200">{pendingId}</p>
                      </div>
                    </div>

                    <div className="space-y-5">
                      <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5">
                        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <p className="text-sm uppercase tracking-[0.18em] text-muted-foreground">Wallet</p>
                            <p className="mt-3 break-all font-mono text-sm leading-7 text-slate-100">
                              {paymentData.wallet_to_pay}
                            </p>
                          </div>
                          <Button
                            type="button"
                            variant="outline"
                            className="border-white/10 bg-white/5 text-white hover:bg-white/10"
                            onClick={handleCopyWallet}
                          >
                            <Copy className="mr-2 size-4" />
                            {copiedWallet ? 'Copied' : 'Copy'}
                          </Button>
                        </div>
                      </div>

                      <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5">
                        <p className="font-semibold text-white">Checklist</p>
                        <div className="mt-4 grid gap-3 text-sm leading-7 text-slate-300 md:grid-cols-3">
                          <div className="flex items-start gap-3 rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                            <CheckCircle2 className="mt-1 size-4 text-accent" />
                            <span>Use the wallet shown above.</span>
                          </div>
                          <div className="flex items-start gap-3 rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                            <CheckCircle2 className="mt-1 size-4 text-accent" />
                            <span>Send the exact amount.</span>
                          </div>
                          <div className="flex items-start gap-3 rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                            <Clock3 className="mt-1 size-4 text-accent" />
                            <span>Return here to check status.</span>
                          </div>
                        </div>
                      </div>

                      <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5">
                        <label className="mb-2 block text-sm font-medium text-white">
                          Transaction hash or explorer URL
                        </label>
                        <input
                          type="text"
                          value={proofInput}
                          onChange={(e) => setProofInput(e.target.value)}
                          placeholder="0x... or https://bscscan.com/tx/..."
                          className="h-12 w-full rounded-lg border border-white/10 bg-slate-950/70 px-4 text-sm text-white outline-none transition placeholder:text-slate-500 focus:ring-2 focus:ring-ring"
                        />
                        <div className="mt-4 grid gap-3 sm:grid-cols-2">
                          <Button
                            type="button"
                            isLoading={loading}
                            disabled={!proofInput.trim()}
                            className="h-12 w-full bg-success text-success-foreground hover:bg-success/90"
                            onClick={handleSubmitProof}
                          >
                            Submit Proof
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            isLoading={loading}
                            disabled={!proofAccepted}
                            className="h-12 w-full border-white/10 bg-white/5 text-white hover:bg-white/10"
                            onClick={handleCheckStatus}
                          >
                            Check Status
                          </Button>
                        </div>

                        <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm">
                          {proofAccepted ? (
                            <div className="flex items-start gap-3 text-success">
                              <CheckCircle2 className="mt-0.5 size-4" />
                              <span>
                                Proof received. Check back for status.
                              </span>
                            </div>
                          ) : (
                            <div className="flex items-start gap-3 text-slate-300">
                              <AlertTriangle className="mt-0.5 size-4 text-accent" />
                              <span>
                                Submit proof first, then check status.
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    <Button
                      type="button"
                      variant="ghost"
                      className="w-full text-slate-300 hover:bg-white/5 hover:text-white"
                      onClick={() => setStep('form')}
                    >
                      Back to profile
                    </Button>
                  </div>
                ) : null}

                {step === 'confirm' && statusData ? (
                  <div className="space-y-8 p-6 sm:p-8">
                    <div className="border-b border-border/70 pb-6">
                      <p className="text-sm font-semibold uppercase tracking-[0.22em] text-accent/80">Status</p>
                      <h2 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-white">Payment update</h2>
                      <p className="mt-3 text-sm leading-7 text-muted-foreground">Latest chain status for this payment.</p>
                    </div>

                    <div
                      className={[
                        'rounded-[1.75rem] border p-6',
                        statusData.status === 'detected'
                          ? 'border-success/30 bg-success/10'
                          : statusData.status === 'expired'
                            ? 'border-destructive/30 bg-destructive/10'
                            : 'border-accent/30 bg-accent/10',
                      ].join(' ')}
                    >
                      <div className="flex items-start gap-4">
                        <div
                          className={[
                            'flex size-12 items-center justify-center rounded-2xl',
                            statusData.status === 'detected'
                              ? 'bg-success/20 text-success'
                              : statusData.status === 'expired'
                                ? 'bg-destructive/20 text-destructive'
                                : 'bg-accent/20 text-accent',
                          ].join(' ')}
                        >
                          {statusData.status === 'detected' ? (
                            <CheckCircle2 className="size-6" />
                          ) : statusData.status === 'expired' ? (
                            <AlertTriangle className="size-6" />
                          ) : (
                            <Clock3 className="size-6" />
                          )}
                        </div>
                        <div>
                          <p className="text-2xl font-bold tracking-[-0.03em] text-white">
                            {statusData.status === 'detected'
                              ? 'Payment confirmed'
                              : statusData.status === 'expired'
                                ? 'Payment window expired'
                                : 'Payment still pending'}
                          </p>
                          <p className="mt-2 text-sm leading-7 text-slate-200">
                            {statusData.status === 'detected'
                              ? 'Your payment has been confirmed and your access is being finalized.'
                              : statusData.status === 'expired'
                                ? 'This payment request expired before it could be completed. Start a new request to continue.'
                                : 'Your request is still being processed. Please wait a bit longer and check again.'}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                        <p className="text-sm uppercase tracking-[0.18em] text-muted-foreground">Status</p>
                        <p className="mt-3 text-lg font-semibold capitalize text-white">
                          {statusData.status}
                        </p>
                      </div>

                      {(statusData.tx_hash || statusData.tx_hash_proof) ? (
                        <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                          <p className="text-sm uppercase tracking-[0.18em] text-muted-foreground">Tx</p>
                          <p className="mt-3 break-all font-mono text-sm leading-7 text-slate-200">
                            {statusData.tx_hash || statusData.tx_hash_proof}
                          </p>
                        </div>
                      ) : null}
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <Button
                        type="button"
                        size="lg"
                        className="h-12 w-full bg-accent text-accent-foreground hover:bg-accent/90"
                        onClick={handleStartOver}
                      >
                        Start New Payment
                      </Button>

                      {statusData.status !== 'detected' ? (
                        <Button
                          type="button"
                          variant="outline"
                          isLoading={loading}
                          className="h-12 w-full border-white/10 bg-white/5 text-white hover:bg-white/10"
                          onClick={handleCheckStatus}
                        >
                          Refresh Status
                        </Button>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </CardContent>
        </Card>
      </div>
    </div>
  )
}
