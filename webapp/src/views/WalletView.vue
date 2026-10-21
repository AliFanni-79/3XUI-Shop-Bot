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

    <!-- Redeem Gift / Check Code Card -->
    <div class="bg-tg-sec border border-gray-700/30 rounded-2xl p-4 space-y-2.5 shadow-sm">
      <div class="flex items-center gap-2">
        <span class="text-base">🎁</span>
        <span class="text-xs font-bold text-tg">ثبت کد هدیه یا بررسی تخفیف</span>
      </div>
      <p class="text-[11px] text-tg-hint leading-relaxed">
        اگر کد هدیه دارید، آن را وارد نمایید تا مستقیماً به موجودی کیف پول شما اضافه شود. کدهای تخفیف را می‌توانید هنگام خرید در منوی خرید اعمال فرمایید.
      </p>

      <div class="flex gap-2 pt-1">
        <input
          v-model="walletCodeInput"
          type="text"
          dir="ltr"
          placeholder="مثال: GIFT50 یا OFF20"
          class="flex-1 bg-tg border border-gray-700/50 rounded-xl px-3 py-2 text-xs text-center uppercase tracking-wider focus:outline-none focus:border-tg-button"
          @keyup.enter="handleWalletApplyCode"
        />
        <button
          type="button"
          @click="handleWalletApplyCode"
          :disabled="!walletCodeInput.trim() || walletCodeLoading"
          class="px-4 py-2 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1 shrink-0"
          :class="walletCodeInput.trim() && !walletCodeLoading ? 'btn-tg shadow active:scale-95' : 'bg-gray-700/30 text-gray-500 cursor-not-allowed'"
        >
          <span v-if="walletCodeLoading" class="w-3.5 h-3.5 border-2 border-white/60 border-t-transparent rounded-full animate-spin"></span>
          <span v-else>ثبت کد</span>
        </button>
      </div>

      <!-- Feedback message -->
      <div v-if="walletCodeResult" class="p-2.5 rounded-xl text-xs flex items-start gap-2 animate-fadeIn" :class="walletCodeResultClass">
        <span class="text-sm shrink-0">{{ walletCodeResultIcon }}</span>
        <span class="leading-relaxed">{{ walletCodeResult.message }}</span>
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
import { ref, computed, onMounted } from 'vue'
import { getWallet, applyOrCheckCode } from '@/api'

const walletData = ref({
  balance: 0,
  transactions: []
})
const loading = ref(true)

const walletCodeInput = ref('')
const walletCodeLoading = ref(false)
const walletCodeResult = ref(null)

const walletCodeResultClass = computed(() => {
  if (!walletCodeResult.value) return ''
  if (walletCodeResult.value.type === 'error') return 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
  if (walletCodeResult.value.type === 'gift') return 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
  return 'bg-amber-500/10 border border-amber-500/30 text-amber-300'
})

const walletCodeResultIcon = computed(() => {
  if (!walletCodeResult.value) return ''
  if (walletCodeResult.value.type === 'error') return '❌'
  if (walletCodeResult.value.type === 'gift') return '🎁'
  return '⚠️'
})

const handleWalletApplyCode = async () => {
  const code = walletCodeInput.value.trim()
  if (!code || walletCodeLoading.value) return

  walletCodeLoading.value = true
  walletCodeResult.value = null

  try {
    const res = await applyOrCheckCode(code, null)
    const data = res.data
    if (data.type === 'gift') {
      walletCodeResult.value = {
        type: 'gift',
        message: data.message || `کد هدیه با موفقیت اعمال شد و مبلغ ${Number(data.amount).toLocaleString('fa-IR')} تومان به موجودی کیف پول افزوده شد.`
      }
      walletCodeInput.value = ''
      await loadWallet()
    } else if (data.type === 'discount') {
      walletCodeResult.value = {
        type: 'discount',
        message: '⚠️ این کد یک کد تخفیف است و قابل شارژ به کیف پول نمی‌باشد. لطفاً هنگام ثبت سفارش در منوی خرید از آن استفاده نمایید.'
      }
    }
  } catch (err) {
    walletCodeResult.value = {
      type: 'error',
      message: err.response?.data?.detail || 'کد وارد شده معتبر نیست یا منقضی شده است.'
    }
  } finally {
    walletCodeLoading.value = false
  }
}

const loadWallet = async () => {
  loading.value = true
  try {
    const { data } = await getWallet()
    walletData.value = data
  } catch (err) {
    console.error('Failed to load wallet:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadWallet()
})
</script>
