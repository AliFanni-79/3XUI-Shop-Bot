/**
 * Axios API client.
 *
 * Automatically attaches the Telegram initData string as
 * `X-Telegram-Init-Data` header on every request so the FastAPI
 * backend can verify the user's identity.
 *
 * In dev mode (running Vite, no real Telegram context) the header
 * is simply omitted — the backend will return 401, which is expected.
 */
import axios from 'axios'

const initData = window.Telegram?.WebApp?.initData || ''

const client = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
    ...(initData ? { 'X-Telegram-Init-Data': initData } : {}),
  },
})

// ─── Auth ────────────────────────────────────────────────────────────────────
export const getMe = () => client.get('/auth/me')

// ─── Plans ───────────────────────────────────────────────────────────────────
export const getPlans = () => client.get('/plans')

// ─── Services ────────────────────────────────────────────────────────────────
export const getServices = () => client.get('/services')

// ─── Wallet ──────────────────────────────────────────────────────────────────
export const getWallet = () => client.get('/wallet')

// ─── Referral ────────────────────────────────────────────────────────────────
export const getReferral = () => client.get('/referral')

// ─── Guides ──────────────────────────────────────────────────────────────────
export const getGuides = () => client.get('/guides')

// ─── Orders ──────────────────────────────────────────────────────────────────
/**
 * Initiate a card-to-card order.
 * The bot will send a payment instruction message in the user's Telegram chat.
 * The user then sends their receipt photo there (not in the Mini App).
 */
export const initCardOrder = (planId, discountCode = null) =>
  client.post('/orders/init-card', { plan_id: planId, discount_code: discountCode })

/**
 * Pay immediately from wallet balance.
 */
export const initWalletOrder = (planId, discountCode = null) =>
  client.post('/orders/init-wallet', { plan_id: planId, discount_code: discountCode })

// ─── Custom Plan Builder ─────────────────────────────────────────────────────
export const getBuilderConfig = () => client.get('/builder/config')

export const calculateBuilderPlan = (months, volumeGb, ipLimit, discountCode = null) =>
  client.post('/builder/calculate', {
    months,
    volume_gb: volumeGb,
    ip_limit: ipLimit,
    discount_code: discountCode,
  })

export const initCustomCardOrder = (months, volumeGb, ipLimit, discountCode = null) =>
  client.post('/orders/init-custom-card', {
    months,
    volume_gb: volumeGb,
    ip_limit: ipLimit,
    discount_code: discountCode,
  })

export const initCustomWalletOrder = (months, volumeGb, ipLimit, discountCode = null) =>
  client.post('/orders/init-custom-wallet', {
    months,
    volume_gb: volumeGb,
    ip_limit: ipLimit,
    discount_code: discountCode,
  })

// ─── Payment Gateways ────────────────────────────────────────────────────────
export const getActiveGateways = () => client.get('/gateways/active')
export const initGatewayOrder = (payload) => client.post('/orders/init-gateway', payload)
export const getAdminGateways = () => client.get('/admin/gateways')
export const saveAdminGateways = (settings) => client.post('/admin/gateways', settings)

// ─── Admin ───────────────────────────────────────────────────────────────────
export const getAdminStats = () => client.get('/admin/stats')
export const getAdminOrders = (status = 'PENDING') => client.get('/admin/orders', { params: { status_filter: status } })
export const approveOrder = (id) => client.post(`/admin/orders/${id}/approve`)
export const rejectOrder = (id, reason = null) => client.post(`/admin/orders/${id}/reject`, { reason })
export const getAdminUsers = (limit = 100, offset = 0) => client.get('/admin/users', { params: { limit, offset } })
export const getAdminPlans = () => client.get('/admin/plans')
export const sendBroadcast = (message, audience = 'all') =>
  client.post('/admin/broadcast', { message, audience })

// ─── Branding / Config ───────────────────────────────────────────────────────
export const getAppConfig = () => client.get('/app/config')
export const getAdminBranding = () => client.get('/admin/branding')
export const saveAdminBranding = (payload) => client.post('/admin/branding', payload)

export default client

