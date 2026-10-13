<template>
  <div class="space-y-4">
    <!-- Header with Back -->
    <div class="flex items-center justify-between pb-2 border-b border-gray-700/30">
      <div class="flex items-center gap-2">
        <router-link to="/" class="text-tg-hint hover:text-tg text-sm font-bold">
          ← بازگشت
        </router-link>
        <h2 class="text-sm font-bold">⚙️ پنل مدیریت ارشد SpeedyBot</h2>
      </div>
      <button @click="loadData" class="text-xs text-tg-button hover:underline flex items-center gap-1">
        🔄 <span>بروزرسانی</span>
      </button>
    </div>

    <!-- Quick Stats Grid -->
    <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
      <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
        <span class="text-tg-hint text-[10px] block">کل کاربران</span>
        <span class="text-base font-bold text-tg mt-0.5 block">{{ Number(stats.total_users || 0).toLocaleString('fa-IR') }}</span>
      </div>
      <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
        <span class="text-tg-hint text-[10px] block">سفارش‌های در انتظار</span>
        <span class="text-base font-bold text-amber-400 mt-0.5 block">{{ Number(stats.pending_orders || 0).toLocaleString('fa-IR') }}</span>
      </div>
      <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
        <span class="text-tg-hint text-[10px] block">سفارش‌های موفق</span>
        <span class="text-base font-bold text-emerald-400 mt-0.5 block">{{ Number(stats.total_orders || 0).toLocaleString('fa-IR') }}</span>
      </div>
      <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
        <span class="text-tg-hint text-[10px] block">درآمد کل (تومان)</span>
        <span class="text-base font-bold text-emerald-300 mt-0.5 block">{{ Number(stats.total_revenue || 0).toLocaleString('fa-IR') }}</span>
      </div>
      <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
        <span class="text-tg-hint text-[10px] block">کاربران جدید امروز</span>
        <span class="text-base font-bold text-blue-400 mt-0.5 block">{{ Number(stats.new_users_today || 0).toLocaleString('fa-IR') }}</span>
      </div>
      <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
        <span class="text-tg-hint text-[10px] block">وضعیت سرویس سنائی</span>
        <span class="text-xs font-bold mt-1 block flex items-center gap-1" :class="serverStatus?.xui?.connected ? 'text-emerald-400' : 'text-rose-400'">
          <span class="w-2 h-2 rounded-full inline-block" :class="serverStatus?.xui?.connected ? 'bg-emerald-400' : 'bg-rose-400'"></span>
          {{ serverStatus?.xui?.connected ? (serverStatus.xui.latency_ms + ' ms') : 'قطع اتصال' }}
        </span>
      </div>
    </div>

    <!-- Admin Navigation Category Pills (Horizontal Scrollable) -->
    <div class="flex gap-1.5 overflow-x-auto pb-2 border-b border-gray-700/30 no-scrollbar text-xs whitespace-nowrap">
      <button
        v-for="t in tabs"
        :key="t.id"
        @click="activeTab = t.id"
        class="py-1.5 px-3 rounded-xl font-medium transition flex items-center gap-1"
        :class="activeTab === t.id ? 'btn-tg shadow text-white font-bold' : 'bg-tg-sec text-tg-hint hover:text-tg'"
      >
        <span>{{ t.icon }}</span>
        <span>{{ t.label }}</span>
        <span v-if="t.badge" class="bg-amber-500 text-black text-[10px] px-1.5 rounded-full font-bold">{{ t.badge }}</span>
      </button>
    </div>

    <!-- Feedback Message Banner -->
    <div v-if="globalMsg" class="p-3 rounded-xl text-xs flex justify-between items-center" :class="globalSuccess ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'">
      <span>{{ globalMsg }}</span>
      <button @click="globalMsg = ''" class="text-xs opacity-70 hover:opacity-100">✕</button>
    </div>

    <!-- ==================== Tab 1: Orders (سفارش‌ها) ==================== -->
    <div v-if="activeTab === 'orders'" class="space-y-3">
      <div class="flex justify-between items-center">
        <h3 class="text-xs font-bold text-tg">سفارش‌های در انتظار بررسی فیش</h3>
        <span class="text-[10px] text-tg-hint">تعداد: {{ orders.length }}</span>
      </div>

      <div v-if="orders.length" class="space-y-2">
        <div
          v-for="order in orders"
          :key="order.id"
          class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30 text-xs space-y-2"
        >
          <div class="flex justify-between items-start">
            <div>
              <span class="font-bold block text-sm">{{ order.plan || 'سفارش سرویس' }}</span>
              <span class="text-[10px] text-tg-hint">کاربر: <code>{{ order.user_id }}</code> | سفارش #{{ order.id }}</span>
            </div>
            <span class="text-emerald-400 font-bold text-sm">{{ Number(order.price).toLocaleString('fa-IR') }} تومان</span>
          </div>

          <div v-if="order.photo_id" class="text-[10px] text-blue-400 bg-blue-500/10 p-2 rounded-xl">
            📷 فیش واریز در چت تلگرام ربات برای سفارش #{{ order.id }} ارسال شده است.
          </div>

          <div class="flex items-center gap-2 pt-1">
            <button
              @click="handleApprove(order.id)"
              :disabled="actionLoading === order.id"
              class="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 rounded-xl transition shadow"
            >
              {{ actionLoading === order.id ? 'در حال تایید...' : 'تایید فیش و ساخت خودکار سرویس ✓' }}
            </button>
            <button
              @click="handleReject(order.id)"
              :disabled="actionLoading === order.id"
              class="px-3 bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 font-semibold py-2 rounded-xl transition"
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

    <!-- ==================== Tab 2: Plans Management (مدیریت پلان‌ها) ==================== -->
    <div v-if="activeTab === 'plans'" class="space-y-3">
      <div class="flex justify-between items-center">
        <h3 class="text-xs font-bold text-tg">پلان‌های آماده فروشگاه</h3>
        <button @click="openCreatePlanModal" class="btn-tg py-1.5 px-3 rounded-xl text-xs font-bold flex items-center gap-1 shadow">
          <span>➕</span>
          <span>افزودن پلان جدید</span>
        </button>
      </div>

      <div class="space-y-2">
        <div
          v-for="p in plansList"
          :key="p.id"
          class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30 text-xs flex justify-between items-center"
        >
          <div class="space-y-0.5">
            <div class="flex items-center gap-2">
              <span class="font-bold text-sm">{{ p.name }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded-full" :class="p.active ? 'bg-emerald-500/15 text-emerald-400' : 'bg-gray-700 text-tg-hint'">
                {{ p.active ? 'فعال' : 'غیرفعال' }}
              </span>
            </div>
            <div class="text-[10px] text-tg-hint flex gap-3">
              <span>مدت: {{ p.days }} روز</span>
              <span>حجم: {{ p.volume_gb > 0 ? p.volume_gb + ' GB' : 'نامحدود' }}</span>
              <span>کاربر: {{ p.ip_limit > 0 ? p.ip_limit + ' کاربره' : 'نامحدود' }}</span>
            </div>
            <div class="text-emerald-400 font-bold text-xs pt-0.5">
              {{ Number(p.price).toLocaleString('fa-IR') }} تومان
            </div>
          </div>

          <div class="flex items-center gap-1.5">
            <button
              @click="handleTogglePlan(p.id)"
              class="p-2 rounded-xl text-xs transition"
              :class="p.active ? 'bg-amber-500/20 text-amber-300' : 'bg-emerald-500/20 text-emerald-300'"
              :title="p.active ? 'غیرفعال‌سازی' : 'فعال‌سازی'"
            >
              {{ p.active ? 'خاموش' : 'روشن' }}
            </button>
            <button
              @click="openEditPlanModal(p)"
              class="p-2 bg-blue-500/20 text-blue-300 rounded-xl text-xs hover:bg-blue-500/30"
              title="ویرایش"
            >
              ✏️
            </button>
            <button
              @click="handleDeletePlan(p.id)"
              class="p-2 bg-rose-500/20 text-rose-300 rounded-xl text-xs hover:bg-rose-500/30"
              title="حذف"
            >
              🗑
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== Tab 3: Builder Defaults (تنظیمات پلن‌ساز) ==================== -->
    <div v-if="activeTab === 'builder'" class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-4 text-xs">
      <div class="border-b border-gray-700/30 pb-2">
        <h3 class="font-bold text-sm text-tg">تنظیمات قیمت‌گذاری و پیش‌فرض‌های پلن‌ساز دلخواه</h3>
        <p class="text-[10px] text-tg-hint">تغییر این مقادیر بلافاصله فرمول محاسبه قیمت پلن‌ساز را در اپلیکیشن خریداران بروزرسانی می‌کند.</p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">قیمت پایه هر ماه (تومان):</label>
          <input type="number" v-model.number="builderDefaults.month_price" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
        </div>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">قیمت هر گیگابایت ترافیک (تومان):</label>
          <input type="number" v-model.number="builderDefaults.gb_price" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
        </div>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">تخفیف ۳ ماهه (%):</label>
          <input type="number" v-model.number="builderDefaults.discount_3m" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
        </div>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">تخفیف ۶ ماهه (%):</label>
          <input type="number" v-model.number="builderDefaults.discount_6m" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
        </div>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">تخفیف ۱۲ ماهه (%):</label>
          <input type="number" v-model.number="builderDefaults.discount_12m" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
        </div>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">قیمت ترافیک نامحدود (تومان):</label>
          <input type="number" v-model.number="builderDefaults.traffic_unlimited_price" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
        </div>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">سقف مصرف منصفانه ترافیک نامحدود (گیگابایت):</label>
          <input type="number" v-model.number="builderDefaults.traffic_unlimited_cap_gb" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
        </div>
      </div>

      <div class="pt-2 border-t border-gray-700/30">
        <span class="font-bold block mb-2 text-[11px]">هزینه اضافه دستگاه / آی‌پی کاربر (تومان):</span>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
          <div>
            <label class="block text-[10px] text-tg-hint">۲ کاربره:</label>
            <input type="number" v-model.number="builderDefaults.user_cost_2" class="w-full bg-tg border border-gray-700/40 rounded-xl px-2 py-1.5 font-mono text-xs" />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint">۳ کاربره:</label>
            <input type="number" v-model.number="builderDefaults.user_cost_3" class="w-full bg-tg border border-gray-700/40 rounded-xl px-2 py-1.5 font-mono text-xs" />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint">۴ کاربره:</label>
            <input type="number" v-model.number="builderDefaults.user_cost_4" class="w-full bg-tg border border-gray-700/40 rounded-xl px-2 py-1.5 font-mono text-xs" />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint">۵ کاربره:</label>
            <input type="number" v-model.number="builderDefaults.user_cost_5" class="w-full bg-tg border border-gray-700/40 rounded-xl px-2 py-1.5 font-mono text-xs" />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint">دستگاه نامحدود:</label>
            <input type="number" v-model.number="builderDefaults.user_cost_unlimited" class="w-full bg-tg border border-gray-700/40 rounded-xl px-2 py-1.5 font-mono text-xs" />
          </div>
        </div>
      </div>

      <button
        @click="handleSaveBuilderDefaults"
        :disabled="savingBuilder"
        class="w-full btn-tg font-bold py-2.5 rounded-xl text-xs transition shadow"
      >
        {{ savingBuilder ? 'در حال ذخیره‌سازی...' : 'ذخیره تنظیمات پلن‌ساز 💾' }}
      </button>
    </div>

    <!-- ==================== Tab 4: Users Management (کاربران) ==================== -->
    <div v-if="activeTab === 'users'" class="space-y-3">
      <div class="flex gap-2">
        <input
          type="text"
          v-model="userSearchQuery"
          @keyup.enter="handleSearchUsers"
          placeholder="جستجو با شناسه تلگرام..."
          class="flex-1 bg-tg-sec border border-gray-700/40 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-tg-button font-mono"
        />
        <button @click="handleSearchUsers" class="btn-tg px-4 py-2 rounded-xl text-xs font-bold">
          جستجو
        </button>
      </div>

      <div class="space-y-2">
        <div
          v-for="u in usersList"
          :key="u.id"
          class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30 text-xs flex justify-between items-center cursor-pointer hover:border-gray-600"
          @click="openUserDetailModal(u.id)"
        >
          <div>
            <div class="flex items-center gap-2">
              <span class="font-mono font-bold text-sm">{{ u.id }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded-full" :class="u.is_active ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'">
                {{ u.is_active ? 'فعال' : 'مسدود' }}
              </span>
            </div>
            <span class="text-[10px] text-tg-hint block mt-0.5">موجودی: {{ Number(u.balance).toLocaleString('fa-IR') }} تومان</span>
          </div>

          <div class="flex items-center gap-2" @click.stop>
            <button
              @click="openAdjustBalanceModal(u)"
              class="px-2.5 py-1.5 bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 rounded-xl text-[10px] font-bold"
            >
              تغییر موجودی
            </button>
            <button
              @click="handleToggleUserStatus(u.id)"
              class="px-2.5 py-1.5 rounded-xl text-[10px] font-bold"
              :class="u.is_active ? 'bg-rose-500/20 text-rose-300' : 'bg-emerald-500/20 text-emerald-300'"
            >
              {{ u.is_active ? 'مسدود' : 'فعال' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== Tab 5: Blacklist (لیست مسدودی) ==================== -->
    <div v-if="activeTab === 'blacklist'" class="space-y-3">
      <div class="flex justify-between items-center">
        <h3 class="text-xs font-bold text-tg">کاربران مسدود شده (Blacklist)</h3>
        <button @click="openAddBlacklistModal" class="bg-rose-600 hover:bg-rose-500 text-white py-1.5 px-3 rounded-xl text-xs font-bold flex items-center gap-1 shadow">
          <span>🚫</span>
          <span>مسدودسازی کاربر جدید</span>
        </button>
      </div>

      <div v-if="blacklist.length" class="space-y-2">
        <div
          v-for="b in blacklist"
          :key="b.user_id"
          class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30 text-xs flex justify-between items-center"
        >
          <div>
            <span class="font-mono font-bold block text-sm">{{ b.user_id }}</span>
            <span class="text-[10px] text-rose-300 block">دلیل: {{ b.reason }}</span>
          </div>
          <button
            @click="handleRemoveBlacklist(b.user_id)"
            class="bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 py-1.5 px-3 rounded-xl text-xs font-bold"
          >
            رفع مسدودیت
          </button>
        </div>
      </div>
      <div v-else class="text-center py-8 bg-tg-sec/40 rounded-xl border border-dashed border-gray-700/30 text-xs text-tg-hint">
        هیچ کاربری در لیست سیاه قرار ندارد.
      </div>
    </div>

    <!-- ==================== Tab 6: Admins (مدیران سیستم) ==================== -->
    <div v-if="activeTab === 'admins'" class="space-y-3">
      <div class="flex justify-between items-center">
        <h3 class="text-xs font-bold text-tg">لیست مدیران ربات و پنل</h3>
        <button @click="openAddAdminModal" class="btn-tg py-1.5 px-3 rounded-xl text-xs font-bold flex items-center gap-1 shadow">
          <span>➕</span>
          <span>افزودن مدیر جدید</span>
        </button>
      </div>

      <div class="space-y-2">
        <div
          v-for="adm in adminsList"
          :key="adm.user_id"
          class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30 text-xs flex justify-between items-center"
        >
          <div class="flex items-center gap-2">
            <span class="text-lg">{{ adm.is_owner ? '👑' : '🛡' }}</span>
            <div>
              <span class="font-mono font-bold block text-sm">{{ adm.user_id }}</span>
              <span class="text-[10px] text-tg-hint">{{ adm.is_owner ? 'مالک اصلی (Owner)' : 'مدیر همکار (Admin)' }}</span>
            </div>
          </div>
          <div v-if="!adm.is_owner">
            <button
              @click="handleRemoveAdmin(adm.user_id)"
              class="bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 py-1.5 px-3 rounded-xl text-xs font-bold"
            >
              حذف دسترسی
            </button>
          </div>
          <div v-else class="text-[10px] text-emerald-400 font-bold px-2 py-1 bg-emerald-500/10 rounded-lg">
            مالک دائمی
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== Tab 7: Payments & Gateways & Stars ==================== -->
    <div v-if="activeTab === 'payments'" class="space-y-4">
      <!-- 1. Card-to-Card Info -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3 text-xs">
        <div class="flex items-center gap-2 border-b border-gray-700/30 pb-2">
          <span class="text-lg">💳</span>
          <div>
            <h4 class="font-bold text-sm text-tg">مشخصات حساب کارت‌به‌کارت</h4>
            <span class="text-[10px] text-tg-hint">جهت واریز و ارسال فیش توسط خریداران</span>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">شماره کارت ۱۶ رقمی:</label>
            <input type="text" v-model="paymentsConfig.card.card_number" dir="ltr" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">نام صاحب حساب:</label>
            <input type="text" v-model="paymentsConfig.card.card_holder" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs" />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">نام بانک:</label>
            <input type="text" v-model="paymentsConfig.card.bank_name" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs" />
          </div>
        </div>
      </div>

      <!-- 2. Telegram Stars Payment (NEW) -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-yellow-500/30 space-y-3 text-xs">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-2">
            <span class="text-xl">⭐</span>
            <div>
              <h4 class="font-bold text-sm text-yellow-300">درگاه تلگرام استارز (Telegram Stars)</h4>
              <span class="text-[10px] text-tg-hint">پرداخت مستقیم درون‌برنامه‌ای تلگرام — بدون نیاز به درگاه بانکی</span>
            </div>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="paymentsConfig.stars.enabled" class="sr-only peer" />
            <div class="w-9 h-5 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-yellow-500"></div>
          </label>
        </div>

        <div v-if="paymentsConfig.stars.enabled" class="space-y-2 pt-2 border-t border-gray-700/30">
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">نرخ تبدیل هر استارز به تومان (Exchange Rate):</label>
            <input type="number" v-model.number="paymentsConfig.stars.rate" dir="ltr" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
            <span class="text-[10px] text-tg-hint block mt-1">
              مثال: با نرخ ۱۵۰۰ تومان، یک پلن ۱۵۰,۰۰۰ تومانی معادل ۱۰۰ استارز محاسبه می‌شود. تمام استارزهای دریافتی مستقیماً به موجودی مالک ربات واریز می‌گردد.
            </span>
          </div>
        </div>
      </div>

      <!-- 3. Zibal Gateway -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3 text-xs">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-2">
            <span class="text-xl">⚡️</span>
            <div>
              <h4 class="font-bold text-sm text-tg">درگاه پرداخت زیبال (Zibal)</h4>
              <span class="text-[10px] text-tg-hint">پرداخت اینترنتی شاپرک با تایید آنی</span>
            </div>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="paymentsConfig.zibal.enabled" class="sr-only peer" />
            <div class="w-9 h-5 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
          </label>
        </div>

        <div v-if="paymentsConfig.zibal.enabled" class="space-y-2 pt-2 border-t border-gray-700/30">
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">مرچنت کی زیبال (Merchant Key):</label>
            <input type="text" v-model="paymentsConfig.zibal.merchant" dir="ltr" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
          </div>
          <div class="flex items-center justify-between">
            <span class="text-tg-hint text-xs">محیط تستی زیبال (Sandbox):</span>
            <input type="checkbox" v-model="paymentsConfig.zibal.sandbox" class="rounded accent-tg-button" />
          </div>
        </div>
      </div>

      <!-- 4. Zarinpal Gateway -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3 text-xs">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-2">
            <span class="text-xl">🟡</span>
            <div>
              <h4 class="font-bold text-sm text-tg">درگاه پرداخت زرین‌پال (Zarinpal)</h4>
              <span class="text-[10px] text-tg-hint">پرداخت شتابی شاپرک</span>
            </div>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="paymentsConfig.zarinpal.enabled" class="sr-only peer" />
            <div class="w-9 h-5 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
          </label>
        </div>

        <div v-if="paymentsConfig.zarinpal.enabled" class="space-y-2 pt-2 border-t border-gray-700/30">
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">مرچنت ۳۶ رقمی زرین‌پال:</label>
            <input type="text" v-model="paymentsConfig.zarinpal.merchant" dir="ltr" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
          </div>
          <div class="flex items-center justify-between">
            <span class="text-tg-hint text-xs">محیط تستی زرین‌پال (Sandbox):</span>
            <input type="checkbox" v-model="paymentsConfig.zarinpal.sandbox" class="rounded accent-tg-button" />
          </div>
        </div>
      </div>

      <button
        @click="handleSavePayments"
        :disabled="savingPayments"
        class="w-full btn-tg font-bold py-2.5 rounded-xl text-xs transition shadow"
      >
        {{ savingPayments ? 'در حال ذخیره‌سازی...' : 'ذخیره تمام روش‌های پرداخت و استارز 💾' }}
      </button>
    </div>

    <!-- ==================== Tab 8: Backups & Ops Mode (بکاپ و عملیات) ==================== -->
    <div v-if="activeTab === 'backups'" class="space-y-4 text-xs">
      <!-- Operating Mode Box -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <h4 class="font-bold text-sm text-tg">حالت کاری سیستم (Operating Mode)</h4>
        <div class="grid grid-cols-3 gap-2">
          <button
            @click="handleSetOpsMode('NORMAL')"
            class="p-2.5 rounded-xl font-bold transition text-center"
            :class="opsMode === 'NORMAL' ? 'bg-emerald-600 text-white shadow' : 'bg-tg border border-gray-700 text-tg-hint'"
          >
            عادی (NORMAL)
          </button>
          <button
            @click="handleSetOpsMode('SALES_PAUSED')"
            class="p-2.5 rounded-xl font-bold transition text-center"
            :class="opsMode === 'SALES_PAUSED' ? 'bg-amber-600 text-white shadow' : 'bg-tg border border-gray-700 text-tg-hint'"
          >
            توقف فروش
          </button>
          <button
            @click="handleSetOpsMode('MAINTENANCE')"
            class="p-2.5 rounded-xl font-bold transition text-center"
            :class="opsMode === 'MAINTENANCE' ? 'bg-rose-600 text-white shadow' : 'bg-tg border border-gray-700 text-tg-hint'"
          >
            تعمیرات
          </button>
        </div>
      </div>

      <!-- Backup Box -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <h4 class="font-bold text-sm text-tg">پشتیبان‌گیری از دیتابیس (SQLite Backups)</h4>
          <button
            @click="handleCreateBackup"
            :disabled="creatingBackup"
            class="btn-tg py-1.5 px-3 rounded-xl font-bold shadow"
          >
            {{ creatingBackup ? 'در حال تهیه...' : 'ایجاد بکاپ فوری 💾' }}
          </button>
        </div>

        <div v-if="backupsList.length" class="space-y-1.5 max-h-60 overflow-y-auto">
          <div
            v-for="bk in backupsList"
            :key="bk.name"
            class="bg-tg p-2.5 rounded-xl border border-gray-700/30 flex justify-between items-center text-xs"
          >
            <div>
              <span class="font-mono font-bold block">{{ bk.name }}</span>
              <span class="text-[10px] text-tg-hint">{{ bk.size_kb }} KB</span>
            </div>
            <span class="text-[10px] text-tg-hint font-mono">
              {{ new Date(bk.created_at * 1000).toLocaleString('fa-IR') }}
            </span>
          </div>
        </div>
        <div v-else class="text-center py-4 text-tg-hint text-[10px]">
          هنوز فایل بکاپی ساخته نشده است.
        </div>
      </div>
    </div>

    <!-- ==================== Tab 9: Server Status (وضعیت سرور) ==================== -->
    <div v-if="activeTab === 'server'" class="space-y-3 text-xs">
      <div v-if="serverStatus" class="space-y-3">
        <!-- Resource Bars -->
        <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
          <h4 class="font-bold text-sm text-tg">منابع سخت‌افزاری سرور</h4>

          <!-- RAM -->
          <div class="space-y-1">
            <div class="flex justify-between text-[11px]">
              <span>حافظه موقت (RAM):</span>
              <span class="font-mono">{{ serverStatus.ram.used_mb }} MB / {{ serverStatus.ram.total_mb }} MB ({{ serverStatus.ram.percent }}%)</span>
            </div>
            <div class="w-full bg-gray-700/50 rounded-full h-2">
              <div class="bg-blue-500 h-2 rounded-full" :style="{ width: Math.min(100, serverStatus.ram.percent) + '%' }"></div>
            </div>
          </div>

          <!-- Disk -->
          <div class="space-y-1">
            <div class="flex justify-between text-[11px]">
              <span>فضای هارد (Disk):</span>
              <span class="font-mono">{{ serverStatus.disk.used_gb }} GB / {{ serverStatus.disk.total_gb }} GB ({{ serverStatus.disk.percent }}%)</span>
            </div>
            <div class="w-full bg-gray-700/50 rounded-full h-2">
              <div class="bg-emerald-500 h-2 rounded-full" :style="{ width: Math.min(100, serverStatus.disk.percent) + '%' }"></div>
            </div>
          </div>
        </div>

        <!-- Details -->
        <div class="grid grid-cols-2 gap-2">
          <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
            <span class="text-tg-hint text-[10px] block">فشار پردازنده (CPU Load)</span>
            <span class="text-base font-bold font-mono text-tg mt-0.5 block">{{ serverStatus.cpu_load }}</span>
          </div>
          <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
            <span class="text-tg-hint text-[10px] block">آپ‌تایم سرور</span>
            <span class="text-base font-bold font-mono text-tg mt-0.5 block">{{ serverStatus.uptime_hours }} ساعت</span>
          </div>
          <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
            <span class="text-tg-hint text-[10px] block">نسخه پایتون</span>
            <span class="text-base font-bold font-mono text-tg mt-0.5 block">{{ serverStatus.python_version }}</span>
          </div>
          <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
            <span class="text-tg-hint text-[10px] block">پینگ 3x-ui</span>
            <span class="text-base font-bold font-mono mt-0.5 block" :class="serverStatus.xui.connected ? 'text-emerald-400' : 'text-rose-400'">
              {{ serverStatus.xui.connected ? serverStatus.xui.latency_ms + ' ms' : 'قطع' }}
            </span>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-8 text-tg-hint">
        در حال دریافت اطلاعات سرور...
      </div>
    </div>

    <!-- ==================== Tab 10: Broadcast (ارسال پیام همگانی) ==================== -->
    <div v-if="activeTab === 'broadcast'" class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3 text-xs">
      <label class="block text-xs font-semibold">ارسال پیام به تلگرام کاربران:</label>

      <div>
        <label class="block text-[10px] text-tg-hint mb-1">مخاطبین هدف:</label>
        <select v-model="broadcastAudience" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs">
          <option value="all">همه کاربران فعال</option>
          <option value="customers">خریداران (مشتریان)</option>
          <option value="trial">کاربران تست رایگان</option>
          <option value="never_bought">کاربرانی که خریدی نداشته‌اند</option>
        </select>
      </div>

      <div>
        <label class="block text-[10px] text-tg-hint mb-1">متن پیام (قالب‌بندی HTML مجاز است):</label>
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
        class="w-full btn-tg font-bold py-2.5 rounded-xl text-xs transition shadow"
      >
        {{ sendingBroadcast ? 'در حال ارسال پیام...' : 'ارسال همگانی 🚀' }}
      </button>
    </div>

    <!-- ==================== Tab 11: Branding / UI Title ==================== -->
    <div v-if="activeTab === 'branding'" class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3 text-xs">
      <div class="flex items-center gap-2">
        <span class="text-lg">🎨</span>
        <div>
          <span class="font-bold block text-sm">نام و عنوان وب‌اپلیکیشن</span>
          <span class="text-[10px] text-tg-hint">تغییر عنوان در تب مرورگر و بالای مینی‌اپ</span>
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
      </div>

      <button
        @click="handleSaveBranding"
        :disabled="savingBranding || !uiTitle.trim()"
        class="w-full btn-tg font-bold py-2.5 rounded-xl text-xs transition active:scale-95 shadow"
      >
        {{ savingBranding ? 'در حال ذخیره‌سازی...' : 'ذخیره عنوان وب‌اپ 💾' }}
      </button>
    </div>

    <!-- ==================== MODALS ==================== -->

    <!-- Modal 1: Plan Create/Edit Modal -->
    <div v-if="showPlanModal" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-md w-full p-4 space-y-3 text-xs shadow-2xl">
        <div class="flex justify-between items-center border-b border-gray-700/30 pb-2">
          <h4 class="font-bold text-sm">{{ isEditingPlan ? 'ویرایش پلان' : 'افزودن پلان جدید' }}</h4>
          <button @click="showPlanModal = false" class="text-tg-hint hover:text-tg text-sm">✕</button>
        </div>

        <div class="space-y-2">
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">نام پلان:</label>
            <input type="text" v-model="planForm.name" placeholder="مثلاً: ۳۰ روزه نامحدود ۱ کاربره" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2" />
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">قیمت (تومان):</label>
              <input type="number" v-model.number="planForm.price" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
            </div>
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">مدت زمان (روز):</label>
              <input type="number" v-model.number="planForm.days" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
            </div>
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">حجم (گیگابایت - 0=نامحدود):</label>
              <input type="number" v-model.number="planForm.volume_gb" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
            </div>
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">تعداد کاربر (IP Limit - 0=نامحدود):</label>
              <input type="number" v-model.number="planForm.ip_limit" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
            </div>
          </div>
        </div>

        <div class="flex gap-2 pt-2">
          <button @click="handleSavePlan" class="flex-1 btn-tg py-2 rounded-xl font-bold shadow">
            ذخیره پلان 💾
          </button>
          <button @click="showPlanModal = false" class="px-4 bg-gray-700/40 text-tg-hint rounded-xl">
            انصراف
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 2: User Detail Modal -->
    <div v-if="selectedUserDetail" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-md w-full p-4 space-y-3 text-xs shadow-2xl max-h-[85vh] overflow-y-auto">
        <div class="flex justify-between items-center border-b border-gray-700/30 pb-2">
          <h4 class="font-bold text-sm">پروفایل کاربر {{ selectedUserDetail.user.id }}</h4>
          <button @click="selectedUserDetail = null" class="text-tg-hint hover:text-tg text-sm">✕</button>
        </div>

        <div class="grid grid-cols-2 gap-2 bg-tg p-3 rounded-xl">
          <div>
            <span class="text-tg-hint text-[10px] block">موجودی کیف پول:</span>
            <span class="font-bold text-emerald-400 text-sm">{{ Number(selectedUserDetail.user.balance).toLocaleString('fa-IR') }} تومان</span>
          </div>
          <div>
            <span class="text-tg-hint text-[10px] block">وضعیت:</span>
            <span class="font-bold" :class="selectedUserDetail.user.is_active ? 'text-emerald-400' : 'text-rose-400'">
              {{ selectedUserDetail.user.is_active ? 'فعال' : 'مسدود' }}
            </span>
          </div>
        </div>

        <div>
          <span class="font-bold block mb-1">سرویس‌های فعال ({{ selectedUserDetail.services.length }}):</span>
          <div v-if="selectedUserDetail.services.length" class="space-y-1">
            <div v-for="s in selectedUserDetail.services" :key="s.id" class="p-2 bg-tg rounded-lg font-mono text-[10px] flex justify-between">
              <span>{{ s.sub_id || 'سرویس' }}</span>
              <span class="text-tg-hint">{{ s.status }}</span>
            </div>
          </div>
          <div v-else class="text-tg-hint text-[10px]">سرویسی یافت نشد.</div>
        </div>

        <div>
          <span class="font-bold block mb-1">تاریخچه تراکنش‌ها ({{ selectedUserDetail.transactions.length }}):</span>
          <div v-if="selectedUserDetail.transactions.length" class="space-y-1">
            <div v-for="t in selectedUserDetail.transactions" :key="t.id" class="p-2 bg-tg rounded-lg text-[10px] flex justify-between items-center">
              <div>
                <span class="font-bold block">{{ t.plan }}</span>
                <span class="text-tg-hint">#{{ t.id }} | {{ t.method }}</span>
              </div>
              <span class="text-emerald-400 font-mono font-bold">{{ Number(t.price).toLocaleString('fa-IR') }} تومان</span>
            </div>
          </div>
          <div v-else class="text-tg-hint text-[10px]">تراکنشی ثبت نشده است.</div>
        </div>

        <button @click="selectedUserDetail = null" class="w-full bg-gray-700/40 text-tg py-2 rounded-xl font-bold">
          بستن
        </button>
      </div>
    </div>

    <!-- Modal 3: Adjust Balance Modal -->
    <div v-if="adjustBalanceUser" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-sm w-full p-4 space-y-3 text-xs shadow-2xl">
        <h4 class="font-bold text-sm">تغییر موجودی کاربر {{ adjustBalanceUser.id }}</h4>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">مبلغ تغییر (تومان - برای کسر علامت منفی بگذارید):</label>
          <input type="number" v-model.number="adjustBalanceAmount" placeholder="مثلاً: 50000 یا -20000" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
        </div>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">دلیل تغییر:</label>
          <input type="text" v-model="adjustBalanceReason" placeholder="شارژ دستی توسط مدیریت" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs" />
        </div>
        <div class="flex gap-2 pt-1">
          <button @click="handleConfirmAdjustBalance" class="flex-1 btn-tg py-2 rounded-xl font-bold shadow">
            ثبت تغییر 💾
          </button>
          <button @click="adjustBalanceUser = null" class="px-4 bg-gray-700/40 text-tg-hint rounded-xl">
            انصراف
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 4: Add Blacklist Modal -->
    <div v-if="showAddBlacklistModal" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-sm w-full p-4 space-y-3 text-xs shadow-2xl">
        <h4 class="font-bold text-sm text-rose-400">مسدودسازی کاربر جدید</h4>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">شناسه عددی تلگرام کاربر:</label>
          <input type="number" v-model.number="blacklistForm.user_id" placeholder="12345678" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
        </div>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">دلیل مسدودسازی:</label>
          <input type="text" v-model="blacklistForm.reason" placeholder="سوء استفاده از سرویس / نقض قوانین" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs" />
        </div>
        <div class="flex gap-2 pt-1">
          <button @click="handleConfirmAddBlacklist" class="flex-1 bg-rose-600 hover:bg-rose-500 text-white py-2 rounded-xl font-bold shadow">
            مسدودسازی 🚫
          </button>
          <button @click="showAddBlacklistModal = false" class="px-4 bg-gray-700/40 text-tg-hint rounded-xl">
            انصراف
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 5: Add Admin Modal -->
    <div v-if="showAddAdminModal" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-sm w-full p-4 space-y-3 text-xs shadow-2xl">
        <h4 class="font-bold text-sm">افزودن مدیر جدید</h4>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">شناسه عددی تلگرام مدیر:</label>
          <input type="number" v-model.number="newAdminId" placeholder="12345678" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
          <span class="text-[10px] text-tg-hint block mt-1">مدیر جدید به تمام بخش‌های پنل و دستور /sudoadmin دسترسی خواهد داشت.</span>
        </div>
        <div class="flex gap-2 pt-1">
          <button @click="handleConfirmAddAdmin" class="flex-1 btn-tg py-2 rounded-xl font-bold shadow">
            ثبت مدیر 👑
          </button>
          <button @click="showAddAdminModal = false" class="px-4 bg-gray-700/40 text-tg-hint rounded-xl">
            انصراف
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  getAdminStats,
  getAdminOrders,
  approveOrder,
  rejectOrder,
  getAdminUsers,
  getAdminUserDetail,
  adjustUserBalance,
  toggleUserStatus,
  getAdminPlans,
  createAdminPlan,
  updateAdminPlan,
  deleteAdminPlan,
  toggleAdminPlan,
  getAdminBuilderDefaults,
  saveAdminBuilderDefaults,
  getAdminBlacklist,
  addAdminBlacklist,
  removeAdminBlacklist,
  getAdminList,
  addAdmin,
  removeAdmin,
  getAdminBackups,
  createAdminBackup,
  getAdminOpsMode,
  saveAdminOpsMode,
  getAdminServerStatus,
  getAdminPayments,
  saveAdminPayments,
  sendBroadcast,
  getAdminBranding,
  saveAdminBranding
} from '@/api'

// Navigation Tabs
const activeTab = ref('orders')
const tabs = computed(() => [
  { id: 'orders', label: 'سفارش‌ها', icon: '📑', badge: orders.value.length || null },
  { id: 'plans', label: 'پلان‌ها', icon: '📦' },
  { id: 'builder', label: 'پلن‌ساز', icon: '🛠' },
  { id: 'users', label: 'کاربران', icon: '👥' },
  { id: 'blacklist', label: 'مسدودی', icon: '🚫' },
  { id: 'admins', label: 'مدیران', icon: '👑' },
  { id: 'payments', label: 'پرداخت و استارز', icon: '💳' },
  { id: 'backups', label: 'بکاپ و عملیات', icon: '💾' },
  { id: 'server', label: 'وضعیت سرور', icon: '🖥' },
  { id: 'broadcast', label: 'پیام همگانی', icon: '📢' },
  { id: 'branding', label: 'عنوان و ظاهر', icon: '🎨' },
])

// Global UI State
const globalMsg = ref('')
const globalSuccess = ref(true)
const actionLoading = ref(null)

// Stats & Server Status
const stats = ref({})
const serverStatus = ref(null)

// Orders
const orders = ref([])

// Plans
const plansList = ref([])
const showPlanModal = ref(false)
const isEditingPlan = ref(false)
const planForm = ref({ id: null, name: '', price: 100000, days: 30, volume_gb: 0, ip_limit: 1, active: 1, sort_order: 100 })

// Builder Defaults
const builderDefaults = ref({
  month_price: 120000,
  gb_price: 1000,
  discount_3m: 5,
  discount_6m: 10,
  discount_12m: 20,
  traffic_discount_50: 5,
  traffic_discount_100: 15,
  traffic_discount_300: 30,
  traffic_unlimited_price: 500000,
  traffic_unlimited_cap_gb: 1000,
  user_cost_1: 0,
  user_cost_2: 20000,
  user_cost_3: 35000,
  user_cost_4: 45000,
  user_cost_5: 50000,
  user_cost_unlimited: 65000,
})
const savingBuilder = ref(false)

// Users
const usersList = ref([])
const userSearchQuery = ref('')
const selectedUserDetail = ref(null)
const adjustBalanceUser = ref(null)
const adjustBalanceAmount = ref(0)
const adjustBalanceReason = ref('')

// Blacklist
const blacklist = ref([])
const showAddBlacklistModal = ref(false)
const blacklistForm = ref({ user_id: null, reason: '' })

// Admins
const adminsList = ref([])
const showAddAdminModal = ref(false)
const newAdminId = ref(null)

// Payments & Gateways & Stars
const paymentsConfig = ref({
  card: { card_number: '', card_holder: '', bank_name: '' },
  zibal: { enabled: false, merchant: '', sandbox: false },
  zarinpal: { enabled: false, merchant: '', sandbox: false },
  stars: { enabled: true, rate: 1500 }
})
const savingPayments = ref(false)

// Backups & Ops Mode
const backupsList = ref([])
const opsMode = ref('NORMAL')
const creatingBackup = ref(false)

// Broadcast
const broadcastAudience = ref('all')
const broadcastText = ref('')
const sendingBroadcast = ref(false)

// Branding
const uiTitle = ref('')
const savingBranding = ref(false)

const showNotify = (msg, success = true) => {
  globalMsg.value = msg
  globalSuccess.value = success
  setTimeout(() => { globalMsg.value = '' }, 4000)
}

// ─── Data Loaders ────────────────────────────────────────────────────────────
const loadData = async () => {
  try {
    const [stRes, ordRes, plRes, uRes, bldRes, blRes, admRes, payRes, bkRes, srvRes, brRes] = await Promise.all([
      getAdminStats().catch(() => ({ data: {} })),
      getAdminOrders().catch(() => ({ data: { orders: [] } })),
      getAdminPlans().catch(() => ({ data: { plans: [] } })),
      getAdminUsers().catch(() => ({ data: { users: [] } })),
      getAdminBuilderDefaults().catch(() => ({ data: null })),
      getAdminBlacklist().catch(() => ({ data: { blacklist: [] } })),
      getAdminList().catch(() => ({ data: { admins: [] } })),
      getAdminPayments().catch(() => ({ data: null })),
      getAdminBackups().catch(() => ({ data: { backups: [] } })),
      getAdminServerStatus().catch(() => ({ data: null })),
      getAdminBranding().catch(() => ({ data: { webapp_title: '' } }))
    ])

    stats.value = stRes.data || {}
    orders.value = ordRes.data?.orders || []
    plansList.value = plRes.data?.plans || []
    usersList.value = uRes.data?.users || []
    if (bldRes?.data) builderDefaults.value = { ...builderDefaults.value, ...bldRes.data }
    blacklist.value = blRes.data?.blacklist || []
    adminsList.value = admRes.data?.admins || []
    if (payRes?.data) paymentsConfig.value = { ...paymentsConfig.value, ...payRes.data }
    backupsList.value = bkRes.data?.backups || []
    serverStatus.value = srvRes?.data || null
    uiTitle.value = brRes.data?.webapp_title || ''

    const modeRes = await getAdminOpsMode().catch(() => null)
    if (modeRes?.data?.mode) opsMode.value = modeRes.data.mode
  } catch (err) {
    console.error('Error loading admin data:', err)
  }
}

// ─── Orders Handlers ─────────────────────────────────────────────────────────
const handleApprove = async (orderId) => {
  actionLoading.value = orderId
  try {
    await approveOrder(orderId)
    showNotify(`سفارش #${orderId} با موفقیت تایید و سرویس ساخته شد!`)
    orders.value = orders.value.filter(o => o.id !== orderId)
    loadData()
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در تایید سفارش', false)
  } finally {
    actionLoading.value = null
  }
}

const handleReject = async (orderId) => {
  actionLoading.value = orderId
  try {
    await rejectOrder(orderId, 'فیش نامعتبر است.')
    showNotify(`سفارش #${orderId} رد شد.`)
    orders.value = orders.value.filter(o => o.id !== orderId)
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در رد سفارش', false)
  } finally {
    actionLoading.value = null
  }
}

// ─── Plans Handlers ──────────────────────────────────────────────────────────
const openCreatePlanModal = () => {
  isEditingPlan.value = false
  planForm.value = { id: null, name: '', price: 100000, days: 30, volume_gb: 0, ip_limit: 1, active: 1, sort_order: 100 }
  showPlanModal.value = true
}

const openEditPlanModal = (plan) => {
  isEditingPlan.value = true
  planForm.value = { ...plan }
  showPlanModal.value = true
}

const handleSavePlan = async () => {
  try {
    if (isEditingPlan.value) {
      await updateAdminPlan(planForm.value.id, planForm.value)
      showNotify('پلان با موفقیت ویرایش شد.')
    } else {
      await createAdminPlan(planForm.value)
      showNotify('پلان جدید با موفقیت اضافه شد.')
    }
    showPlanModal.value = false
    const res = await getAdminPlans()
    plansList.value = res.data?.plans || []
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ذخیره پلان', false)
  }
}

const handleTogglePlan = async (planId) => {
  try {
    const res = await toggleAdminPlan(planId)
    const target = plansList.value.find(p => p.id === planId)
    if (target) target.active = res.data.active
    showNotify('وضعیت پلان تغییر یافت.')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در تغییر وضعیت پلان', false)
  }
}

const handleDeletePlan = async (planId) => {
  if (!confirm('آیا از حذف این پلان مطمئن هستید؟')) return
  try {
    await deleteAdminPlan(planId)
    plansList.value = plansList.value.filter(p => p.id !== planId)
    showNotify('پلان حذف شد.')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در حذف پلان', false)
  }
}

// ─── Builder Defaults ────────────────────────────────────────────────────────
const handleSaveBuilderDefaults = async () => {
  savingBuilder.value = true
  try {
    await saveAdminBuilderDefaults(builderDefaults.value)
    showNotify('پیش‌فرض‌های پلن‌ساز با موفقیت ذخیره شد.')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ذخیره پلن‌ساز', false)
  } finally {
    savingBuilder.value = false
  }
}

// ─── Users Handlers ──────────────────────────────────────────────────────────
const handleSearchUsers = async () => {
  try {
    const res = await getAdminUsers(100, 0, userSearchQuery.value || null)
    usersList.value = res.data?.users || []
  } catch (err) {
    showNotify('خطا در جستجوی کاربران', false)
  }
}

const openUserDetailModal = async (userId) => {
  try {
    const res = await getAdminUserDetail(userId)
    selectedUserDetail.value = res.data
  } catch (err) {
    showNotify('خطا در دریافت جزئیات کاربر', false)
  }
}

const openAdjustBalanceModal = (u) => {
  adjustBalanceUser.value = u
  adjustBalanceAmount.value = 0
  adjustBalanceReason.value = 'شارژ دستی توسط مدیریت'
}

const handleConfirmAdjustBalance = async () => {
  if (!adjustBalanceAmount.value) return
  try {
    const res = await adjustUserBalance(adjustBalanceUser.value.id, adjustBalanceAmount.value, adjustBalanceReason.value)
    adjustBalanceUser.value.balance = res.data.new_balance
    showNotify(`موجودی کاربر ${adjustBalanceUser.value.id} بروزرسانی شد.`)
    adjustBalanceUser.value = null
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در تغییر موجودی', false)
  }
}

const handleToggleUserStatus = async (userId) => {
  try {
    const res = await toggleUserStatus(userId)
    const target = usersList.value.find(u => u.id === userId)
    if (target) target.is_active = res.data.is_active
    showNotify('وضعیت کاربر تغییر یافت.')
  } catch (err) {
    showNotify('خطا در تغییر وضعیت کاربر', false)
  }
}

// ─── Blacklist Handlers ──────────────────────────────────────────────────────
const openAddBlacklistModal = () => {
  blacklistForm.value = { user_id: null, reason: 'نقض قوانین سرویس' }
  showAddBlacklistModal.value = true
}

const handleConfirmAddBlacklist = async () => {
  if (!blacklistForm.value.user_id) return
  try {
    await addAdminBlacklist(blacklistForm.value.user_id, blacklistForm.value.reason)
    showNotify(`کاربر ${blacklistForm.value.user_id} مسدود شد.`)
    showAddBlacklistModal.value = false
    const res = await getAdminBlacklist()
    blacklist.value = res.data?.blacklist || []
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در مسدودسازی کاربر', false)
  }
}

const handleRemoveBlacklist = async (userId) => {
  try {
    await removeAdminBlacklist(userId)
    blacklist.value = blacklist.value.filter(b => b.user_id !== userId)
    showNotify(`مسدودیت کاربر ${userId} لغو شد.`)
  } catch (err) {
    showNotify('خطا در رفع مسدودیت', false)
  }
}

// ─── Admins Handlers ─────────────────────────────────────────────────────────
const openAddAdminModal = () => {
  newAdminId.value = null
  showAddAdminModal.value = true
}

const handleConfirmAddAdmin = async () => {
  if (!newAdminId.value) return
  try {
    await addAdmin(newAdminId.value)
    showNotify(`مدیر ${newAdminId.value} با موفقیت اضافه شد.`)
    showAddAdminModal.value = false
    const res = await getAdminList()
    adminsList.value = res.data?.admins || []
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در افزودن مدیر', false)
  }
}

const handleRemoveAdmin = async (userId) => {
  if (!confirm(`آیا دسترسی مدیر ${userId} حذف شود؟`)) return
  try {
    await removeAdmin(userId)
    adminsList.value = adminsList.value.filter(a => a.user_id !== userId)
    showNotify('دسترسی مدیر حذف شد.')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در حذف مدیر', false)
  }
}

// ─── Payments & Stars Handlers ───────────────────────────────────────────────
const handleSavePayments = async () => {
  savingPayments.value = true
  try {
    await saveAdminPayments({
      card_number: paymentsConfig.value.card.card_number,
      card_holder: paymentsConfig.value.card.card_holder,
      bank_name: paymentsConfig.value.card.bank_name,
      zibal_enabled: paymentsConfig.value.zibal.enabled,
      zibal_merchant: paymentsConfig.value.zibal.merchant,
      zibal_sandbox: paymentsConfig.value.zibal.sandbox,
      zarinpal_enabled: paymentsConfig.value.zarinpal.enabled,
      zarinpal_merchant: paymentsConfig.value.zarinpal.merchant,
      zarinpal_sandbox: paymentsConfig.value.zarinpal.sandbox,
      stars_enabled: paymentsConfig.value.stars.enabled,
      stars_rate: paymentsConfig.value.stars.rate,
    })
    showNotify('تنظیمات روش‌های پرداخت و استارز ذخیره شد.')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ذخیره روش‌های پرداخت', false)
  } finally {
    savingPayments.value = false
  }
}

// ─── Backups & Ops Mode ──────────────────────────────────────────────────────
const handleCreateBackup = async () => {
  creatingBackup.value = true
  try {
    const res = await createAdminBackup()
    showNotify(res.data?.message || 'بکاپ ساخته شد.')
    const bRes = await getAdminBackups()
    backupsList.value = bRes.data?.backups || []
  } catch (err) {
    showNotify('خطا در ایجاد بکاپ', false)
  } finally {
    creatingBackup.value = false
  }
}

const handleSetOpsMode = async (mode) => {
  try {
    await saveAdminOpsMode(mode)
    opsMode.value = mode
    showNotify(`حالت کاری به ${mode} تغییر یافت.`)
  } catch (err) {
    showNotify('خطا در تغییر حالت کاری', false)
  }
}

// ─── Broadcast Handlers ──────────────────────────────────────────────────────
const handleBroadcast = async () => {
  if (!broadcastText.value.trim()) return
  sendingBroadcast.value = true
  try {
    await sendBroadcast(broadcastText.value.trim(), broadcastAudience.value)
    showNotify('پیام همگانی در صف ارسال قرار گرفت 🚀')
    broadcastText.value = ''
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ارسال پیام', false)
  } finally {
    sendingBroadcast.value = false
  }
}

// ─── Branding Handlers ───────────────────────────────────────────────────────
const handleSaveBranding = async () => {
  if (!uiTitle.value.trim()) return
  savingBranding.value = true
  try {
    await saveAdminBranding({ webapp_title: uiTitle.value.trim() })
    showNotify('عنوان وب‌اپ ذخیره شد.')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ذخیره عنوان', false)
  } finally {
    savingBranding.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>
