<template>
  <div class="space-y-4">
    <!-- Header with Back -->
    <div class="flex items-center justify-between pb-2 border-b border-gray-700/30">
      <div class="flex items-center gap-2">
        <router-link to="/" class="text-tg-hint hover:text-tg text-sm font-bold">
          ← بازگشت
        </router-link>
        <h2 class="text-sm font-bold">⚙️ پنل مدیریت SpeedyBot</h2>
      </div>
      <button @click="loadData" class="text-xs text-tg-button hover:underline">
        🔄 بروزرسانی
      </button>
    </div>

    <!-- Quick Stats -->
    <div class="grid grid-cols-2 gap-2 text-xs">
      <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
        <span class="text-tg-hint text-[10px] block">کل کاربران</span>
        <span class="text-base font-bold text-tg mt-0.5 block">{{ Number(stats.total_users).toLocaleString('fa-IR') }}</span>
      </div>
      <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
        <span class="text-tg-hint text-[10px] block">سفارش‌های در انتظار</span>
        <span class="text-base font-bold text-amber-400 mt-0.5 block">{{ Number(stats.pending_orders).toLocaleString('fa-IR') }}</span>
      </div>
      <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
        <span class="text-tg-hint text-[10px] block">سفارش‌های موفق</span>
        <span class="text-base font-bold text-emerald-400 mt-0.5 block">{{ Number(stats.total_orders).toLocaleString('fa-IR') }}</span>
      </div>
      <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
        <span class="text-tg-hint text-[10px] block">کاربران جدید امروز</span>
        <span class="text-base font-bold text-blue-400 mt-0.5 block">{{ Number(stats.new_users_today).toLocaleString('fa-IR') }}</span>
      </div>
    </div>

    <!-- Admin Tabs -->
    <div class="flex gap-2 border-b border-gray-700/30 pb-1">
      <button
        @click="activeTab = 'orders'"
        class="text-xs font-semibold py-1 px-3 rounded-xl transition"
        :class="activeTab === 'orders' ? 'btn-tg' : 'text-tg-hint hover:text-tg'"
      >
        سفارش‌ها ({{ orders.length }})
      </button>
      <button
        @click="activeTab = 'broadcast'"
        class="text-xs font-semibold py-1 px-3 rounded-xl transition"
        :class="activeTab === 'broadcast' ? 'btn-tg' : 'text-tg-hint hover:text-tg'"
      >
        ارسال پیام همگانی
      </button>
      <button
        @click="activeTab = 'users'"
        class="text-xs font-semibold py-1 px-3 rounded-xl transition"
        :class="activeTab === 'users' ? 'btn-tg' : 'text-tg-hint hover:text-tg'"
      >
        کاربران
      </button>
      <button
        @click="activeTab = 'gateways'"
        class="text-xs font-semibold py-1 px-3 rounded-xl transition"
        :class="activeTab === 'gateways' ? 'btn-tg' : 'text-tg-hint hover:text-tg'"
      >
        درگاه‌های پرداخت
      </button>
      <button
        @click="activeTab = 'branding'"
        class="text-xs font-semibold py-1 px-3 rounded-xl transition"
        :class="activeTab === 'branding' ? 'btn-tg' : 'text-tg-hint hover:text-tg'"
      >
        عنوان و ظاهر
      </button>
    </div>

    <!-- Tab 1: Orders -->
    <div v-if="activeTab === 'orders'" class="space-y-3">
      <div v-if="orders.length" class="space-y-2">
        <div
          v-for="order in orders"
          :key="order.id"
          class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30 text-xs space-y-2"
        >
          <div class="flex justify-between items-start">
            <div>
              <span class="font-bold block">{{ order.plan || 'سفارش' }}</span>
              <span class="text-[10px] text-tg-hint">کاربر: <code>{{ order.user_id }}</code> | شناسه: #{{ order.id }}</span>
            </div>
            <span class="text-emerald-400 font-bold">{{ Number(order.price).toLocaleString('fa-IR') }} تومان</span>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <button
              @click="handleApprove(order.id)"
              :disabled="actionLoading === order.id"
              class="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-1.5 rounded-xl transition"
            >
              تایید و ساخت سرویس ✓
            </button>
            <button
              @click="handleReject(order.id)"
              :disabled="actionLoading === order.id"
              class="px-3 bg-rose-600/30 hover:bg-rose-600/50 text-rose-300 font-semibold py-1.5 rounded-xl transition"
            >
              رد ✕
            </button>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-8 bg-tg-sec/40 rounded-xl border border-dashed border-gray-700/30 text-xs text-tg-hint">
        سفارش در انتظاری وجود ندارد.
      </div>
    </div>

    <!-- Tab 2: Broadcast -->
    <div v-if="activeTab === 'broadcast'" class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
      <label class="block text-xs font-semibold">ارسال پیام به تلگرام کاربران:</label>

      <div>
        <label class="block text-[10px] text-tg-hint mb-1">مخاطبین:</label>
        <select v-model="broadcastAudience" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs">
          <option value="all">همه کاربران فعال</option>
          <option value="customers">خریداران (مشتریان)</option>
          <option value="trial">کاربران تست رایگان</option>
          <option value="never_bought">کاربرانی که خریدی نداشته‌اند</option>
        </select>
      </div>

      <div>
        <label class="block text-[10px] text-tg-hint mb-1">متن پیام (HTML مجاز است):</label>
        <textarea
          v-model="broadcastText"
          rows="4"
          placeholder="متن پیام را وارد کنید..."
          class="w-full bg-tg border border-gray-700/40 rounded-xl p-3 text-xs focus:outline-none focus:border-tg-button"
        ></textarea>
      </div>

      <button
        @click="handleBroadcast"
        :disabled="sendingBroadcast || !broadcastText.trim()"
        class="w-full btn-tg font-bold py-2 rounded-xl text-xs transition"
      >
        {{ sendingBroadcast ? 'در حال ارسال...' : 'ارسال همگانی 🚀' }}
      </button>

      <p v-if="broadcastMsg" class="text-xs text-emerald-400 mt-1">{{ broadcastMsg }}</p>
    </div>

    <!-- Tab 3: Users -->
    <div v-if="activeTab === 'users'" class="space-y-2">
      <div v-for="u in usersList" :key="u.id" class="bg-tg-sec p-2.5 rounded-xl border border-gray-700/20 text-xs flex justify-between items-center">
        <div>
          <span class="font-mono font-bold">{{ u.id }}</span>
          <span class="text-[10px] text-tg-hint block">موجودی: {{ Number(u.balance).toLocaleString('fa-IR') }} تومان</span>
        </div>
        <span class="text-[10px] px-2 py-0.5 rounded-full" :class="u.is_active ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'">
          {{ u.is_active ? 'فعال' : 'مسدود' }}
        </span>
      </div>
    </div>

    <!-- Tab 4: Gateways Configuration -->
    <div v-if="activeTab === 'gateways'" class="space-y-4">
      <!-- Zibal Box -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-2">
            <span class="text-xl">💳</span>
            <div>
              <h3 class="font-bold text-xs text-tg">درگاه زیبال (Zibal)</h3>
              <span class="text-[10px] text-tg-hint">وب‌سرویس پرداخت آنلاین ریالی و شتابی</span>
            </div>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="gatewaysConfig.zibal.enabled" class="sr-only peer" />
            <div class="w-9 h-5 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
          </label>
        </div>

        <div v-if="gatewaysConfig.zibal.enabled" class="space-y-2 pt-2 border-t border-gray-700/30 text-xs">
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">کد مرچنت زیبال (Merchant Key):</label>
            <input
              type="text"
              v-model="gatewaysConfig.zibal.merchant"
              placeholder="مثلاً: zibal یا کلید دریافتی از پنل زیبال"
              dir="ltr"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs focus:outline-none focus:border-tg-button"
            />
            <span class="text-[10px] text-tg-hint block mt-0.5">برای حالت تستی زیبال، مقدار <code>zibal</code> را وارد کنید.</span>
          </div>

          <div class="flex items-center justify-between pt-1">
            <span class="text-tg-hint text-xs">محیط آزمایشی (Sandbox):</span>
            <input type="checkbox" v-model="gatewaysConfig.zibal.sandbox" class="rounded accent-tg-button" />
          </div>
        </div>
      </div>

      <!-- Zarinpal Box -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-2">
            <span class="text-xl">🟡</span>
            <div>
              <h3 class="font-bold text-xs text-tg">درگاه زرین‌پال (Zarinpal)</h3>
              <span class="text-[10px] text-tg-hint">درگاه پرداخت اینترنتی شاپرک</span>
            </div>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="gatewaysConfig.zarinpal.enabled" class="sr-only peer" />
            <div class="w-9 h-5 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
          </label>
        </div>

        <div v-if="gatewaysConfig.zarinpal.enabled" class="space-y-2 pt-2 border-t border-gray-700/30 text-xs">
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">مرچنت کد ۳۶ رقمی زرین‌پال:</label>
            <input
              type="text"
              v-model="gatewaysConfig.zarinpal.merchant"
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              dir="ltr"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs focus:outline-none focus:border-tg-button"
            />
          </div>

          <div class="flex items-center justify-between pt-1">
            <span class="text-tg-hint text-xs">محیط آزمایشی زرین‌پال (Sandbox):</span>
            <input type="checkbox" v-model="gatewaysConfig.zarinpal.sandbox" class="rounded accent-tg-button" />
          </div>
        </div>
      </div>

      <button
        @click="handleSaveGateways"
        :disabled="savingGateways"
        class="w-full btn-tg font-bold py-2.5 rounded-xl text-xs transition active:scale-95 shadow"
      >
        {{ savingGateways ? 'در حال ذخیره‌سازی...' : 'ذخیره تنظیمات درگاه‌ها 💾' }}
      </button>

      <p v-if="gatewaySavedMsg" class="text-xs text-emerald-400 text-center">{{ gatewaySavedMsg }}</p>
    </div>

    <!-- Tab 5: Branding / UI Title -->
    <div v-if="activeTab === 'branding'" class="space-y-3">
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 text-xs space-y-3">
        <div class="flex items-center gap-2">
          <span class="text-lg">🎨</span>
          <div>
            <span class="font-bold block">تنظیم نام و عنوان وب‌اپلیکیشن</span>
            <span class="text-[10px] text-tg-hint">تغییر عنوان در تب مرورگر و بالای صفحه مینی‌اپ</span>
          </div>
        </div>

        <div class="space-y-1">
          <label class="block text-xs font-medium text-tg">عنوان و نام وب‌اپ (Web UI Title):</label>
          <input
            type="text"
            v-model="uiTitle"
            placeholder="مثال: فروشگاه اسپیدی یا SpeedyBot"
            class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-tg-button font-medium"
          />
          <p class="text-[10px] text-tg-hint pt-1">
            این عنوان بلافاصله در عنوان تب مرورگر (Browser Tab) و در هدر بالای مینی‌اپ برای تمام کاربران نمایش داده می‌شود.
          </p>
        </div>

        <button
          @click="handleSaveBranding"
          :disabled="savingBranding || !uiTitle.trim()"
          class="w-full btn-tg font-bold py-2.5 rounded-xl text-xs transition active:scale-95 shadow"
        >
          {{ savingBranding ? 'در حال ذخیره‌سازی...' : 'ذخیره عنوان وب‌اپ 💾' }}
        </button>

        <p v-if="brandingSavedMsg" class="text-xs text-emerald-400 text-center">{{ brandingSavedMsg }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import {
  getAdminStats,
  getAdminOrders,
  approveOrder,
  rejectOrder,
  getAdminUsers,
  sendBroadcast,
  getAdminGateways,
  saveAdminGateways,
  getAdminBranding,
  saveAdminBranding
} from '@/api'

const auth = useAuthStore()

const stats = ref({
  total_users: 0,
  total_orders: 0,
  total_revenue: 0,
  pending_orders: 0,
  new_users_today: 0
})
const orders = ref([])
const usersList = ref([])
const activeTab = ref('orders')
const actionLoading = ref(null)

const broadcastAudience = ref('all')
const broadcastText = ref('')
const sendingBroadcast = ref(false)
const broadcastMsg = ref('')

const loadData = async () => {
  try {
    const [sRes, oRes] = await Promise.all([
      getAdminStats(),
      getAdminOrders('PENDING')
    ])
    stats.value = sRes.data
    orders.value = oRes.data.orders || []
  } catch (err) {
    console.error('Failed to load admin stats:', err)
  }
}

const handleApprove = async (orderId) => {
  actionLoading.value = orderId
  try {
    await approveOrder(orderId)
    await loadData()
  } catch (err) {
    alert(err.response?.data?.detail || 'خطا در تایید سفارش')
  } finally {
    actionLoading.value = null
  }
}

const handleReject = async (orderId) => {
  const reason = prompt('دلیل رد سفارش (اختیاری):')
  actionLoading.value = orderId
  try {
    await rejectOrder(orderId, reason)
    await loadData()
  } catch (err) {
    alert(err.response?.data?.detail || 'خطا در رد سفارش')
  } finally {
    actionLoading.value = null
  }
}

const handleBroadcast = async () => {
  if (!confirm('آیا از ارسال این پیام به تمام کاربران انتخاب‌شده مطمئن هستید؟')) return
  sendingBroadcast.value = true
  broadcastMsg.value = ''
  try {
    const res = await sendBroadcast(broadcastText.value, broadcastAudience.value)
    broadcastMsg.value = `پیام در صف ارسال قرار گرفت (${res.data.total} مخاطب).`
    broadcastText.value = ''
  } catch (err) {
    alert('خطا در ارسال پیام همگانی')
  } finally {
    sendingBroadcast.value = false
  }
}

const gatewaysConfig = ref({
  zibal: { enabled: false, merchant: '', sandbox: false },
  zarinpal: { enabled: false, merchant: '', sandbox: false }
})
const savingGateways = ref(false)
const gatewaySavedMsg = ref('')

const handleSaveGateways = async () => {
  savingGateways.value = true
  gatewaySavedMsg.value = ''
  try {
    const payload = {
      zibal_enabled: gatewaysConfig.value.zibal.enabled,
      zibal_merchant: gatewaysConfig.value.zibal.merchant || '',
      zibal_sandbox: gatewaysConfig.value.zibal.sandbox || false,
      zarinpal_enabled: gatewaysConfig.value.zarinpal.enabled,
      zarinpal_merchant: gatewaysConfig.value.zarinpal.merchant || '',
      zarinpal_sandbox: gatewaysConfig.value.zarinpal.sandbox || false
    }
    const res = await saveAdminGateways(payload)
    gatewaySavedMsg.value = res.data.message || 'تنظیمات با موفقیت ذخیره شد.'
    setTimeout(() => {
      gatewaySavedMsg.value = ''
    }, 3000)
  } catch (err) {
    alert(err.response?.data?.detail || 'خطا در ذخیره تنظیمات درگاه‌ها')
  } finally {
    savingGateways.value = false
  }
}

const uiTitle = ref('')
const savingBranding = ref(false)
const brandingSavedMsg = ref('')

const handleSaveBranding = async () => {
  if (!uiTitle.value.trim()) return
  savingBranding.value = true
  brandingSavedMsg.value = ''
  try {
    const res = await saveAdminBranding({ webapp_title: uiTitle.value.trim() })
    brandingSavedMsg.value = res.data.message || 'عنوان با موفقیت بروزرسانی شد.'
    auth.setAppTitle(uiTitle.value.trim())
    setTimeout(() => {
      brandingSavedMsg.value = ''
    }, 3000)
  } catch (err) {
    alert(err.response?.data?.detail || 'خطا در ذخیره عنوان وب‌اپ')
  } finally {
    savingBranding.value = false
  }
}

onMounted(async () => {
  await loadData()
  try {
    const [uRes, gRes, bRes] = await Promise.all([
      getAdminUsers(50, 0),
      getAdminGateways().catch(() => null),
      getAdminBranding().catch(() => null)
    ])
    usersList.value = uRes.data.users || []
    if (gRes && gRes.data) {
      gatewaysConfig.value = {
        zibal: { ...gatewaysConfig.value.zibal, ...gRes.data.zibal },
        zarinpal: { ...gatewaysConfig.value.zarinpal, ...gRes.data.zarinpal }
      }
    }
    if (bRes && bRes.data && bRes.data.webapp_title) {
      uiTitle.value = bRes.data.webapp_title
    } else {
      uiTitle.value = auth.appTitle || 'SpeedyBot'
    }
  } catch (err) {
    console.error(err)
  }
})
</script>
