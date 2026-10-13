<template>
  <div class="space-y-4">
    <!-- Top Mode Switcher: Pre-made Plans vs Custom Builder -->
    <div class="bg-tg-sec p-1 rounded-2xl border border-gray-700/30 flex text-xs">
      <button
        @click="activeMode = 'catalog'"
        class="flex-1 py-2 rounded-xl font-bold transition flex items-center justify-center gap-1.5"
        :class="activeMode === 'catalog' ? 'btn-tg shadow' : 'text-tg-hint hover:text-tg'"
      >
        <span>🛍</span>
        <span>پلن‌های آماده</span>
      </button>

      <button
        @click="activeMode = 'builder'"
        class="flex-1 py-2 rounded-xl font-bold transition flex items-center justify-center gap-1.5"
        :class="activeMode === 'builder' ? 'btn-tg shadow' : 'text-tg-hint hover:text-tg'"
      >
        <span>🛠</span>
        <span>ساخت پلن دلخواه</span>
      </button>
    </div>

    <!-- ===================================================================== -->
    <!-- MODE 1: PRE-MADE CATALOG PLANS                                        -->
    <!-- ===================================================================== -->
    <div v-if="activeMode === 'catalog'" class="space-y-4">
      <!-- Category Tabs -->
      <div v-if="categories.length > 1" class="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
        <button
          v-for="cat in categories"
          :key="cat.id"
          @click="selectedCategoryId = cat.id"
          class="px-3.5 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition"
          :class="selectedCategoryId === cat.id ? 'btn-tg shadow' : 'bg-tg-sec text-tg-hint hover:text-tg'"
        >
          {{ cat.name }}
        </button>
      </div>

      <!-- Active Plans List -->
      <div v-if="currentPlans.length" class="space-y-3">
        <div
          v-for="plan in currentPlans"
          :key="plan.id"
          class="bg-tg-sec rounded-2xl p-4 border border-gray-700/20 shadow-sm flex flex-col justify-between hover:border-tg-button/40 transition"
        >
          <div>
            <div class="flex justify-between items-start mb-2">
              <h3 class="font-bold text-sm text-tg">{{ plan.name }}</h3>
              <span class="text-xs bg-emerald-500/15 text-emerald-400 font-semibold px-2 py-0.5 rounded-full">
                {{ formatVolume(plan.volume_gb) }}
              </span>
            </div>

            <div class="grid grid-cols-2 gap-2 text-xs text-tg-hint my-3">
              <div class="flex items-center gap-1.5 bg-tg/40 p-2 rounded-lg">
                <span>⏱</span>
                <span>مدت: {{ plan.days }} روز</span>
              </div>
              <div class="flex items-center gap-1.5 bg-tg/40 p-2 rounded-lg">
                <span>👥</span>
                <span>کاربر: {{ plan.ip_limit > 0 ? `${plan.ip_limit} کاربر` : 'نامحدود' }}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-between pt-2 border-t border-gray-700/30 mt-1">
            <div>
              <span class="text-xs text-tg-hint block">قیمت</span>
              <span class="text-sm font-bold text-tg">{{ Number(plan.price).toLocaleString('fa-IR') }} تومان</span>
            </div>
            <button
              @click="openCheckoutModal(plan, false)"
              class="btn-tg text-xs font-semibold px-4 py-2 rounded-xl shadow active:scale-95 transition"
            >
              خرید و فعال‌سازی
            </button>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="text-center py-12 bg-tg-sec/50 rounded-2xl border border-dashed border-gray-700/40">
        <p class="text-sm text-tg-hint">پک یا پلانی در این دسته‌بندی یافت نشد.</p>
      </div>
    </div>

    <!-- ===================================================================== -->
    <!-- MODE 2: CUSTOM PLAN BUILDER                                            -->
    <!-- ===================================================================== -->
    <div v-else class="space-y-4">
      <!-- 1. DURATION SELECTION -->
      <div class="bg-tg-sec rounded-2xl p-4 border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <label class="text-xs font-bold text-tg flex items-center gap-1.5">
            <span>⏱</span>
            <span>۱. انتخاب مدت زمان پلن</span>
          </label>
          <span class="text-[10px] text-tg-hint">پایه هر ماه: {{ Number(builderConfig.month_price).toLocaleString('fa-IR') }} تومان</span>
        </div>

        <div class="grid grid-cols-2 gap-2">
          <button
            v-for="dur in durationOptions"
            :key="dur.months"
            type="button"
            @click="selectedMonths = dur.months"
            class="p-3 rounded-xl border text-right transition flex flex-col justify-between"
            :class="selectedMonths === dur.months ? 'bg-tg-button/15 border-tg-button text-tg shadow-sm ring-1 ring-tg-button' : 'bg-tg border-gray-700/40 text-tg-hint hover:text-tg'"
          >
            <div class="flex justify-between items-center w-full mb-1">
              <span class="font-bold text-xs" :class="selectedMonths === dur.months ? 'text-tg' : ''">{{ dur.label }}</span>
              <span v-if="dur.discountPercent > 0" class="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">
                {{ dur.discountPercent }}٪ تخفیف
              </span>
            </div>

            <div class="text-[11px] mt-1">
              <span v-if="dur.discountPercent > 0" class="line-through text-gray-500 block text-[10px]">
                {{ Number(dur.basePrice).toLocaleString('fa-IR') }} تومان
              </span>
              <span class="font-bold" :class="selectedMonths === dur.months ? 'text-emerald-400' : 'text-tg/90'">
                {{ Number(dur.finalPrice).toLocaleString('fa-IR') }} تومان
              </span>
            </div>
          </button>
        </div>
      </div>

      <!-- 2. TRAFFIC LIMIT SELECTION -->
      <div class="bg-tg-sec rounded-2xl p-4 border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <label class="text-xs font-bold text-tg flex items-center gap-1.5">
            <span>📦</span>
            <span>۲. سقف ترافیک و حجم اینترنت</span>
          </label>
          <span class="text-[10px] text-tg-hint">هر گیگابایت: {{ Number(builderConfig.gb_price).toLocaleString('fa-IR') }} تومان</span>
        </div>

        <!-- Unlimited Traffic Toggle Button -->
        <button
          type="button"
          @click="toggleUnlimitedTraffic"
          class="w-full p-3 rounded-xl border flex items-center justify-between text-xs transition"
          :class="isUnlimitedTraffic ? 'bg-amber-500/15 border-amber-500/60 text-amber-300 ring-1 ring-amber-500/50' : 'bg-tg border-gray-700/40 text-tg-hint hover:text-tg'"
        >
          <div class="flex items-center gap-2">
            <span class="text-lg">♾</span>
            <div class="text-right">
              <span class="font-bold block">ترافیک نامحدود</span>
              <span class="text-[10px] text-tg-hint">سقف مصرف منصفانه ۱,۰۰۰ گیگابایت</span>
            </div>
          </div>
          <span class="font-bold text-emerald-400">{{ Number(builderConfig.traffic_unlimited_price).toLocaleString('fa-IR') }} تومان</span>
        </button>

        <!-- Custom GB selection (if not unlimited) -->
        <div v-if="!isUnlimitedTraffic" class="space-y-3 pt-2">
          <div class="flex justify-between items-center bg-tg p-3 rounded-xl border border-gray-700/40">
            <span class="text-xs text-tg-hint">حجم انتخابی:</span>
            <div class="flex items-baseline gap-1">
              <span class="text-lg font-black text-tg">{{ selectedGb }}</span>
              <span class="text-xs text-tg-hint">گیگابایت</span>
            </div>
          </div>

          <!-- Slider -->
          <div class="px-1">
            <input
              type="range"
              min="5"
              max="500"
              step="5"
              v-model.number="selectedGb"
              class="w-full accent-tg-button cursor-pointer"
            />
            <div class="flex justify-between text-[10px] text-tg-hint mt-1">
              <span>۵ گیگ</span>
              <span class="text-emerald-400">۵۰ گیگ (۵٪)</span>
              <span class="text-emerald-400">۱۰۰ گیگ (۱۵٪)</span>
              <span class="text-emerald-400">۳۰۰ گیگ (۳۰٪)</span>
              <span>۵۰۰ گیگ</span>
            </div>
          </div>

          <!-- Quick presets -->
          <div class="flex flex-wrap gap-1.5 pt-1">
            <button
              v-for="preset in [20, 50, 100, 150, 200, 300, 500]"
              :key="preset"
              type="button"
              @click="selectedGb = preset"
              class="px-2.5 py-1 rounded-lg text-[11px] font-medium transition"
              :class="selectedGb === preset ? 'btn-tg shadow' : 'bg-tg text-tg-hint hover:text-tg'"
            >
              {{ preset }} GB
            </button>
          </div>
        </div>
      </div>

      <!-- 3. USER LIMIT SELECTION -->
      <div class="bg-tg-sec rounded-2xl p-4 border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <label class="text-xs font-bold text-tg flex items-center gap-1.5">
            <span>👥</span>
            <span>۳. تعداد کاربر همزمان (دستگاه‌ها)</span>
          </label>
        </div>

        <!-- Fair-use warning if unlimited traffic + tried unlimited user -->
        <div v-if="isUnlimitedTraffic" class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-300 leading-relaxed">
          ⚠️ <b>سیاست مصرف منصفانه:</b> به دلیل انتخاب ترافیک نامحدود، امکان انتخاب کاربر نامحدود وجود ندارد.
        </div>

        <!-- User buttons: 1, 2, 3, 4, 5, Unlimited -->
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="u in userOptions"
            :key="u.value"
            type="button"
            :disabled="u.value === 0 && isUnlimitedTraffic"
            @click="selectUserLimit(u.value)"
            class="p-2.5 rounded-xl border text-center transition flex flex-col items-center justify-between"
            :class="[
              selectedUsers === u.value
                ? 'bg-tg-button/15 border-tg-button text-tg ring-1 ring-tg-button'
                : 'bg-tg border-gray-700/40 text-tg-hint hover:text-tg',
              (u.value === 0 && isUnlimitedTraffic) ? 'opacity-40 cursor-not-allowed' : ''
            ]"
          >
            <span class="font-bold text-xs">{{ u.label }}</span>
            <span class="text-[10px] mt-1 text-emerald-400 font-medium">
              {{ u.cost === 0 ? 'رایگان' : `+${Number(u.cost).toLocaleString('fa-IR')}` }}
            </span>
          </button>
        </div>
      </div>

      <!-- 4. BRIEF SUMMARY & PRICE BREAKDOWN -->
      <div class="bg-gradient-to-br from-tg-sec to-tg border border-gray-700/40 rounded-2xl p-4 space-y-3 shadow-md">
        <h3 class="font-bold text-xs flex items-center gap-1.5 border-b border-gray-700/30 pb-2">
          <span>📋</span>
          <span>پیش‌فاکتور و خلاصه پلن سفارشی شما</span>
        </h3>

        <div class="space-y-1.5 text-xs text-tg/90">
          <div class="flex justify-between items-center">
            <span class="text-tg-hint">مدت زمان:</span>
            <div class="flex items-center gap-2">
              <span v-if="calculatedBrief.duration.discount_amount > 0" class="line-through text-[10px] text-gray-500">
                {{ Number(calculatedBrief.duration.base_price).toLocaleString('fa-IR') }}
              </span>
              <span class="font-semibold">{{ Number(calculatedBrief.duration.final_price).toLocaleString('fa-IR') }} تومان</span>
            </div>
          </div>

          <div class="flex justify-between items-center">
            <span class="text-tg-hint">ترافیک اینترنت:</span>
            <div class="flex items-center gap-2">
              <span v-if="calculatedBrief.traffic.discount_amount > 0" class="line-through text-[10px] text-gray-500">
                {{ Number(calculatedBrief.traffic.base_price).toLocaleString('fa-IR') }}
              </span>
              <span class="font-semibold">{{ Number(calculatedBrief.traffic.final_price).toLocaleString('fa-IR') }} تومان</span>
            </div>
          </div>

          <div class="flex justify-between items-center">
            <span class="text-tg-hint">کاربران مجاز:</span>
            <span class="font-semibold">
              {{ calculatedBrief.user_limit.cost === 0 ? 'رایگان' : `${Number(calculatedBrief.user_limit.cost).toLocaleString('fa-IR')} تومان` }}
            </span>
          </div>

          <div class="border-t border-gray-700/30 pt-2 flex justify-between items-baseline">
            <span class="font-bold text-xs text-tg">مبلغ کل نهایی:</span>
            <div class="flex items-baseline gap-1">
              <span class="text-xl font-black text-emerald-400">
                {{ Number(calculatedBrief.total_price).toLocaleString('fa-IR') }}
              </span>
              <span class="text-[10px] text-tg-hint">تومان</span>
            </div>
          </div>
        </div>

        <button
          @click="openCustomCheckoutModal"
          class="w-full btn-tg font-bold text-xs py-3 rounded-xl shadow active:scale-95 transition flex items-center justify-center gap-2 mt-2"
        >
          <span>تایید و پرداخت</span>
          <span>←</span>
        </button>
      </div>
    </div>

    <!-- ===================================================================== -->
    <!-- CHECKOUT MODAL (For both catalog and custom plans)                    -->
    <!-- ===================================================================== -->
    <div v-if="activePlan" class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div class="bg-tg-sec w-full max-w-md rounded-t-3xl sm:rounded-2xl p-5 border border-gray-700/40 space-y-4 animate-slide-up">
        <div class="flex justify-between items-center pb-2 border-b border-gray-700/40">
          <h3 class="font-bold text-sm">انتخاب روش پرداخت</h3>
          <button @click="closeModal" class="text-tg-hint hover:text-tg text-lg">✕</button>
        </div>

        <div class="bg-tg/50 p-3 rounded-xl border border-gray-700/30 text-xs space-y-1">
          <div class="flex justify-between">
            <span class="text-tg-hint">پلن انتخابی:</span>
            <span class="font-bold">{{ activePlan.name }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-tg-hint">مبلغ قابل پرداخت:</span>
            <span class="font-bold text-emerald-400">{{ Number(activePlan.price).toLocaleString('fa-IR') }} تومان</span>
          </div>
        </div>

        <!-- Discount Code Input -->
        <div>
          <label class="block text-xs text-tg-hint mb-1">کد تخفیف (اختیاری):</label>
          <input
            v-model="discountCode"
            type="text"
            dir="ltr"
            placeholder="DISCOUNT_CODE"
            class="w-full bg-tg border border-gray-700/50 rounded-xl px-3 py-2 text-xs text-center uppercase tracking-wider focus:outline-none focus:border-tg-button"
          />
        </div>

        <!-- Payment Method Options -->
        <div class="space-y-2 pt-1">
          <!-- Card to Card button -->
          <button
            @click="payCard"
            :disabled="submitting"
            class="w-full bg-tg hover:bg-gray-700/40 border border-gray-600/50 p-3 rounded-xl flex items-center justify-between text-xs transition"
          >
            <div class="flex items-center gap-2">
              <span class="text-base">💳</span>
              <div class="text-right">
                <span class="font-bold block">کارت‌به‌کارت (ارسال فیش در چت تلگرام)</span>
                <span class="text-[10px] text-tg-hint">پیام واریز در تلگرام ارسال شده و فیش در چت تایید می‌شود</span>
              </div>
            </div>
            <span>←</span>
          </button>

          <!-- Wallet button -->
          <button
            @click="payWallet"
            :disabled="submitting"
            class="w-full bg-tg hover:bg-gray-700/40 border border-gray-600/50 p-3 rounded-xl flex items-center justify-between text-xs transition"
          >
            <div class="flex items-center gap-2">
              <span class="text-base">👛</span>
              <div class="text-right">
                <span class="font-bold block">پرداخت با موجودی کیف پول</span>
                <span class="text-[10px] text-tg-hint">موجودی فعلی: {{ Number(auth.balance).toLocaleString('fa-IR') }} تومان</span>
              </div>
            </div>
            <span>←</span>
          </button>

          <!-- Zibal Online Gateway -->
          <button
            v-if="activeGateways.zibal"
            @click="payGateway('zibal')"
            :disabled="submitting"
            class="w-full bg-tg hover:bg-gray-700/40 border border-emerald-600/50 p-3 rounded-xl flex items-center justify-between text-xs transition"
          >
            <div class="flex items-center gap-2">
              <span class="text-base">⚡️</span>
              <div class="text-right">
                <span class="font-bold text-emerald-400 block">درگاه پرداخت آنلاین زیبال (شاپرک)</span>
                <span class="text-[10px] text-tg-hint">پرداخت شتابی و فعال‌سازی آنی بدون نیاز به تایید دستی</span>
              </div>
            </div>
            <span>←</span>
          </button>

          <!-- Zarinpal Online Gateway -->
          <button
            v-if="activeGateways.zarinpal"
            @click="payGateway('zarinpal')"
            :disabled="submitting"
            class="w-full bg-tg hover:bg-gray-700/40 border border-amber-500/50 p-3 rounded-xl flex items-center justify-between text-xs transition"
          >
            <div class="flex items-center gap-2">
              <span class="text-base">🟡</span>
              <div class="text-right">
                <span class="font-bold text-amber-300 block">درگاه پرداخت زرین‌پال (شاپرک)</span>
                <span class="text-[10px] text-tg-hint">پرداخت شتابی با تمام کارت‌های عضو شتاب</span>
              </div>
            </div>
            <span>←</span>
          </button>

          <!-- Telegram Stars Payment -->
          <button
            v-if="activeGateways.stars"
            @click="payStars"
            :disabled="submitting"
            class="w-full bg-tg hover:bg-gray-700/40 border border-yellow-500/50 p-3 rounded-xl flex items-center justify-between text-xs transition"
          >
            <div class="flex items-center gap-2">
              <span class="text-base">⭐</span>
              <div class="text-right">
                <span class="font-bold text-yellow-300 block">پرداخت با تلگرام استارز (Telegram Stars)</span>
                <span class="text-[10px] text-tg-hint">
                  پرداخت مستقیم درون تلگرام (تقریباً {{ Math.max(1, Math.ceil(modalPrice / (activeGateways.stars_rate || 1500))).toLocaleString('fa-IR') }} استارز)
                </span>
              </div>
            </div>
            <span>←</span>
          </button>
        </div>

        <!-- Status / Alert message -->
        <div v-if="message" class="p-3 rounded-xl text-xs" :class="isSuccess ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'">
          {{ message }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getPlans,
  getBuilderConfig,
  initCardOrder,
  initWalletOrder,
  initCustomCardOrder,
  initCustomWalletOrder,
  getActiveGateways,
  initGatewayOrder,
  initStarsOrder
} from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

// State
const activeMode = ref('catalog') // 'catalog' | 'builder'
const categories = ref([])
const selectedCategoryId = ref(null)
const activeGateways = ref({ card: true, wallet: true, zibal: false, zarinpal: false, stars: false, stars_rate: 1500 })

// Builder state
const selectedMonths = ref(1) // 1, 3, 6, 12
const isUnlimitedTraffic = ref(false)
const selectedGb = ref(50) // 5 .. 500
const selectedUsers = ref(1) // 1, 2, 3, 4, 5, 0 (unlimited)

const builderConfig = ref({
  month_price: 120000,
  dur_discounts: { 1: 0, 3: 5, 6: 10, 12: 20 },
  gb_price: 1000,
  traffic_discounts: [
    { min_gb: 300, percent: 30 },
    { min_gb: 100, percent: 15 },
    { min_gb: 50, percent: 5 }
  ],
  traffic_unlimited_price: 500000,
  traffic_unlimited_cap_gb: 1000,
  user_costs: { 1: 0, 2: 20000, 3: 35000, 4: 45000, 5: 50000, 0: 65000 }
})

// Checkout Modal state
const activePlan = ref(null)
const isCustomPlan = ref(false)
const discountCode = ref('')
const submitting = ref(false)
const message = ref('')
const isSuccess = ref(false)

// ---------------------------------------------------------------------------
// Computed: Catalog
// ---------------------------------------------------------------------------
const currentPlans = computed(() => {
  if (!categories.value.length) return []
  const cat = categories.value.find(c => c.id === selectedCategoryId.value)
  return cat ? cat.plans : categories.value[0]?.plans || []
})

const formatVolume = (vol) => {
  if (!vol || vol <= 0) return 'حجم نامحدود'
  return `${vol} گیگابایت`
}

// ---------------------------------------------------------------------------
// Computed: Builder
// ---------------------------------------------------------------------------
const durationOptions = computed(() => {
  const mPrice = builderConfig.value.month_price
  const discounts = builderConfig.value.dur_discounts
  return [1, 3, 6, 12].map(m => {
    const base = m * mPrice
    const pct = discounts[m] || 0
    const final = base - Math.round((base * pct) / 100)
    return {
      months: m,
      label: `${m} ماهه`,
      basePrice: base,
      discountPercent: pct,
      finalPrice: final
    }
  })
})

const userOptions = computed(() => {
  const costs = builderConfig.value.user_costs
  return [
    { value: 1, label: '۱ کاربر', cost: costs[1] ?? 0 },
    { value: 2, label: '۲ کاربر', cost: costs[2] ?? 20000 },
    { value: 3, label: '۳ کاربر', cost: costs[3] ?? 35000 },
    { value: 4, label: '۴ کاربر', cost: costs[4] ?? 45000 },
    { value: 5, label: '۵ کاربر', cost: costs[5] ?? 50000 },
    { value: 0, label: 'نامحدود', cost: costs[0] ?? 65000 }
  ]
})

const calculatedBrief = computed(() => {
  const m = selectedMonths.value
  const mPrice = builderConfig.value.month_price
  const durBase = m * mPrice
  const durPct = builderConfig.value.dur_discounts[m] || 0
  const durDiscAmt = Math.round((durBase * durPct) / 100)
  const durFinal = durBase - durDiscAmt

  // Traffic
  let trafBase = 0
  let trafPct = 0
  let trafDiscAmt = 0
  let trafFinal = 0
  if (isUnlimitedTraffic.value) {
    trafBase = builderConfig.value.traffic_unlimited_price
    trafFinal = trafBase
  } else {
    trafBase = selectedGb.value * builderConfig.value.gb_price
    for (const td of builderConfig.value.traffic_discounts) {
      if (selectedGb.value > td.min_gb) {
        trafPct = td.percent
        break
      }
    }
    trafDiscAmt = Math.round((trafBase * trafPct) / 100)
    trafFinal = trafBase - trafDiscAmt
  }

  // Users
  const uCost = builderConfig.value.user_costs[selectedUsers.value] ?? 0

  const total = durFinal + trafFinal + uCost

  return {
    duration: {
      months: m,
      base_price: durBase,
      discount_amount: durDiscAmt,
      final_price: durFinal
    },
    traffic: {
      is_unlimited: isUnlimitedTraffic.value,
      volume_gb: isUnlimitedTraffic.value ? 0 : selectedGb.value,
      base_price: trafBase,
      discount_amount: trafDiscAmt,
      final_price: trafFinal
    },
    user_limit: {
      ip_limit: selectedUsers.value,
      cost: uCost
    },
    total_price: total
  }
})

// Actions
const toggleUnlimitedTraffic = () => {
  isUnlimitedTraffic.value = !isUnlimitedTraffic.value
  if (isUnlimitedTraffic.value && selectedUsers.value === 0) {
    // Fair use: cannot have unlimited users with unlimited traffic
    selectedUsers.value = 1
  }
}

const selectUserLimit = (val) => {
  if (val === 0 && isUnlimitedTraffic.value) {
    return // Forbidden by fair use
  }
  selectedUsers.value = val
}

const openCheckoutModal = (plan, isCustom = false) => {
  activePlan.value = plan
  isCustomPlan.value = isCustom
  message.value = ''
  discountCode.value = ''
}

const openCustomCheckoutModal = () => {
  const brief = calculatedBrief.value
  const trafLabel = brief.traffic.is_unlimited ? 'نامحدود' : `${brief.traffic.volume_gb} گیگ`
  const userLabel = brief.user_limit.ip_limit === 0 ? 'نامحدود' : `${brief.user_limit.ip_limit} کاربر`
  const planName = `پلن اختصاصی | ${brief.duration.months} ماهه - ${trafLabel} - ${userLabel}`

  openCheckoutModal({
    id: 0,
    name: planName,
    price: brief.total_price,
    days: brief.duration.months * 30,
    volume_gb: brief.traffic.volume_gb,
    ip_limit: brief.user_limit.ip_limit
  }, true)
}

const closeModal = () => {
  activePlan.value = null
  submitting.value = false
}

const payCard = async () => {
  submitting.value = true
  message.value = ''
  try {
    if (isCustomPlan.value) {
      await initCustomCardOrder(
        selectedMonths.value,
        isUnlimitedTraffic.value ? 0 : selectedGb.value,
        selectedUsers.value,
        discountCode.value || null
      )
    } else {
      await initCardOrder(activePlan.value.id, discountCode.value || null)
    }
    isSuccess.value = true
    message.value = '✅ پیام پرداخت و شماره کارت در چت تلگرام شما ارسال شد. لطفاً تصویر فیش را در چت ارسال فرمایید.'
    setTimeout(() => {
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.close()
      }
    }, 2500)
  } catch (err) {
    isSuccess.value = false
    message.value = err.response?.data?.detail || 'خطا در ثبت درخواست کارت‌به‌کارت'
  } finally {
    submitting.value = false
  }
}

