import axios, { AxiosError, type AxiosInstance, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'

const API_BASE_URL = import.meta.env.MODE === 'development' ? 'http://localhost:8000/api' : '/api'

export interface APIResponse<T> {
  data: T
  status: number
}

export interface ErrorResponse {
  error: string
  detail?: string
  status_code: number
}

export function getApiErrorMessage(error: unknown, fallback: string) {
  const axiosError = error as AxiosError<{ detail?: string; error?: string; message?: string }>

  const normalizeDetail = (detail: unknown) => {
    if (typeof detail === 'string') {
      return detail
    }

    if (Array.isArray(detail)) {
      const parts = detail
        .map((entry) => {
          if (typeof entry === 'string') {
            return entry
          }

          if (entry && typeof entry === 'object') {
            const typedEntry = entry as { msg?: string; loc?: unknown }
            const message = typedEntry.msg
            const location = Array.isArray(typedEntry.loc) ? typedEntry.loc.join('.') : ''
            if (message) {
              return location ? `${location}: ${message}` : message
            }
          }

          return String(entry)
        })
        .filter(Boolean)

      return parts.length > 0 ? parts.join(', ') : undefined
    }

    if (detail && typeof detail === 'object') {
      try {
        return JSON.stringify(detail)
      } catch {
        return String(detail)
      }
    }

    return undefined
  }

  return (
    normalizeDetail(axiosError.response?.data?.detail) ||
    axiosError.response?.data?.error ||
    axiosError.response?.data?.message ||
    (error instanceof Error ? error.message : fallback)
  )
}

export interface PaymentInitiateRequest {
  discord_id: string
  discord_username: string
  tradingview_username: string
  email?: string
  affiliate_code?: string
  network: string
  sender_wallet: string
}

export interface PaymentInitiateResponse {
  pending_id: string
  wallet_to_pay: string
  amount_usd: number
  discount_applied: number
  network: string
  discount_percent?: number
}

interface RawPaymentInitiateResponse {
  pending_id: string
  wallet_to_pay: string
  amount_usd: number | string
  discount_applied: number | string
  network: string
  discount_percent?: number | string | null
}

export interface PaymentProofSubmitResponse {
  status: 'accepted'
  tx_hash: string
  message: string
}

export interface PaymentStatusResponse {
  status: 'pending' | 'detected' | 'expired'
  tx_hash_proof?: string
  tx_hash?: string
  months_granted?: number
  expires_at?: string
}

export interface NetworkInfo {
  id: string
  label: string
  chain: string
  wallet: string
  token_contract?: string | null
  min_confirmations?: number
  tolerance_usd?: number
  is_active?: boolean
}

export interface PaymentNetworkConfig {
  network_code: string
  label: string
  chain: string
  wallet: string
  token_contract: string
  min_confirmations: number
  tolerance_usd: number
  is_active: boolean
}

export interface PaymentNetworkUpdate {
  network_code: string
  label: string
  chain: string
  wallet: string
  token_contract?: string
  min_confirmations?: number
  tolerance_usd?: number
  is_active: boolean
}

export interface GuildSettingsConfig {
  guild_id: string
  vip_role_id?: string | null
  community_role_id?: string | null
  welcome_channel_id?: string | null
  setup_channel_id?: string | null
  admin_channel_id?: string | null
  payment_logs_channel_id?: string | null
  support_channel_id?: string | null
  is_active: boolean
  updated_at?: string | null
}

export interface GuildSettingsUpdate {
  guild_id: string
  vip_role_id?: string | null
  community_role_id?: string | null
  welcome_channel_id?: string | null
  setup_channel_id?: string | null
  admin_channel_id?: string | null
  payment_logs_channel_id?: string | null
  support_channel_id?: string | null
  is_active?: boolean | null
}

export interface AdminLoginResponse {
  token: string
  expires_at: string
}

export interface DashboardResponse {
  stats: {
    total_subscribers: number
    active_subscribers: number
    monthly_revenue_usd: number
    unpaid_commissions_usd: number
  }
  recent_subscribers: SubscriberResponse[]
}

export interface SubscriberResponse {
  id: string
  discord_id: string
  discord_username: string
  tradingview_username: string
  email?: string
  expires_at?: string
  is_active: boolean
  months_paid: number
  created_at: string
  commission_wallet?: string
  network?: string
  owned_referral_code?: string
  owned_referral_link?: string
}

export interface SubscribersResponse {
  items: SubscriberResponse[]
  total: number
  page: number
  per_page: number
}

export interface AffiliateResponse {
  id: string
  code: string
  discord_id?: string | null
  name?: string | null
  type: string
  discount_percent: number
  commission_percent: number
  payout_wallet?: string | null
  usage_limit?: number | null
  is_active: boolean
  created_at: string
  affiliate_link?: string | null
}

export interface AffiliatesResponse {
  items: AffiliateResponse[]
  total: number
  page: number
  per_page: number
}

export interface AffiliateDetailResponse extends AffiliateResponse {
  active_members: number
  usage_count: number
  total_commissions_owed: number
  total_commissions_paid: number
}

export interface CreateAffiliateRequest {
  code: string
  name?: string
  type?: 'promo' | 'member'
  discount_percent?: number
  usage_limit?: number
  is_active?: boolean
}

export interface AdminSettingsResponse {
  wallets: Record<string, string>
  payment_networks: PaymentNetworkConfig[]
  guild_settings?: GuildSettingsConfig[]
  smtp_host: string
  smtp_port: number
  smtp_user: string
  admin_email: string
  price_per_month_usd: number
  payment_tolerance_usd: number
}

export interface AdminPasswordChangeRequest {
  current_password: string
  new_password: string
}

export interface AdminPasswordChangeResponse {
  status: string
  password_version: number
  updated_at: string
}

export interface ExtendSubscriberResponse {
  status: string
  new_expires: string
}

export interface CommissionResponse {
  status: string
  commission_count: number
  total_paid: number
}

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
  const token = localStorage.getItem('admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('token_expires_at')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const paymentAPI = {
  async getNetworks(): Promise<NetworkInfo[]> {
    const { data } = await apiClient.get('/payment/networks')
    return data.networks || data
  },

  async initiate(request: PaymentInitiateRequest): Promise<PaymentInitiateResponse> {
    const { data } = await apiClient.post<RawPaymentInitiateResponse>('/payment/initiate', request)
    return {
      ...data,
      amount_usd: Number(data.amount_usd),
      discount_applied: Number(data.discount_applied),
      discount_percent:
        data.discount_percent === null || data.discount_percent === undefined
          ? undefined
          : Number(data.discount_percent),
    }
  },

  async submitProof(pendingId: string, txHashOrUrl: string): Promise<PaymentProofSubmitResponse> {
    const { data } = await apiClient.post('/payment/proof', {
      pending_id: pendingId,
      tx_hash_or_url: txHashOrUrl,
    })
    return data
  },

  async checkStatus(pendingId: string): Promise<PaymentStatusResponse> {
    const { data } = await apiClient.get(`/payment/status/${pendingId}`)
    return data
  },
}

export const adminAPI = {
  async login(password: string): Promise<AdminLoginResponse> {
    const { data } = await apiClient.post('/admin/login', { password })
    return data
  },

  async logout(): Promise<void> {
    await apiClient.post('/admin/logout')
  },

  async getDashboard(): Promise<DashboardResponse> {
    const { data } = await apiClient.get('/admin/dashboard')
    return data
  },

  async getSubscribers(page: number = 1, search?: string, activeOnly?: boolean): Promise<SubscribersResponse> {
    const { data } = await apiClient.get('/admin/subscribers', {
      params: { page, search, active_only: activeOnly || undefined },
    })
    return data
  },

  async extendSubscriber(subscriberId: string, months: number): Promise<ExtendSubscriberResponse> {
    const { data } = await apiClient.post(`/admin/subscribers/${subscriberId}/extend`, { months })
    return data
  },

  async revokeSubscriber(subscriberId: string): Promise<void> {
    await apiClient.delete(`/admin/subscribers/${subscriberId}`)
  },

  async getAffiliates(page: number = 1, search?: string, activeOnly?: boolean): Promise<AffiliatesResponse> {
    const { data } = await apiClient.get('/admin/affiliates', {
      params: { page, search, active_only: activeOnly || undefined },
    })
    return data
  },

  async createAffiliate(affiliate: CreateAffiliateRequest): Promise<AffiliateResponse> {
    const { data } = await apiClient.post('/admin/affiliates', affiliate)
    return data
  },

  async updateAffiliate(
    id: string,
    affiliate: Partial<Pick<AffiliateResponse, 'name' | 'discount_percent' | 'commission_percent' | 'payout_wallet' | 'is_active'>>
  ): Promise<AffiliateResponse> {
    const { data } = await apiClient.put(`/admin/affiliates/${id}`, affiliate)
    return data
  },

  async deleteAffiliate(id: string): Promise<void> {
    await apiClient.delete(`/admin/affiliates/${id}`)
  },

  async getAffiliateDetail(id: string): Promise<AffiliateDetailResponse> {
    const { data } = await apiClient.get(`/admin/affiliates/${id}`)
    return data
  },

  async getAffiliateMembers(affiliateId: string): Promise<SubscribersResponse> {
    const { data } = await apiClient.get(`/admin/affiliates/${affiliateId}/members`)
    return data
  },

  async markCommissionsPaid(affiliateId: string, commissionIds: string[]): Promise<CommissionResponse> {
    const { data } = await apiClient.post(`/admin/affiliates/${affiliateId}/mark-paid`, {
      commission_ids: commissionIds,
    })
    return data
  },

  async markAffiliateCommissionsPaid(affiliateId: string): Promise<void> {
    await apiClient.post(`/admin/affiliates/${affiliateId}/mark-all-paid`)
  },

  async getSettings(): Promise<AdminSettingsResponse> {
    const { data } = await apiClient.get('/admin/settings')
    return {
      ...data,
      price_per_month_usd: Number(data.price_per_month_usd),
      payment_tolerance_usd: Number(data.payment_tolerance_usd),
      payment_networks: Array.isArray(data.payment_networks)
        ? data.payment_networks.map((network: PaymentNetworkConfig) => ({
            ...network,
            min_confirmations: Number(network.min_confirmations),
            tolerance_usd: Number(network.tolerance_usd),
            is_active: Boolean(network.is_active),
          }))
        : [],
    }
  },

  async updateSettings(settings: Partial<Omit<AdminSettingsResponse, 'payment_networks'>> & { payment_networks?: PaymentNetworkUpdate[]; smtp_pass?: string }): Promise<AdminSettingsResponse> {
    const { data } = await apiClient.put('/admin/settings', settings)
    return {
      ...data,
      price_per_month_usd: Number(data.price_per_month_usd),
      payment_tolerance_usd: Number(data.payment_tolerance_usd),
      payment_networks: Array.isArray(data.payment_networks)
        ? data.payment_networks.map((network: PaymentNetworkConfig) => ({
            ...network,
            min_confirmations: Number(network.min_confirmations),
            tolerance_usd: Number(network.tolerance_usd),
            is_active: Boolean(network.is_active),
          }))
        : [],
    }
  },

  async changePassword(request: AdminPasswordChangeRequest): Promise<AdminPasswordChangeResponse> {
    const { data } = await apiClient.post('/admin/password', request)
    return data
  },
}

export default apiClient
