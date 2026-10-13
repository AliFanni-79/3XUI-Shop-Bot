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
import { getWallet } from '@/api'

const walletData = ref({
  balance: 0,
  transactions: []
})
const loading = ref(true)

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
