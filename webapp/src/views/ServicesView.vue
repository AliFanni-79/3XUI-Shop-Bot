<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-bold">📡 سرویس‌های فعال من</h2>
      <button @click="loadServices" class="text-xs text-tg-button hover:underline">
        🔄 بروزرسانی
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="py-12 flex justify-center">
      <div class="w-6 h-6 border-2 border-tg-button border-t-transparent rounded-full animate-spin"></div>
    </div>

    <!-- Services List -->
    <div v-else-if="services.length" class="space-y-3">
      <div
        v-for="(svc, index) in services"
        :key="index"
        class="bg-tg-sec rounded-2xl p-4 border border-gray-700/30 shadow-sm space-y-3"
      >
        <div class="flex justify-between items-start">
          <div>
            <h3 class="font-bold text-sm flex items-center gap-1.5">
              <span>⚡️</span>
              <span>{{ svc.plan_name || 'سرویس اشتراکی' }}</span>
            </h3>
            <span class="text-[11px] text-tg-hint block mt-0.5">نام کانفیگ: {{ svc.custom_name || svc.email }}</span>
          </div>

          <span
            class="text-[10px] font-bold px-2 py-0.5 rounded-full"
            :class="statusBadgeClass(svc.status)"
          >
            {{ formatStatus(svc.status) }}
          </span>
        </div>

        <!-- Details Grid -->
        <div class="grid grid-cols-2 gap-2 text-xs">
          <div class="bg-tg/50 p-2 rounded-xl border border-gray-700/20">
            <span class="text-[10px] text-tg-hint block">حجم</span>
            <span class="font-semibold">{{ svc.volume_gb > 0 ? `${svc.volume_gb} GB` : 'نامحدود' }}</span>
          </div>
          <div class="bg-tg/50 p-2 rounded-xl border border-gray-700/20">
            <span class="text-[10px] text-tg-hint block">اعتبار</span>
            <span class="font-semibold">{{ svc.days > 0 ? `${svc.days} روز` : '-' }}</span>
          </div>
        </div>

        <!-- Subscription URL -->
        <div v-if="svc.sub_url" class="space-y-2 pt-1 border-t border-gray-700/20">
          <label class="text-[11px] text-tg-hint block">لینک اتصال (Subscription Link):</label>
          <div class="flex items-center gap-2">
            <input
              type="text"
              readonly
              :value="svc.sub_url"
              class="flex-1 bg-tg border border-gray-700/50 rounded-xl px-2.5 py-1.5 text-[11px] text-left text-gray-300 font-mono focus:outline-none"
            />
            <button
              @click="copyUrl(svc.sub_url)"
              class="btn-tg px-3 py-1.5 rounded-xl text-xs font-semibold shrink-0 active:scale-95 transition"
            >
              {{ copiedUrl === svc.sub_url ? 'کپی شد ✓' : 'کپی' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-12 bg-tg-sec/50 rounded-2xl border border-dashed border-gray-700/40 space-y-3">
      <span class="text-3xl block">🔌</span>
      <p class="text-xs text-tg-hint">شما در حال حاضر هیچ سرویس فعالی ندارید.</p>
      <router-link to="/" class="inline-block btn-tg text-xs font-semibold px-4 py-2 rounded-xl shadow">
        مشاهده پلن‌ها و خرید
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getServices } from '@/api'

const services = ref([])
const loading = ref(true)
const copiedUrl = ref('')

const loadServices = async () => {
  loading.value = true
  try {
    const { data } = await getServices()
    services.value = data.services || []
  } catch (err) {
    console.error('Failed to load services:', err)
  } finally {
    loading.value = false
  }
}

const copyUrl = (url) => {
  navigator.clipboard.writeText(url)
  copiedUrl.value = url
  setTimeout(() => {
    copiedUrl.value = ''
  }, 2000)
}

const formatStatus = (status) => {
  switch (status) {
    case 'APPROVED':
    case 'ACTIVE':
      return 'فعال'
    case 'CREATING':
    case 'PROCESSING':
      return 'در حال ساخت'
    case 'EXPIRED':
      return 'منقضی شده'
    default:
      return status || 'فعال'
  }
}

const statusBadgeClass = (status) => {
  switch (status) {
    case 'APPROVED':
    case 'ACTIVE':
      return 'bg-emerald-500/15 text-emerald-400'
    case 'CREATING':
    case 'PROCESSING':
      return 'bg-amber-500/15 text-amber-400'
    case 'EXPIRED':
      return 'bg-rose-500/15 text-rose-400'
    default:
      return 'bg-blue-500/15 text-blue-400'
  }
}

onMounted(() => {
  loadServices()
})
</script>