const payWallet = async () => {
  submitting.value = true
  message.value = ''
  try {
    if (isCustomPlan.value) {
      await initCustomWalletOrder(
        selectedMonths.value,
        isUnlimitedTraffic.value ? 0 : selectedGb.value,
        selectedUsers.value,
        discountCode.value || null
      )
    } else {
      await initWalletOrder(activePlan.value.id, discountCode.value || null)
    }
    isSuccess.value = true
    message.value = '🎉 پرداخت با کیف پول موفق بود و سرویس شما ثبت شد.'
    await auth.fetchMe()
    setTimeout(() => {
      closeModal()
    }, 2000)
  } catch (err) {
    isSuccess.value = false
    message.value = err.response?.data?.detail || 'موجودی ناکافی یا خطای دیگر'
  } finally {
    submitting.value = false
  }
}

const payGateway = async (gatewayName) => {
  submitting.value = true
  message.value = 'در حال ارتباط با درگاه بانکی...'
  isSuccess.value = true
  try {
    let payload
    if (isCustomPlan.value) {
      payload = {
        gateway: gatewayName,
        months: selectedMonths.value,
        volume_gb: isUnlimitedTraffic.value ? 0 : selectedGb.value,
        ip_limit: selectedUsers.value,
        discount_code: discountCode.value || null
      }
    } else {
      payload = {
        gateway: gatewayName,
        plan_id: activePlan.value.id,
        discount_code: discountCode.value || null
      }
    }
    const res = await initGatewayOrder(payload)
    if (res.data?.payment_url) {
      message.value = 'در حال انتقال به صفحه پرداخت بانکی...'
      if (window.Telegram?.WebApp?.openLink) {
        window.Telegram.WebApp.openLink(res.data.payment_url)
      } else {
        window.location.href = res.data.payment_url
      }
    } else {
      throw new Error('لینک پرداخت دریافت نشد.')
    }
  } catch (err) {
    isSuccess.value = false
    message.value = err.response?.data?.detail || 'خطا در اتصال به درگاه بانکی'
    submitting.value = false
  }
}

