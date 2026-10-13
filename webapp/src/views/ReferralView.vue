<template>
  <div class="space-y-4">
    <!-- Referral Banner -->
    <div class="bg-tg-sec rounded-2xl p-4 border border-gray-700/30 space-y-3">
      <div class="flex items-center gap-2">
        <span class="text-2xl">🤝</span>
        <div>
          <h2 class="text-sm font-bold">همکاری در فروش و دعوت دوستان</h2>
          <p class="text-[11px] text-tg-hint">با معرفی دوستان خود، پورسانت نقدی دریافت کنید!</p>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-2 text-xs pt-1">
        <div class="bg-tg/50 p-2.5 rounded-xl border border-gray-700/20 text-center">
          <span class="text-[10px] text-tg-hint block">درصد پورسانت</span>
          <span class="font-bold text-amber-400 mt-0.5 block">{{ refData.commission_percent }}٪</span>
        </div>
        <div class="bg-tg/50 p-2.5 rounded-xl border border-gray-700/20 text-center">
          <span class="text-[10px] text-tg-hint block">دوستان معرفی‌شده</span>
          <span class="font-bold text-emerald-400 mt-0.5 block">{{ refData.total_referrals }} نفر</span>
        </div>
      </div>
    </div>

    <!-- Referral Link -->
    <div v-if="refData.link" class="bg-tg-sec rounded-2xl p-4 border border-gray-700/30 space-y-2">
      <label class="text-xs font-semibold block">لینک اختصاصی شما:</label>
      <div class="flex items-center gap-2">
        <input
          type="text"
          readonly
          :value="refData.link"
          class="flex-1 bg-tg border border-gray-700/50 rounded-xl px-3 py-2 text-xs text-left text-gray-300 font-mono focus:outline-none"
        />
        <button
          @click="copyLink"
          class="btn-tg px-4 py-2 rounded-xl text-xs font-semibold shrink-0 active:scale-95 transition"
        >
          {{ copied ? 'کپی شد ✓' : 'کپی لینک' }}
        </button>
      </div>
    </div>

    <!-- Total Earned Card -->
    <div class="bg-tg-sec/50 rounded-2xl p-4 border border-gray-700/20 flex justify-between items-center text-xs">
      <span class="text-tg-hint">کل درآمد کسب‌شده از معرف:</span>
      <span class="font-bold text-emerald-400 text-sm">
        {{ Number(refData.total_earned).toLocaleString('fa-IR') }} تومان
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getReferral } from '@/api'

const refData = ref({
  referral_enabled: true,
  code: '',
  link: '',
  total_earned: 0,
  total_referrals: 0,
  commission_percent: 10
})
const copied = ref(false)

const loadReferral = async () => {
  try {
    const { data } = await getReferral()
    refData.value = data
  } catch (err) {
    console.error('Failed to load referral:', err)
  }
}

const copyLink = () => {
  if (refData.value.link) {
    navigator.clipboard.writeText(refData.value.link)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  }
}

onMounted(() => {
  loadReferral()
})
</script>
