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

// ─── Plans & Trial & Promotions ──────────────────────────────────────────────
export const getPlans = () => client.get('/plans')
export const getActivePromotions = () => client.get('/promotions/active')
export const validateDiscountCode = (code = null, basePrice = 0, kind = 'NEW') =>
  client.post('/discounts/validate', { code, base_price: basePrice, kind })
export const getTrialStatus = () => client.get('/trial/status')
export const claimFreeTrial = (customName = null) =>
  client.post('/trial/claim', { custom_name: customName })

// ─── Services ────────────────────────────────────────────────────────────────
export const getServices = () => client.get('/services')

// ─── Wallet ──────────────────────────────────────────────────────────────────
export const getWallet = () => client.get('/wallet')
export const redeemWalletCode = (code) => client.post('/wallet/code/redeem', { code })
export const getWalletDiscounts = () => client.get('/wallet/discounts')

// ─── Codes (Discounts & Gifts) ───────────────────────────────────────────────
export const applyOrCheckCode = (code, price = null) =>
  client.post('/codes/apply', { code, price })

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

export const initCustomCardOrder = (months, volumeGb, ipLimit, discountCode = null, customName = null, serverIds = null) =>
  client.post('/orders/init-custom-card', {
    months,
    volume_gb: volumeGb,
    ip_limit: ipLimit,
    discount_code: discountCode,
    custom_name: customName,
    server_ids: serverIds,
  })