const payStars = async () => {
  submitting.value = true
  message.value = 'در حال ایجاد فاکتور تلگرام استارز...'
  isSuccess.value = true
  try {
    let payload
    if (isCustomPlan.value) {
      payload = {
        custom_spec: {
          months: selectedMonths.value,
          volume_gb: isUnlimitedTraffic.value ? 0 : selectedGb.value,
          ip_limit: selectedUsers.value,
        },
        discount_code: discountCode.value || null
      }
    } else {
      payload = {
        plan_id: activePlan.value.id,
        discount_code: discountCode.value || null
      }
    }
    const res = await initStarsOrder(payload)
    if (res.data?.invoice_link) {
      if (window.Telegram?.WebApp?.openInvoice) {
        window.Telegram.WebApp.openInvoice(res.data.invoice_link, (status) => {
          if (status === 'paid') {
            isSuccess.value = true
            message.value = 'پرداخت استارز با موفقیت انجام شد! سرویس شما فعال گردید.'
            setTimeout(() => {
              activePlan.value = null
              router.push('/services')
            }, 1500)
          } else if (status === 'cancelled') {
            message.value = 'پرداخت استارز لغو شد.'
            submitting.value = false
          } else if (status === 'failed') {
            isSuccess.value = false
            message.value = 'پرداخت استارز با خطا مواجه شد.'
            submitting.value = false
          }
        })
      } else {
        window.open(res.data.invoice_link, '_blank')
        message.value = 'فاکتور استارز باز شد. پس از پرداخت، سرویس فعال خواهد شد.'
      }
    } else {
      throw new Error('لینک فاکتور دریافت نشد.')
    }
  } catch (err) {
    isSuccess.value = false
    message.value = err.response?.data?.detail || 'خطا در ایجاد فاکتور استارز'
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const [pRes, bRes, gRes] = await Promise.all([
      getPlans(),
      getBuilderConfig().catch(() => null),
      getActiveGateways().catch(() => null)
    ])
    categories.value = pRes.data.categories || []
    if (categories.value.length) {
      selectedCategoryId.value = categories.value[0].id
    }
    if (bRes && bRes.data) {
      builderConfig.value = { ...builderConfig.value, ...bRes.data }
    }
    if (gRes && gRes.data) {
      activeGateways.value = { ...activeGateways.value, ...gRes.data }
    }
  } catch (err) {
    console.error('Failed to load store data:', err)
  }
})
</script>
