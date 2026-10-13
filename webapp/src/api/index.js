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
export const initCardOrder = (planId, discountCode = null, customName = null) =>
  client.post('/orders/init-card', { plan_id: planId, discount_code: discountCode, custom_name: customName })

/**
 * Pay immediately from wallet balance.
 */
export const initWalletOrder = (planId, discountCode = null, customName = null) =>
  client.post('/orders/init-wallet', { plan_id: planId, discount_code: discountCode, custom_name: customName })

// ─── Custom Plan Builder ─────────────────────────────────────────────────────
export const getBuilderConfig = () => client.get('/builder/config')

export const calculateBuilderPlan = (months, volumeGb, ipLimit, discountCode = null) =>
  client.post('/builder/calculate', {
    months,
    volume_gb: volumeGb,
    ip_limit: ipLimit,
    discount_code: discountCode,
  })

export const initCustomCardOrder = (months, volumeGb, ipLimit, discountCode = null, customName = null) =>
  client.post('/orders/init-custom-card', {
    months,
    volume_gb: volumeGb,
    ip_limit: ipLimit,
    discount_code: discountCode,
    custom_name: customName,
  })

export const initCustomWalletOrder = (months, volumeGb, ipLimit, discountCode = null, customName = null) =>
  client.post('/orders/init-custom-wallet', {
    months,
    volume_gb: volumeGb,
    ip_limit: ipLimit,
    discount_code: discountCode,
    custom_name: customName,
  })

// ─── Payment Gateways & Stars ────────────────────────────────────────────────
export const getActiveGateways = () => client.get('/gateways/active')
export const initGatewayOrder = (payload) => client.post('/orders/init-gateway', payload)
export const initStarsOrder = (payload) => client.post('/orders/init-stars', payload)

// ─── Admin — Payments & Gateways ─────────────────────────────────────────────
export const getAdminPayments = () => client.get('/admin/payments')
export const saveAdminPayments = (settings) => client.post('/admin/payments', settings)
export const getAdminGateways = () => client.get('/admin/gateways')
export const saveAdminGateways = (settings) => client.post('/admin/gateways', settings)

// ─── Admin — Builder Defaults ────────────────────────────────────────────────
export const getAdminBuilderDefaults = () => client.get('/admin/builder/defaults')
export const saveAdminBuilderDefaults = (settings) => client.post('/admin/builder/defaults', settings)

// ─── Admin — Plans CRUD ──────────────────────────────────────────────────────
export const getAdminPlans = () => client.get('/admin/plans')
export const createAdminPlan = (plan) => client.post('/admin/plans', plan)
export const updateAdminPlan = (id, plan) => client.put(`/admin/plans/${id}`, plan)
export const deleteAdminPlan = (id) => client.delete(`/admin/plans/${id}`)
export const toggleAdminPlan = (id) => client.post(`/admin/plans/${id}/toggle`)

// ─── Admin — Users Management ────────────────────────────────────────────────
export const getAdminUsers = (limit = 100, offset = 0, q = null) =>
  client.get('/admin/users', { params: { limit, offset, ...(q ? { q } : {}) } })
export const getAdminUserDetail = (id) => client.get(`/admin/users/${id}`)
export const adjustUserBalance = (id, amount, reason = null) =>
  client.post(`/admin/users/${id}/balance`, { amount, reason })
export const toggleUserStatus = (id) => client.post(`/admin/users/${id}/toggle-status`)

// ─── Admin — Blacklist ───────────────────────────────────────────────────────
export const getAdminBlacklist = () => client.get('/admin/blacklist')
export const addAdminBlacklist = (userId, reason = 'Blocked by admin') =>
  client.post('/admin/blacklist/add', { user_id: userId, reason })
export const removeAdminBlacklist = (userId) =>
  client.post('/admin/blacklist/remove', { user_id: userId })

// ─── Admin — Admins Management ───────────────────────────────────────────────
export const getAdminList = () => client.get('/admin/admins')
export const addAdmin = (userId, role = 'ADMIN') =>
  client.post('/admin/admins/add', { user_id: userId, role })
export const removeAdmin = (userId) =>
  client.post('/admin/admins/remove', { user_id: userId })

// ─── Admin — Backups & Ops Mode ─────────────────────────────────────────────
export const getAdminBackups = () => client.get('/admin/backups')
export const createAdminBackup = () => client.post('/admin/backups/create')
export const getAdminOpsMode = () => client.get('/admin/ops/mode')
export const saveAdminOpsMode = (mode) => client.post('/admin/ops/mode', { mode })

// ─── Admin — Server Status ───────────────────────────────────────────────────
export const getAdminServerStatus = () => client.get('/admin/server-status')

// ─── Admin — Orders & Broadcast ──────────────────────────────────────────────
export const getAdminStats = () => client.get('/admin/stats')
export const getAdminOrders = (status = 'PENDING') => client.get('/admin/orders', { params: { status_filter: status } })
export const approveOrder = (id) => client.post(`/admin/orders/${id}/approve`)
export const rejectOrder = (id, reason = null) => client.post(`/admin/orders/${id}/reject`, { reason })
export const sendBroadcast = (message, audience = 'all') =>
  client.post('/admin/broadcast', { message, audience })

// ─── Branding / Config ───────────────────────────────────────────────────────
export const getAppConfig = () => client.get('/app/config')
export const getAdminBranding = () => client.get('/admin/branding')
export const saveAdminBranding = (payload) => client.post('/admin/branding', payload)

export default client