export const initCustomWalletOrder = (months, volumeGb, ipLimit, discountCode = null, customName = null, serverIds = null) =>
  client.post('/orders/init-custom-wallet', {
    months,
    volume_gb: volumeGb,
    ip_limit: ipLimit,
    discount_code: discountCode,
    custom_name: customName,
    server_ids: serverIds,
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

// ─── Admin — Sanaei 3x-ui & Groups ──────────────────────────────────────────
export const getAdminXuiGroups = () => client.get('/admin/xui/groups')
export const reconcileAdminXuiGroups = () => client.post('/admin/xui/groups/reconcile')
export const testAdminXui = () => client.get('/admin/xui/test')
export const replaceAdminDomain = (oldDomain, newDomain) =>
  client.post('/admin/xui/replace-domain', { old_domain: oldDomain, new_domain: newDomain })
export const deleteAdminPanelClient = (email) =>
  client.post('/admin/xui/delete-client', { email })

// ─── Admin — Rewards (Cashback, Discounts, Gifts) ───────────────────────────
export const getAdminRewards = () => client.get('/admin/rewards')
export const saveAdminCashback = (percent) => client.post('/admin/rewards/cashback', { percent })
export const createAdminDiscount = (payload) => client.post('/admin/rewards/discounts', payload)
export const toggleAdminDiscount = (code) => client.post(`/admin/rewards/discounts/${code}/toggle`)
export const deleteAdminDiscount = (code) => client.delete(`/admin/rewards/discounts/${code}`)
export const createAdminGift = (payload) => client.post('/admin/rewards/gifts', payload)
export const deleteAdminGift = (code) => client.delete(`/admin/rewards/gifts/${code}`)

// ─── Admin — Affiliate & Referrals ──────────────────────────────────────────
export const getAdminAffiliate = () => client.get('/admin/affiliate')
export const saveAdminAffiliate = (payload) => client.post('/admin/affiliate/settings', payload)

// ─── Admin — Content, Security & Notifications ──────────────────────────────
export const getAdminContentSecurity = () => client.get('/admin/content-security')
export const saveAdminContentSecurity = (payload) => client.post('/admin/content-security', payload)
export const checkAdminNotifications = () => client.post('/admin/notifications/check-now')

// ─── Admin — Plan Inbounds ───────────────────────────────────────────────────
export const getAdminInbounds = () => client.get('/admin/inbounds')
export const getAdminPlanInbounds = (planId) => client.get(`/admin/plans/${planId}/inbounds`)
export const toggleAdminPlanInbound = (planId, inboundId) =>
  client.post(`/admin/plans/${planId}/inbounds/toggle`, { inbound_id: inboundId })
export const resetAdminPlanInbounds = (planId) => client.post(`/admin/plans/${planId}/inbounds/reset`)

// ─── Admin — Server Profiles (Servers / Inbounds Grouping) ───────────────────
export const getAdminServers = () => client.get('/admin/servers')
export const createAdminServer = (payload) => client.post('/admin/servers', payload)
export const updateAdminServer = (id, payload) => client.put(`/admin/servers/${id}`, payload)
export const deleteAdminServer = (id) => client.delete(`/admin/servers/${id}`)
export const toggleAdminServer = (id) => client.post(`/admin/servers/${id}/toggle`)
export const autoGroupAdminServers = () => client.post('/admin/servers/auto-group')

// ─── Admin — Customer Services Management ────────────────────────────────────
export const getAdminServiceDetails = (email) => client.get(`/admin/services/${encodeURIComponent(email)}`)
export const updateAdminService = (email, payload) => client.post(`/admin/services/${encodeURIComponent(email)}`, payload)
export const resetAdminServiceTraffic = (email) => client.post(`/admin/services/${encodeURIComponent(email)}/reset-traffic`)
export const deleteAdminService = (email) => client.delete(`/admin/services/${encodeURIComponent(email)}`)

// ─── Admin — Categories ──────────────────────────────────────────────────────
export const getAdminCategories = () => client.get('/admin/categories')
export const createAdminCategory = (payload) => client.post('/admin/categories', payload)
export const updateAdminCategory = (id, payload) => client.put(`/admin/categories/${id}`, payload)
export const deleteAdminCategory = (id) => client.delete(`/admin/categories/${id}`)

// ─── Admin — Volume Packs ────────────────────────────────────────────────────
export const getAdminVolumePacks = () => client.get('/admin/volume-packs')
export const createAdminVolumePack = (payload) => client.post('/admin/volume-packs', payload)
export const updateAdminVolumePack = (id, payload) => client.put(`/admin/volume-packs/${id}`, payload)
export const deleteAdminVolumePack = (id) => client.delete(`/admin/volume-packs/${id}`)
export const toggleAdminVolumePack = (id) => client.post(`/admin/volume-packs/${id}/toggle`)

// ─── Admin — Trial Plan Management ───────────────────────────────────────────
export const getAdminTrialSettings = () => client.get('/admin/trial/settings')
export const saveAdminTrialSettings = (payload) => client.post('/admin/trial/settings', payload)
export const toggleAdminTrialInbound = (inboundId) =>
  client.post('/admin/trial/inbounds/toggle', { inbound_id: inboundId })
export const resetAdminTrialInbounds = () => client.post('/admin/trial/inbounds/reset')
export const getAdminTrialOverrides = () => client.get('/admin/trial/overrides')
export const saveAdminTrialOverride = (payload) => client.post('/admin/trial/overrides', payload)
export const deleteAdminTrialOverride = (userId) => client.delete(`/admin/trial/overrides/${userId}`)

// ─── Admin — CRM & Service Claims ────────────────────────────────────────────
export const getAdminCrm = () => client.get('/admin/crm')
export const saveAdminCrmSettings = (payload) => client.post('/admin/crm/settings', payload)
export const approveAdminClaim = (claimId) => client.post(`/admin/crm/claims/${claimId}/approve`)
export const rejectAdminClaim = (claimId, reason = null) =>
  client.post(`/admin/crm/claims/${claimId}/reject`, { reason })

// ─── Admin — Guides ──────────────────────────────────────────────────────────
export const getAdminGuides = () => client.get('/admin/guides')
export const createAdminGuide = (payload) => client.post('/admin/guides', payload)
export const deleteAdminGuide = (id) => client.delete(`/admin/guides/${id}`)
export const toggleAdminGuides = () => client.post('/admin/guides/toggle')
export const promptAdminGuideBot = (platform, app_name = null) =>
  client.post('/admin/guides/prompt-bot', null, { params: { platform, app_name: app_name || undefined } })

// ─── Admin — Audit Log ───────────────────────────────────────────────────────
export const getAdminAudit = (limit = 50) => client.get('/admin/audit', { params: { limit } })
export const saveAdminAuditSettings = (payload) => client.post('/admin/audit/settings', payload)

// ─── Admin — Panel Snapshot ──────────────────────────────────────────────────
export const getAdminSnapshot = () => client.get('/admin/snapshot')
export const sendAdminSnapshot = () => client.post('/admin/snapshot/send')

// ─── Admin — App Version ─────────────────────────────────────────────────────
export const getAdminVersion = () => client.get('/admin/version')

export default client

