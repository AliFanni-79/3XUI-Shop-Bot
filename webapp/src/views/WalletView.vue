<template>
  <div class="space-y-4">
    <!-- Balance Card -->
    <div class="bg-gradient-to-br from-tg-button/20 to-tg-sec border border-tg-button/30 rounded-2xl p-5 shadow-sm space-y-2">
      <span class="text-xs text-tg-hint block">موجودی کیف پول</span>
      <div class="flex items-baseline gap-1.5">
        <span class="text-2xl font-black text-tg">{{ Number(walletData.balance).toLocaleString('fa-IR') }}</span>
        <span class="text-xs text-tg-hint">تومان</span>
      </div>
      <p class="text-[11px] text-tg-hint pt-2 border-t border-gray-700/20">
        💡 با موجودی کیف پول می‌توانید در کسری از ثانیه پلن‌های جدید را فعال کنید.
      </p>
    </div>

    <!-- Code Entry Card (Gift / Discount) -->
    <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
      <div class="flex items-center gap-2">
        <span class="text-base">🎁</span>
        <div>
          <h3 class="text-xs font-bold text-tg">ثبت کد هدیه یا کد تخفیف</h3>
          <p class="text-[10px] text-tg-hint">کد هدیه مستقیماً کیف پول را شارژ می‌کند و کد تخفیف در پنل ذخیره می‌شود.</p>
        </div>
      </div>

      <div class="flex gap-2">
        <input
          type="text"
          v-model="codeInput"
          @keyup.enter="handleRedeemCode"
          placeholder="کد را اینجا وارد کنید (مثلاً: OFF50 یا GIFT100)..."
          class="flex-1 bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs font-mono uppercase text-left tracking-wider placeholder:text-right placeholder:font-sans placeholder:tracking-normal"
          dir="ltr"
        />
        <button
          @click="handleRedeemCode"
          :disabled="submittingCode || !codeInput.trim()"
          class="bg-tg-button text-white px-4 py-2 rounded-xl text-xs font-bold hover:brightness-110 disabled:opacity-50 transition shrink-0 flex items-center gap-1.5"
        >
          <span v-if="submittingCode" class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
          <span>بررسی و ثبت</span>
        </button>
      </div>

      <!-- Alert message for code redemption -->
      <div
        v-if="codeMessage"
        class="p-2.5 rounded-xl text-xs flex items-center justify-between"
        :class="codeSuccess ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'"
      >
        <span>{{ codeMessage }}</span>
        <button @click="codeMessage = ''" class="text-xs opacity-70 hover:opacity-100 mr-2">✕</button>
      </div>
    </div>

    <!-- Active Saved Discounts Section -->
    <div v-if="savedDiscounts.length" class="space-y-2.5">
      <div class="flex items-center justify-between px-1">
        <h3 class="text-xs font-bold text-tg flex items-center gap-1.5">
          <span>🎟 کدهای تخفیف فعال شما</span>
          <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-blue-500/20 text-blue-300 font-mono">
            {{ savedDiscounts.length }}
          </span>
        </h3>
        <span class="text-[10px] text-tg-hint">معتبر برای خریدهای بعدی</span>
      </div>

      <div class="space-y-2.5">
        <div
          v-for="d in savedDiscounts"
          :key="d.code"
          class="bg-tg-sec p-3.5 rounded-2xl border border-blue-500/30 space-y-2.5 shadow-sm"
        >
          <!-- Header: Code, Title, Status Badge -->
          <div class="flex items-start justify-between gap-2">
            <div>
              <div class="flex items-center gap-2">
                <span class="font-mono font-black text-sm text-blue-400 bg-black/25 px-2.5 py-0.5 rounded-lg border border-blue-500/30" dir="ltr">
                  {{ d.code }}
                </span>
                <span class="font-bold text-xs text-tg">{{ d.title }}</span>
              </div>
              <span class="text-[11px] text-emerald-400 font-bold block mt-1">
                ✨ مزیت مرحله فعلی: {{ d.benefit_text }}
              </span>
            </div>

            <span class="px-2 py-0.5 rounded-lg text-[10px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shrink-0">
              قابل استفاده ✓
            </span>
          </div>

          <!-- Badges: Remaining Days & Remaining Uses -->
          <div class="flex flex-wrap items-center gap-1.5 text-[11px]">
            <span
              v-if="d.remaining_days !== null && d.remaining_days !== undefined"
              class="px-2 py-0.5 rounded-lg font-medium bg-amber-500/15 text-amber-300 border border-amber-500/20"
            >
              ⏳ {{ d.remaining_days }} روز از مهلت مانده
            </span>
            <span
              v-else
              class="px-2 py-0.5 rounded-lg text-tg-hint bg-gray-800/60"
            >
              ♾ بدون محدودیت زمانی
            </span>

            <span
              v-if="d.remaining_uses !== null && d.remaining_uses !== undefined"
              class="px-2 py-0.5 rounded-lg font-medium bg-purple-500/15 text-purple-300 border border-purple-500/20"
            >
              🔄 {{ d.remaining_uses }} بار استفاده باقیمانده
            </span>
            <span
              v-else
              class="px-2 py-0.5 rounded-lg text-tg-hint bg-gray-800/60"
            >
              🔄 استفاده نامحدود
            </span>
          </div>

          <!-- Tiered Steps Breakdown (if stepped) -->
          <div v-if="d.steps && d.steps.length > 1" class="space-y-1 bg-tg/60 p-2.5 rounded-xl border border-gray-700/30">
            <span class="text-[10px] font-bold text-tg-hint block">حالت پلکانی تخفیف:</span>
            <div class="flex flex-wrap gap-1.5">
              <div
                v-for="(st, idx) in d.steps"
                :key="idx"
                class="px-2 py-0.5 rounded-lg text-[10px] flex items-center gap-1 border transition"
                :class="st.step === d.step_index
                  ? 'bg-amber-500/20 border-amber-500/60 text-amber-300 font-bold'
                  : 'bg-tg border-gray-700/40 text-tg-hint'"
              >
                <span>
                  {{ idx === d.steps.length - 1 && st.repeat_after ? `خرید ${idx + 1} به بعد:` : `خرید ${idx + 1}:` }}
                </span>
                <span class="font-bold text-emerald-300">
                  {{ st.discount_type === 'FIXED' ? Number(st.discount_value).toLocaleString('fa-IR') + ' ت' : st.discount_value + '٪' }}
                </span>
                <span v-if="Number(st.cashback_percent) > 0" class="text-cyan-300">
                  + {{ st.cashback_percent }}٪ کش‌بک
                </span>
                <span v-if="st.step === d.step_index" class="text-[9px] text-amber-300 font-black">
                  👈 (نوبت شما)
                </span>
              </div>
            </div>
          </div>

          <!-- Description (if provided by admin) -->
          <div v-if="d.description" class="bg-tg/40 p-2.5 rounded-xl border border-gray-700/20 text-[11px] text-tg-hint space-y-0.5">
            <span class="font-bold text-tg block text-[10px]">📝 توضیحات:</span>
            <p class="leading-relaxed whitespace-pre-line">{{ d.description }}</p>
          </div>

          <!-- Action Button: «کپی و استفاده» -> Copies Code and Redirects to Store -->
          <div class="pt-1 flex justify-end">
            <button
              type="button"
              @click="copyAndUseDiscount(d.code)"
              :disabled="copiedCode === d.code"
              class="w-full sm:w-auto bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold px-4 py-2 rounded-xl text-xs flex items-center justify-center gap-1.5 shadow transition active:scale-95 disabled:opacity-80"
            >
              <template v-if="copiedCode === d.code">
                <span>✓</span>
                <span>کپی شد! در حال انتقال...</span>
              </template>
              <template v-else>
                <span>📋</span>
                <span>کپی و استفاده</span>
                <span>←</span>
              </template>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Transactions List -->
    <div class="space-y-2">
      <h3 class="text-xs font-bold text-tg-hint px-1">تاریخچه تراکنش‌های کیف پول</h3>

      <div v-if="loading" class="py-8 flex justify-center">
        <div class="w-5 h-5 border-2 border-tg-button border-t-transparent rounded-full animate-spin"></div>
      </div>

      <div v-else-if="walletData.transactions.length" class="space-y-2">
        <div
          v-for="tx in walletData.transactions"
          :key="tx.id"
          class="bg-tg-sec p-3 rounded-xl border border-gray-700/20 flex items-center justify-between text-xs"
        >
          <div>
            <span class="font-semibold block text-tg">{{ tx.description || tx.type }}</span>
            <span class="text-[10px] text-tg-hint block mt-0.5">شناسه: #{{ tx.id }}</span>
          </div>

          <div class="text-left">
            <span
              class="font-bold block"
              :class="tx.amount > 0 ? 'text-emerald-400' : 'text-rose-400'"
            >
              {{ tx.amount > 0 ? '+' : '' }}{{ Number(tx.amount).toLocaleString('fa-IR') }}
            </span>
            <span class="text-[10px] text-tg-hint">تومان</span>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else class="text-center py-8 bg-tg-sec/40 rounded-xl border border-dashed border-gray-700/30">
        <p class="text-xs text-tg-hint">تراکنشی در کیف پول ثبت نشده است.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getWallet, getWalletDiscounts, redeemWalletCode } from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const walletData = ref({
  balance: 0,
  transactions: []
})
const savedDiscounts = ref([])
const loading = ref(true)

