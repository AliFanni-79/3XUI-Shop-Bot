<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-bold flex items-center gap-1.5">
        <span>📡</span>
        <span>سرویس‌های من</span>
      </h2>
      <button @click="loadServices" class="text-xs text-tg-button hover:underline flex items-center gap-1">
        <span>🔄</span>
        <span>بروزرسانی</span>
      </button>
    </div>

    <!-- Filter Tabs (if we have services) -->
    <div v-if="!loading && services.length > 0" class="flex gap-1.5 bg-tg-sec p-1 rounded-xl border border-gray-700/30 text-xs">
      <button
        @click="currentFilter = 'all'"
        class="flex-1 py-1.5 rounded-lg font-medium transition text-center"
        :class="currentFilter === 'all' ? 'btn-tg shadow-sm font-bold' : 'text-tg-hint hover:text-tg'"
      >
        همه ({{ services.length }})
      </button>
      <button
        @click="currentFilter = 'active'"
        class="flex-1 py-1.5 rounded-lg font-medium transition text-center"
        :class="currentFilter === 'active' ? 'btn-tg shadow-sm font-bold' : 'text-tg-hint hover:text-tg'"
      >
        🟢 فعال ({{ activeServices.length }})
      </button>
      <button
        v-if="deactivatedServices.length > 0"
        @click="currentFilter = 'deactivated'"
        class="flex-1 py-1.5 rounded-lg font-medium transition text-center"
        :class="currentFilter === 'deactivated' ? 'btn-tg shadow-sm font-bold' : 'text-tg-hint hover:text-tg'"
      >
        ⏸ غیرفعال ({{ deactivatedServices.length }})
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="py-12 flex justify-center">
      <div class="w-6 h-6 border-2 border-tg-button border-t-transparent rounded-full animate-spin"></div>
    </div>

    <!-- Filter Empty Notice -->
    <div
      v-else-if="services.length > 0 && displayedServices.length === 0"
      class="text-center py-8 bg-tg-sec/50 rounded-2xl border border-dashed border-gray-700/40 space-y-2 p-4"
    >
      <span class="text-2xl block">🔍</span>
      <p class="text-xs text-tg-hint">
        {{ currentFilter === 'active' ? 'شما در حال حاضر سرویس فعالی ندارید.' : 'سرویس غیرفعالی در ۳۰ روز گذشته یافت نشد.' }}
      </p>
      <button
        @click="currentFilter = 'all'"
        class="text-xs text-tg-button hover:underline font-semibold"
      >
        مشاهده همه سرویس‌ها
      </button>
    </div>

    <!-- Services List -->
    <div v-else-if="displayedServices.length" class="space-y-3">
      <div
        v-for="(svc, index) in displayedServices"
        :key="svc.tx_id || svc.email || index"
        class="rounded-2xl p-4 border shadow-sm space-y-3 transition"
        :class="svc.is_active ? 'bg-tg-sec border-gray-700/30' : 'bg-tg-sec/70 border-gray-700/50 opacity-95'"
      >
        <div class="flex justify-between items-start gap-2">
          <div class="min-w-0 flex-1">
            <h3 class="font-bold text-sm flex items-center gap-1.5 truncate">
              <span>{{ svc.kind === 'TRIAL' ? '🎁' : (svc.is_active ? '⚡️' : '⏸') }}</span>
              <span class="truncate">{{ svc.plan_name || 'سرویس اشتراکی' }}</span>
            </h3>
            <span class="text-[11px] text-tg-hint block mt-0.5 font-mono truncate">
              نام کانفیگ: {{ svc.custom_name || svc.email }}
            </span>
          </div>

          <span
            class="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
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

        <!-- Subscription URL (Active Services) -->
        <div v-if="svc.is_active && svc.sub_url" class="space-y-2 pt-1 border-t border-gray-700/20">
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

        <!-- Rebuy Action Bar (Deactivated Services) -->
        <div
          v-else-if="!svc.is_active"
          class="pt-3 border-t border-gray-700/30 flex items-center justify-between gap-2"
        >
          <div class="text-[11px] text-tg-hint flex items-center gap-1 truncate">
            <span>{{ svc.plan_available ? '📦 پلن در فروشگاه موجود است' : '🛠 ساخت در پلن دلخواه' }}</span>
          </div>
          <button
            @click="handleRebuy(svc)"
            class="btn-tg px-3.5 py-1.5 rounded-xl text-xs font-bold shrink-0 flex items-center gap-1.5 shadow-sm active:scale-95 transition"
          >
            <span>🔄</span>
            <span>خرید مجدد</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Completely Empty State -->
    <div v-else class="text-center py-12 bg-tg-sec/50 rounded-2xl border border-dashed border-gray-700/40 space-y-3">
      <span class="text-3xl block">🔌</span>
      <p class="text-xs text-tg-hint">شما در حال حاضر هیچ سرویسی ندارید.</p>
      <router-link to="/" class="inline-block btn-tg text-xs font-semibold px-4 py-2 rounded-xl shadow">
        مشاهده پلن‌ها و خرید
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getServices } from '@/api'

const router = useRouter()
const services = ref([])
const loading = ref(true)
const copiedUrl = ref('')
const currentFilter = ref('all') // 'all' | 'active' | 'deactivated'

const activeServices = computed(() => services.value.filter(s => s.is_active))
const deactivatedServices = computed(() => services.value.filter(s => !s.is_active))

const displayedServices = computed(() => {
  if (currentFilter.value === 'active') return activeServices.value
  if (currentFilter.value === 'deactivated') return deactivatedServices.value
  return services.value
})

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
  if (!url) return
  navigator.clipboard.writeText(url)
  copiedUrl.value = url
  setTimeout(() => {
    copiedUrl.value = ''
  }, 2000)
}

const handleRebuy = (svc) => {
  if (svc.plan_available && svc.plan_id) {
    // Plan is active in catalog -> navigate to pre-made plans buy menu
    router.push({
      path: '/',
      query: {
        mode: 'catalog',
        category_id: svc.category_id || undefined,
        plan_id: svc.plan_id
      }
    })
  } else {
    // Plan is not available in catalog (or was custom) -> navigate to custom builder
    const months = svc.days ? Math.max(1, Math.round(svc.days / 30)) : 1
    const validMonths = [1, 3, 6, 12].includes(months) ? months : 1
    router.push({
      path: '/',
      query: {
        mode: 'builder',
        months: validMonths,
        volume: svc.volume_gb || 0,
        ip: svc.ip_limit || 1
      }
    })
  }
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
    case 'REVOKED':
      return 'لغو شده'
    default:
      return status || 'غیرفعال'
  }
}

const statusBadgeClass = (status) => {
  switch (status) {
    case 'APPROVED':
    case 'ACTIVE':
      return 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
    case 'CREATING':
    case 'PROCESSING':
      return 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
    case 'EXPIRED':
      return 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
    case 'REVOKED':
      return 'bg-red-600/20 text-red-400 border border-red-500/30'
    default:
      return 'bg-gray-500/15 text-gray-400 border border-gray-500/30'
  }
}

onMounted(() => {
  loadServices()
})
</script>