const codeInput = ref('')
const submittingCode = ref(false)
const codeMessage = ref('')
const codeSuccess = ref(false)

const loadWallet = async () => {
  try {
    const { data } = await getWallet()
    walletData.value = data
  } catch (err) {
    console.error('Failed to load wallet:', err)
  }
}

const loadDiscounts = async () => {
  try {
    const { data } = await getWalletDiscounts()
    savedDiscounts.value = data.discounts || []
  } catch (err) {
    console.error('Failed to load saved discounts:', err)
  }
}

const handleRedeemCode = async () => {
  const code = codeInput.value.trim()
  if (!code) return
  submittingCode.value = true
  codeMessage.value = ''
  try {
    const { data } = await redeemWalletCode(code)
    codeSuccess.value = true
    codeMessage.value = data.message || 'عملیات با موفقیت انجام شد.'
    codeInput.value = ''
    if (data.type === 'GIFT') {
      if (data.balance !== undefined) {
        walletData.value.balance = data.balance
        auth.balance = data.balance
      }
      await loadWallet()
    } else {
      await loadDiscounts()
    }
  } catch (err) {
    codeSuccess.value = false
    codeMessage.value = err.response?.data?.detail || 'کد وارد شده معتبر نمی‌باشد.'
  } finally {
    submittingCode.value = false
  }
}

const copiedCode = ref(null)

const copyToClipboard = async (text) => {
  let success = false
  if (navigator?.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      success = true
    } catch (_) {}
  }
  if (!success) {
    try {
      const el = document.createElement('textarea')
      el.value = text
      el.setAttribute('readonly', '')
      el.style.position = 'fixed'
      el.style.left = '-9999px'
      el.style.top = '-9999px'
      el.style.opacity = '0'
      document.body.appendChild(el)
      el.select()
      el.setSelectionRange(0, 99999)
      success = document.execCommand('copy')
      document.body.removeChild(el)
    } catch (_) {}
  }
  return success
}

const copyAndUseDiscount = async (code) => {
  if (!code) return
  copiedCode.value = code
  await copyToClipboard(code)

  try {
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
  } catch (_) {}

  setTimeout(() => {
    router.push({ path: '/store', query: { code } })
  }, 350)
}

const goToStore = () => {
  router.push('/store')
}

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([loadWallet(), loadDiscounts()])
  } finally {
    loading.value = false
  }
})
</script>
