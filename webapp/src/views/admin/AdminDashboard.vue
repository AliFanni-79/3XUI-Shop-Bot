<template>
  <div class="space-y-4">
    <!-- Header with Back -->
    <div class="flex items-center justify-between pb-2 border-b border-gray-700/30">
      <div class="flex items-center gap-2">
        <router-link to="/" class="text-tg-hint hover:text-tg text-sm font-bold">
          ← بازگشت
        </router-link>
        <h2 class="text-sm font-bold">⚙️ پنل مدیریت ارشد {{ uiTitle || auth.appTitle || 'فروشگاه' }}</h2>
        <span class="bg-blue-500/20 text-blue-400 border border-blue-500/30 text-[10px] px-2 py-0.5 rounded-full font-mono font-bold">
          v{{ appVersion }}
        </span>
      </div>
      <button @click="loadData" class="text-xs text-tg-button hover:underline flex items-center gap-1">
        🔄 <span>بروزرسانی</span>
      </button>
    </div>

    <!-- Quick Stats Grid -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
      <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
        <span class="text-tg-hint text-[10px] block">نسخه فعال نرم‌افزار</span>
        <span class="text-base font-bold text-sky-400 mt-0.5 block font-mono">v{{ appVersion }}</span>
      </div>
      <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
        <span class="text-tg-hint text-[10px] block">سرویس تست رایگان</span>
        <span class="text-base font-bold mt-0.5 block" :class="trialSettings.enabled ? 'text-emerald-400' : 'text-gray-400'">
          {{ trialSettings.enabled ? 'فعال ✓' : 'غیرفعال' }}
        </span>
      </div>
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
        <span class="text-xs font-bold mt-1 flex items-center gap-1" :class="serverStatus?.xui?.connected ? 'text-emerald-400' : 'text-rose-400'">
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
      <!-- Sub-tabs -->
      <div class="flex gap-1.5 border-b border-gray-700/30 pb-2 text-xs">
        <button
          @click="plansSubTab = 'catalog'"
          class="py-1.5 px-3 rounded-xl transition font-medium"
          :class="plansSubTab === 'catalog' ? 'bg-tg-button text-white font-bold' : 'bg-tg-sec text-tg-hint hover:text-tg'"
        >
          📦 پلان‌ها ({{ plansList.length }})
        </button>
        <button
          @click="plansSubTab = 'categories'"
          class="py-1.5 px-3 rounded-xl transition font-medium"
          :class="plansSubTab === 'categories' ? 'bg-tg-button text-white font-bold' : 'bg-tg-sec text-tg-hint hover:text-tg'"
        >
          🗂 دسته‌بندی‌ها ({{ categoriesList.length }})
        </button>
        <button
          @click="plansSubTab = 'volume'"
          class="py-1.5 px-3 rounded-xl transition font-medium"
          :class="plansSubTab === 'volume' ? 'bg-tg-button text-white font-bold' : 'bg-tg-sec text-tg-hint hover:text-tg'"
        >
          ➕ بسته‌های حجم اضافه ({{ volumePacksList.length }})
        </button>
      </div>

      <!-- 2.1 Catalog Plans List -->
      <div v-if="plansSubTab === 'catalog'" class="space-y-3">
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
                <span v-if="getCategoryName(p.category_id)" class="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300">
                  {{ getCategoryIcon(p.category_id) }} {{ getCategoryName(p.category_id) }}
                </span>
              </div>
              <div class="text-[10px] text-tg-hint flex flex-wrap gap-x-3 gap-y-0.5">
                <span>مدت: {{ p.days }} روز</span>
                <span>حجم: {{ p.volume_gb > 0 ? p.volume_gb + ' GB' : 'نامحدود' }}</span>
                <span>کاربر: {{ p.ip_limit > 0 ? p.ip_limit + ' کاربره' : 'نامحدود' }}</span>
                <span v-if="p.group_name" class="text-blue-400 font-semibold">👥 گروه: {{ p.group_name }}</span>
              </div>
              <div class="text-emerald-400 font-bold text-xs pt-0.5">
                {{ Number(p.price).toLocaleString('fa-IR') }} تومان
              </div>
            </div>

            <div class="flex items-center gap-1.5">
              <button
                @click="openPlanInboundsModal(p)"
                class="p-2 bg-indigo-500/20 text-indigo-300 rounded-xl text-xs hover:bg-indigo-500/30"
                title="مسیریابی اینباندها"
              >
                🔀 اینباندها
              </button>
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

      <!-- 2.2 Categories List -->
      <div v-if="plansSubTab === 'categories'" class="space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <h3 class="text-xs font-bold text-tg">دسته‌بندی‌های پلن‌ها</h3>
            <span class="text-[10px] text-tg-hint">دسته‌بندی سرویس‌ها جهت نمایش منظم به خریداران در ربات و مینی‌اپ</span>
          </div>
          <button @click="openCreateCategoryModal" class="btn-tg py-1.5 px-3 rounded-xl text-xs font-bold flex items-center gap-1 shadow">
            <span>➕</span>
            <span>افزودن دسته‌بندی</span>
          </button>
        </div>

        <div v-if="categoriesList.length" class="space-y-2">
          <div
            v-for="cat in categoriesList"
            :key="cat.id"
            class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30 text-xs flex justify-between items-center"
          >
            <div class="space-y-1">
              <div class="flex items-center gap-2">
                <span class="text-base">{{ cat.icon || '📦' }}</span>
                <span class="font-bold text-sm">{{ cat.name }}</span>
                <span class="text-[10px] px-2 py-0.5 rounded-full" :class="cat.is_active ? 'bg-emerald-500/15 text-emerald-400' : 'bg-gray-700 text-tg-hint'">
                  {{ cat.is_active ? 'فعال' : 'غیرفعال' }}
                </span>
                <span class="text-[10px] text-tg-hint font-mono bg-tg px-2 py-0.5 rounded-lg">
                  {{ cat.plans_count || 0 }} پلن مرتبط
                </span>
              </div>
              <p v-if="cat.description" class="text-[10px] text-tg-hint">{{ cat.description }}</p>
            </div>

            <div class="flex items-center gap-1.5">
              <button
                @click="openEditCategoryModal(cat)"
                class="p-2 bg-blue-500/20 text-blue-300 rounded-xl text-xs hover:bg-blue-500/30"
                title="ویرایش"
              >
                ✏️
              </button>
              <button
                @click="handleDeleteCategory(cat.id)"
                class="p-2 bg-rose-500/20 text-rose-300 rounded-xl text-xs hover:bg-rose-500/30"
                title="حذف"
              >
                🗑
              </button>
            </div>
          </div>
        </div>
        <div v-else class="text-center py-8 bg-tg-sec/40 rounded-xl border border-dashed border-gray-700/30 text-xs text-tg-hint">
          دسته‌بندی ثبت نشده است. پلن‌ها در دسته‌بندی پیش‌فرض نمایش داده می‌شوند.
        </div>
      </div>

      <!-- 2.3 Volume Packs List -->
      <div v-if="plansSubTab === 'volume'" class="space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <h3 class="text-xs font-bold text-tg">بسته‌های حجم اضافه (Volume Packs)</h3>
            <span class="text-[10px] text-tg-hint">خریداران می‌توانند برای سرویس فعال خود حجم اضافه بخرند</span>
          </div>
          <button @click="openCreateVolumePackModal" class="btn-tg py-1.5 px-3 rounded-xl text-xs font-bold flex items-center gap-1 shadow">
            <span>➕</span>
            <span>افزودن بسته حجم</span>
          </button>
        </div>

        <div v-if="volumePacksList.length" class="space-y-2">
          <div
            v-for="pack in volumePacksList"
            :key="pack.id"
            class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30 text-xs flex justify-between items-center"
          >
            <div>
              <div class="flex items-center gap-2">
                <span class="font-bold text-sm">{{ pack.volume_gb }} گیگابایت اضافه</span>
                <span class="text-[10px] px-2 py-0.5 rounded-full" :class="pack.is_active ? 'bg-emerald-500/15 text-emerald-400' : 'bg-gray-700 text-tg-hint'">
                  {{ pack.is_active ? 'فعال' : 'غیرفعال' }}
                </span>
                <span class="text-[10px] text-tg-hint">اعتبار: {{ pack.duration_days }} روز</span>
              </div>
              <div class="text-emerald-400 font-bold text-xs pt-1">
                {{ Number(pack.price).toLocaleString('fa-IR') }} تومان
              </div>
            </div>

            <div class="flex items-center gap-1.5">
              <button
                @click="handleToggleVolumePack(pack.id)"
                class="p-2 rounded-xl text-xs transition"
                :class="pack.is_active ? 'bg-amber-500/20 text-amber-300' : 'bg-emerald-500/20 text-emerald-300'"
                :title="pack.is_active ? 'غیرفعال‌سازی' : 'فعال‌سازی'"
              >
                {{ pack.is_active ? 'خاموش' : 'روشن' }}
              </button>
              <button
                @click="openEditVolumePackModal(pack)"
                class="p-2 bg-blue-500/20 text-blue-300 rounded-xl text-xs hover:bg-blue-500/30"
                title="ویرایش"
              >
                ✏️
              </button>
              <button
                @click="handleDeleteVolumePack(pack.id)"
                class="p-2 bg-rose-500/20 text-rose-300 rounded-xl text-xs hover:bg-rose-500/30"
                title="حذف"
              >
                🗑
              </button>
            </div>
          </div>
        </div>
        <div v-else class="text-center py-8 bg-tg-sec/40 rounded-xl border border-dashed border-gray-700/30 text-xs text-tg-hint">
          بسته حجم اضافه‌ای تعریف نشده است.
        </div>
      </div>
    </div>

    <!-- ==================== Tab: Free Trial (تست رایگان) ==================== -->
    <div v-if="activeTab === 'trial'" class="space-y-4 text-xs">
      <!-- Trial Stats Card -->
      <div class="grid grid-cols-3 gap-2">
        <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30 text-center">
          <span class="text-tg-hint text-[10px] block">کل اکانت‌های تست اهدا شده</span>
          <span class="text-base font-bold text-tg mt-1 block">{{ Number(trialStats.total_trials || 0).toLocaleString('fa-IR') }}</span>
        </div>
        <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30 text-center">
          <span class="text-tg-hint text-[10px] block">تست‌های فعال فعلی</span>
          <span class="text-base font-bold text-emerald-400 mt-1 block">{{ Number(trialStats.active_trials || 0).toLocaleString('fa-IR') }}</span>
        </div>
        <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30 text-center">
          <span class="text-tg-hint text-[10px] block">تست‌های منقضی شده</span>
          <span class="text-base font-bold text-amber-400 mt-1 block">{{ Number(trialStats.expired_trials || 0).toLocaleString('fa-IR') }}</span>
        </div>
      </div>

      <!-- Main Trial Settings Card -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center border-b border-gray-700/30 pb-2">
          <div class="flex items-center gap-2">
            <span class="text-xl">🎁</span>
            <div>
              <h4 class="font-bold text-sm text-tg">تنظیمات سرویس تست رایگان (Free Trial)</h4>
              <span class="text-[10px] text-tg-hint">اهدای اشتراک موقت به کاربران جهت بررسی کیفیت بدون نیاز به پرداخت</span>
            </div>
          </div>
          <button
            @click="trialSettings.enabled = !trialSettings.enabled"
            class="px-3 py-1.5 rounded-xl font-bold transition shadow"
            :class="trialSettings.enabled ? 'bg-emerald-600 text-white' : 'bg-gray-700 text-tg-hint'"
          >
            {{ trialSettings.enabled ? 'تست رایگان فعال ✓' : 'غیرفعال' }}
          </button>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">حجم هدیه (گیگابایت):</label>
            <input
              type="number"
              step="0.5"
              v-model.number="trialSettings.volume_gb"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-center"
            />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">مدت زمان اعتبار (روز):</label>
            <input
              type="number"
              v-model.number="trialSettings.days"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-center"
            />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">محدودیت کاربر (IP Limit):</label>
            <input
              type="number"
              v-model.number="trialSettings.ip_limit"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-center"
            />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">دوره انتظار مجدد (روز):</label>
            <input
              type="number"
              v-model.number="trialSettings.cooldown_days"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-center"
            />
            <span class="text-[8px] text-tg-hint block mt-0.5">0 یعنی فقط یکبار در طول عمر کاربر</span>
          </div>
        </div>

        <div>
          <label class="block text-[10px] text-tg-hint mb-0.5">گروه سنائی اختصاصی تست (3x-ui Group Name):</label>
          <input
            type="text"
            list="xuiGroupsList"
            v-model="trialSettings.group_name"
            placeholder="مثلاً Trial یا خالی جهت استفاده از پیش‌فرض"
            class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs"
          />
        </div>

        <!-- CRM Follow-up settings -->
        <div class="p-3 bg-tg rounded-xl border border-gray-700/30 space-y-2">
          <div class="flex items-center justify-between">
            <div>
              <span class="font-bold block">ارسال خودکار پیام پیگیری تست (CRM Follow-up)</span>
              <span class="text-[10px] text-tg-hint">ارسال پیام پیشنهاد خرید و تخفیف پس از انقضای تست رایگان</span>
            </div>
            <button
              @click="trialSettings.followup_enabled = !trialSettings.followup_enabled"
              class="px-2.5 py-1 rounded-lg font-bold text-[10px] transition"
              :class="trialSettings.followup_enabled ? 'bg-emerald-600 text-white' : 'bg-gray-700 text-tg-hint'"
            >
              {{ trialSettings.followup_enabled ? 'فعال ✓' : 'غیرفعال' }}
            </button>
          </div>
          <div v-if="trialSettings.followup_enabled" class="flex items-center gap-2 pt-1">
            <span class="text-[10px] text-tg-hint">تاخیر ارسال پیام پیگیری:</span>
            <input
              type="number"
              v-model.number="trialSettings.followup_delay_hours"
              class="w-20 bg-tg-sec border border-gray-700/40 rounded-lg px-2 py-1 text-center font-mono text-xs"
            />
            <span class="text-[10px] text-tg-hint">ساعت پس از انقضای تست</span>
          </div>
        </div>

        <button
          @click="handleSaveTrialSettings"
          :disabled="savingTrialSettings"
          class="w-full btn-tg font-bold py-2.5 rounded-xl text-xs transition shadow"
        >
          {{ savingTrialSettings ? 'در حال ذخیره‌سازی...' : 'ذخیره تنظیمات تست رایگان 💾' }}
        </button>
      </div>

      <!-- Trial Inbound Routing Card -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <h4 class="font-bold text-sm text-tg">مسیریابی اینباندهای تست رایگان (Inbounds Routing)</h4>
            <span class="text-[10px] text-tg-hint">انتخاب اینباندهایی که اکانت تست در آنها ساخته شود (اگر هیچکدام انتخاب نشود، در همه ساخته می‌شود)</span>
          </div>
          <button
            @click="handleResetTrialInbounds"
            class="px-3 py-1 bg-amber-500/20 text-amber-300 rounded-xl text-xs hover:bg-amber-500/30 transition"
          >
            بازنشانی به همه 🔄
          </button>
        </div>

        <div v-if="trialInbounds.length" class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div
            v-for="inb in trialInbounds"
            :key="inb.id"
            class="p-2.5 rounded-xl border flex items-center justify-between transition cursor-pointer"
            :class="inb.selected ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-tg border-gray-700/30 opacity-70'"
            @click="handleToggleTrialInbound(inb.id)"
          >
            <div>
              <span class="font-bold block">{{ inb.tag || ('اینباند #' + inb.id) }}</span>
              <span class="text-[10px] text-tg-hint font-mono">{{ inb.protocol }} : {{ inb.port }}</span>
            </div>
            <span
              class="px-2.5 py-1 rounded-lg text-[10px] font-bold"
              :class="inb.selected ? 'bg-emerald-600 text-white' : 'bg-gray-700 text-tg-hint'"
            >
              {{ inb.selected ? 'فعال ✓' : 'خاموش' }}
            </span>
          </div>
        </div>
        <div v-else class="text-center py-4 text-tg-hint text-[10px]">
          در حال حاضر اینباندی از پنل دریافت نشده است یا ارتباط برقرار نیست.
        </div>
      </div>

      <!-- Trial Overrides Card -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <h4 class="font-bold text-sm text-tg">استثناهای کاربری تست (Trial Overrides)</h4>
            <span class="text-[10px] text-tg-hint">تعیین حجم یا مدت زمان تست اختصاصی برای کاربران یا تسترها</span>
          </div>
          <button
            @click="openAddTrialOverrideModal"
            class="btn-tg py-1.5 px-3 rounded-xl text-xs font-bold flex items-center gap-1 shadow"
          >
            <span>➕</span>
            <span>افزودن کاربر خاص</span>
          </button>
        </div>

        <div v-if="trialOverrides.length" class="space-y-1.5">
          <div
            v-for="ov in trialOverrides"
            :key="ov.user_id"
            class="bg-tg p-2.5 rounded-xl border border-gray-700/30 flex justify-between items-center text-xs"
          >
            <div>
              <div class="flex items-center gap-2">
                <span class="font-bold font-mono">کاربر: {{ ov.user_id }}</span>
                <span class="text-emerald-400 font-bold font-mono">{{ ov.volume_gb }} GB</span>
                <span class="text-blue-400 font-mono">{{ ov.days }} روز</span>
                <span class="text-purple-400 font-mono">{{ ov.ip_limit }} کاربره</span>
              </div>
              <span v-if="ov.note" class="text-[10px] text-tg-hint block mt-0.5">یادداشت: {{ ov.note }}</span>
            </div>
            <button
              @click="handleDeleteTrialOverride(ov.user_id)"
              class="p-1.5 bg-rose-500/20 text-rose-300 rounded-lg hover:bg-rose-500/30 transition"
              title="حذف استثنا"
            >
              🗑
            </button>
          </div>
        </div>
        <div v-else class="text-center py-4 text-tg-hint text-[10px]">
          هیچ استثنای کاربری ثبت نشده است. برای همه کاربران از تنظیمات عمومی استفاده می‌شود.
        </div>
      </div>
    </div>
<!-- ==================== Tab: Sanaei 3x-ui & Groups ==================== -->
    <div v-if="activeTab === 'xui'" class="space-y-3 text-xs">
      <!-- Sanaei Groups Box -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <h4 class="font-bold text-sm text-tg">👥 گروه‌های پنل سنائی (Sanaei Groups)</h4>
            <span class="text-[10px] text-tg-hint">دسته‌بندی خودکار کلاینت‌ها و اختصاص به گروه‌های 3x-ui</span>
          </div>
          <button
            @click="handleReconcileGroups"
            :disabled="loadingXui"
            class="btn-tg py-1.5 px-3 rounded-xl font-bold shadow text-xs flex items-center gap-1"
          >
            <span>🔄</span>
            <span>{{ loadingXui ? 'در حال همگام‌سازی...' : 'همگام‌سازی کلاینت‌ها با گروه‌ها' }}</span>
          </button>
        </div>

        <div v-if="xuiGroups.length" class="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
          <div
            v-for="g in xuiGroups"
            :key="g.name"
            class="bg-tg p-2.5 rounded-xl border border-gray-700/30 flex justify-between items-center"
          >
            <span class="font-bold font-mono text-sm text-blue-400">{{ g.name }}</span>
            <span v-if="g.id" class="text-[10px] text-tg-hint font-mono">#{{ g.id }}</span>
          </div>
        </div>
        <div v-else class="text-center py-4 text-tg-hint text-[10px] bg-tg rounded-xl">
          گروهی دریافت نشد یا ارتباط با پنل برقرار نیست.
        </div>
      </div>

      <!-- Diagnostic Test Box -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <h4 class="font-bold text-sm text-tg">🧪 تست سلامت اتصال API سنائی (Diagnostic)</h4>
            <span class="text-[10px] text-tg-hint">بررسی دسترسی توکن، اینباندها و کلاینت‌ها بدون تغییر اطلاعات</span>
          </div>
          <button
            @click="handleRunXuiDiag"
            :disabled="runningDiag"
            class="bg-blue-600 hover:bg-blue-500 text-white font-bold py-1.5 px-3 rounded-xl shadow text-xs transition"
          >
            {{ runningDiag ? 'در حال بررسی...' : 'اجرای تست اتصال 🔎' }}
          </button>
        </div>

        <div v-if="xuiDiagResult" class="bg-black/50 p-3 rounded-xl border border-gray-700/40 font-mono text-[11px] whitespace-pre-wrap text-emerald-400">
          {{ xuiDiagResult }}
        </div>
      </div>

      <!-- Domain Migration Box -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <h4 class="font-bold text-sm text-tg">🔄 تعویض کلی دامنه (Domain Migration)</h4>
        <span class="text-[10px] text-tg-hint block">جایگزینی دامنه قدیمی با دامنه جدید در تنظیمات ربات، ساب، خوش‌آمدگویی و فایل .env</span>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">دامنه یا هاست قدیمی:</label>
            <input
              type="text"
              v-model="domainForm.old_domain"
              placeholder="old-domain.com"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-left"
              dir="ltr"
            />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">دامنه یا هاست جدید:</label>
            <input
              type="text"
              v-model="domainForm.new_domain"
              placeholder="new-domain.com"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-left"
              dir="ltr"
            />
          </div>
        </div>

        <button
          @click="handleReplaceDomain"
          :disabled="replacingDomain || !domainForm.old_domain || !domainForm.new_domain"
          class="w-full btn-tg font-bold py-2 rounded-xl text-xs transition shadow"
        >
          {{ replacingDomain ? 'در حال اعمال تغییرات...' : 'اعمال تعویض دامنه در کل سیستم 🔄' }}
        </button>
      </div>

      <!-- Delete Client directly from panel -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-rose-500/20 space-y-3">
        <h4 class="font-bold text-sm text-rose-400">🔌 حذف مستقیم اشتراک از پنل سنائی</h4>
        <span class="text-[10px] text-tg-hint block">حذف کامل اشتراک یک کاربر (با ایمیل کلاینت) مستقیماً از روی پنل 3x-ui</span>

        <div class="flex gap-2">
          <input
            type="text"
            v-model="deleteClientEmail"
            placeholder="ایمیل کلاینت در پنل، مثلا: sp_123456789_1"
            class="flex-1 bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-left"
            dir="ltr"
          />
          <button
            @click="handleDeleteClient"
            :disabled="deletingClient || !deleteClientEmail.trim()"
            class="bg-rose-600 hover:bg-rose-500 text-white font-bold py-2 px-4 rounded-xl text-xs transition shadow"
          >
            {{ deletingClient ? 'در حال حذف...' : 'حذف از پنل 🗑' }}
          </button>
        </div>
      </div>
    </div>

    
    <!-- ==================== Tab: CRM & Claims (CRM و احراز اتصال) ==================== -->
    <div v-if="activeTab === 'crm'" class="space-y-4 text-xs">
      <!-- CRM Settings Card -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <h4 class="font-bold text-sm text-tg">📈 تنظیمات CRM و ثبت نام سرویس‌ها</h4>

        <div class="space-y-2">
          <div class="flex items-center justify-between p-2.5 bg-tg rounded-xl border border-gray-700/30">
            <div>
              <span class="font-bold block">نظرسنجی منبع آشنایی خریداران</span>
              <span class="text-[10px] text-tg-hint">پرسش از کاربران پس از خرید برای تشخیص کانال‌های بازاریابی موثر</span>
            </div>
            <button
              @click="crmSettings.survey_enabled = !crmSettings.survey_enabled"
              class="px-3 py-1.5 rounded-xl font-bold transition"
              :class="crmSettings.survey_enabled ? 'bg-emerald-600 text-white shadow' : 'bg-gray-700 text-tg-hint'"
            >
              {{ crmSettings.survey_enabled ? 'فعال ✓' : 'غیرفعال' }}
            </button>
          </div>

          <div class="flex items-center justify-between p-2.5 bg-tg rounded-xl border border-gray-700/30">
            <div>
              <span class="font-bold block">تغییر نام دلخواه سرویس توسط کاربر</span>
              <span class="text-[10px] text-tg-hint">کاربر بتواند نام نمایشی سرویس خود را در بات تغییر دهد</span>
            </div>
            <button
              @click="crmSettings.custom_name_enabled = !crmSettings.custom_name_enabled"
              class="px-3 py-1.5 rounded-xl font-bold transition"
              :class="crmSettings.custom_name_enabled ? 'bg-emerald-600 text-white shadow' : 'bg-gray-700 text-tg-hint'"
            >
              {{ crmSettings.custom_name_enabled ? 'مجاز ✓' : 'غیرفعال' }}
            </button>
          </div>

          <div class="flex items-center justify-between p-2.5 bg-tg rounded-xl border border-gray-700/30">
            <div>
              <span class="font-bold block">اتصال سرویس‌های قبلی و قدیمی سنائی (Existing Service Claiming)</span>
              <span class="text-[10px] text-tg-hint">امکان ثبت درخواست اتصال کانفیگ‌های قبلی به پنل کاربری بات جهت تمدید</span>
            </div>
            <button
              @click="crmSettings.existing_service_enabled = !crmSettings.existing_service_enabled"
              class="px-3 py-1.5 rounded-xl font-bold transition"
              :class="crmSettings.existing_service_enabled ? 'bg-emerald-600 text-white shadow' : 'bg-gray-700 text-tg-hint'"
            >
              {{ crmSettings.existing_service_enabled ? 'فعال ✓' : 'غیرفعال' }}
            </button>
          </div>
        </div>

        <button
          @click="handleSaveCrmSettings"
          :disabled="savingCrm"
          class="w-full btn-tg font-bold py-2 rounded-xl text-xs transition shadow"
        >
          {{ savingCrm ? 'در حال ذخیره‌سازی...' : 'ذخیره تنظیمات CRM 💾' }}
        </button>
      </div>

      <!-- Pending Service Claims -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <h4 class="font-bold text-sm text-tg">درخواست‌های اتصال سرویس در انتظار بررسی</h4>
            <span class="text-[10px] text-tg-hint">کاربرانی که می‌خواهند سرویس قبلی خود را به این ربات متصل کنند</span>
          </div>
          <span class="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full font-bold">
            {{ pendingClaims.length }} در انتظار
          </span>
        </div>

        <div v-if="pendingClaims.length" class="space-y-2">
          <div
            v-for="cl in pendingClaims"
            :key="cl.id"
            class="bg-tg p-3 rounded-xl border border-gray-700/30 space-y-2"
          >
            <div class="flex justify-between items-start">
              <div>
                <span class="font-bold block">شناسه/ایمیل: <code class="text-blue-400">{{ cl.sub_id }}</code></span>
                <span class="text-[10px] text-tg-hint">کاربر: <code>{{ cl.user_id }}</code> | درخواست #{{ cl.id }}</span>
              </div>
              <span class="text-[10px] text-tg-hint font-mono">{{ cl.created_at }}</span>
            </div>
            <div class="flex items-center gap-2 pt-1">
              <button
                @click="handleApproveClaim(cl.id)"
                class="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-1.5 rounded-xl transition shadow"
              >
                تایید اتصال سرویس ✓
              </button>
              <button
                @click="openRejectClaimModal(cl.id)"
                class="px-3 bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 font-semibold py-1.5 rounded-xl transition"
              >
                رد ✕
              </button>
            </div>
          </div>
        </div>
        <div v-else class="text-center py-6 text-tg-hint text-[10px]">
          درخواست اتصال سرویسی در انتظار بررسی نیست.
        </div>
      </div>

      <!-- Survey Breakdown Card -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <h4 class="font-bold text-sm text-tg">📊 آمار کانال‌های جذب مشتری (نتایج نظرسنجی)</h4>
        <div v-if="surveyStats.length" class="space-y-2">
          <div
            v-for="s in surveyStats"
            :key="s.source"
            class="bg-tg p-2.5 rounded-xl border border-gray-700/30 flex justify-between items-center"
          >
            <span class="font-bold">{{ s.source }}</span>
            <span class="font-mono font-bold text-emerald-400">{{ s.count }} کاربر</span>
          </div>
        </div>
        <div v-else class="text-center py-4 text-tg-hint text-[10px]">
          هنوز پاسخی در نظرسنجی ثبت نشده است.
        </div>
      </div>
    </div>

    <!-- ==================== Tab: Connection Guides (راهنمای اتصال) ==================== -->
    <div v-if="activeTab === 'guides'" class="space-y-4 text-xs">
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center border-b border-gray-700/30 pb-2">
          <div>
            <h4 class="font-bold text-sm text-tg">📲 مدیریت آموزش و راهنمای اتصال</h4>
            <span class="text-[10px] text-tg-hint">ارسال راهنمای اتصال برنامه‌ها (V2rayNG, Streisand, v2rayN و...) به کاربران</span>
          </div>
          <button
            @click="handleToggleGuides"
            class="px-3 py-1.5 rounded-xl font-bold transition shadow"
            :class="guidesEnabled ? 'bg-emerald-600 text-white' : 'bg-gray-700 text-tg-hint'"
          >
            {{ guidesEnabled ? 'بخش راهنما فعال ✓' : 'غیرفعال' }}
          </button>
        </div>

        <!-- Platform filter pills -->
        <div class="flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          <button
            v-for="plt in guidePlatforms"
            :key="plt.id"
            @click="activeGuidePlatform = plt.id"
            class="py-1.5 px-3 rounded-xl transition font-medium flex items-center gap-1"
            :class="activeGuidePlatform === plt.id ? 'bg-tg-button text-white font-bold' : 'bg-tg text-tg-hint hover:text-tg'"
          >
            <span>{{ plt.icon }}</span>
            <span>{{ plt.label }}</span>
          </button>
        </div>

        <div class="flex justify-between items-center pt-2">
          <span class="font-bold text-tg">مطالب راهنمای پلتفرم انتخاب شده:</span>
          <div class="flex items-center gap-2">
            <button
              @click="handlePromptGuideBot(activeGuidePlatform)"
              :disabled="promptingBot"
              class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold flex items-center gap-1 shadow transition"
              title="ارسال پیام به چت تلگرام مدیر تا مطلب راهنما را مستقیماً در چت ربات ارسال فرمایید"
            >
              <span>📲</span>
              <span>{{ promptingBot ? 'در حال ارسال...' : 'ارسال در تلگرام' }}</span>
            </button>
            <button
              @click="openAddGuideModal"
              class="btn-tg py-1.5 px-3 rounded-xl text-xs font-bold flex items-center gap-1 shadow"
            >
              <span>➕</span>
              <span>افزودن در وب</span>
            </button>
          </div>
        </div>

        <div v-if="telegramBotUrl" class="p-2.5 bg-blue-500/10 border border-blue-500/30 rounded-xl flex items-center justify-between text-xs">
          <span class="text-blue-300">دستور به تلگرام شما ارسال شد. لطفاً به چت ربات بروید و متن یا تصویر/ویدیو را ارسال کنید:</span>
          <a :href="telegramBotUrl" target="_blank" class="px-2.5 py-1 bg-blue-600 text-white rounded-lg font-bold text-[11px] hover:bg-blue-500">
            باز کردن ربات در تلگرام ↗️
          </a>
        </div>

        <div v-if="filteredGuides.length" class="space-y-2">
          <div
            v-for="item in filteredGuides"
            :key="item.id"
            class="bg-tg p-3.5 rounded-xl border border-gray-700/30 space-y-2"
          >
            <div class="flex justify-between items-start gap-2">
              <div class="flex-1 min-w-0 space-y-2">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-bold text-sm">{{ item.title || (item.body ? (item.body.length > 50 ? item.body.slice(0, 50) + '...' : item.body) : ('آموزش #' + item.id)) }}</span>
                  <span v-if="item.app_name" class="text-[10px] px-2 py-0.5 rounded-lg bg-blue-500/20 text-blue-300 border border-blue-500/30 font-semibold">
                    برنامه: {{ item.app_name }}
                  </span>
                  <span class="text-[9px] px-2 py-0.5 rounded-full font-mono" :class="item.media_type === 'VIDEO' ? 'bg-purple-500/20 text-purple-300' : (item.media_type === 'PHOTO' ? 'bg-blue-500/20 text-blue-300' : 'bg-gray-700/30 text-tg-hint')">
                    {{ item.media_type }}
                  </span>
                </div>

                <!-- Media Preview in Admin Panel -->
                <div v-if="item.media_file_id && item.media_type === 'PHOTO'" class="rounded-xl overflow-hidden border border-gray-700/40 bg-black/40 max-w-sm">
                  <img :src="getGuideMediaUrl(item)" class="w-full max-h-48 object-contain" loading="lazy"/>
                </div>
                <div v-else-if="item.media_file_id && item.media_type === 'VIDEO'" class="rounded-xl overflow-hidden border border-gray-700/40 bg-black/60 max-w-sm">
                  <video controls playsinline preload="metadata" :src="getGuideMediaUrl(item)" class="w-full max-h-48 rounded-xl"></video>
                </div>

                <p v-if="item.body" class="text-[11px] text-tg-hint whitespace-pre-wrap leading-relaxed">{{ item.body }}</p>

                <!-- Attached Telegram File ID Box (Fixed Layout) -->
                <div v-if="item.media_file_id" class="p-2 bg-gray-800/60 rounded-xl border border-gray-700/40 space-y-1.5 max-w-sm">
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-[10px] text-amber-400 font-semibold flex items-center gap-1">
                      📎 فایل پیوست:
                    </span>
                    <button
                      type="button"
                      @click.stop="copyFileId(item.media_file_id)"
                      class="text-[9px] px-2 py-0.5 bg-gray-700/70 hover:bg-gray-600 text-gray-200 rounded-md transition flex items-center gap-1"
                    >
                      <span>{{ copiedFileId === item.media_file_id ? '✓ کپی شد' : '📋 کپی ID' }}</span>
                    </button>
                  </div>
                  <div class="font-mono text-[9px] text-gray-300 break-all bg-black/40 px-2 py-1.5 rounded-lg border border-gray-800/80 dir-ltr select-all">
                    {{ item.media_file_id }}
                  </div>
                </div>
              </div>

              <button
                @click="handleDeleteGuide(item.id)"
                class="p-2 bg-rose-500/20 text-rose-300 rounded-xl hover:bg-rose-500/30 transition shrink-0"
                title="حذف"
              >
                🗑
              </button>
            </div>
          </div>
        </div>
        <div v-else class="text-center py-6 text-tg-hint text-[10px]">
          هنوز مطلبی برای این پلتفرم ثبت نشده است. با دکمه افزودن اولین آموزش را ایجاد کنید.
        </div>
      </div>
    </div>
<!-- ==================== Tab: Rewards & Discounts ==================== -->
    <div v-if="activeTab === 'rewards'" class="space-y-3 text-xs">
      <!-- Cashback Box -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <h4 class="font-bold text-sm text-tg">💰 سیستم کش‌بک (بازگشت وجه به کیف پول)</h4>
            <span class="text-[10px] text-tg-hint">درصدی از مبلغ هر خرید موفق به صورت خودکار به کیف پول خریدار واریز می‌شود</span>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <div class="flex items-center gap-1.5 flex-1">
            <input
              type="number"
              step="0.5"
              min="0"
              max="100"
              v-model.number="rewardsData.cashback_percent"
              class="w-24 bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-center"
            />
            <span class="text-sm font-bold text-tg">% درصد پاداش</span>
          </div>
          <button
            @click="handleSaveCashback"
            :disabled="savingCashback"
            class="btn-tg py-2 px-4 rounded-xl font-bold text-xs shadow"
          >
            {{ savingCashback ? 'ذخیره...' : 'ذخیره درصد کش‌بک 💾' }}
          </button>
        </div>
      </div>

      <!-- Discount Codes Box -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <h4 class="font-bold text-sm text-tg">🎟 کدهای تخفیف</h4>
            <span class="text-[10px] text-tg-hint">تعداد فعال: {{ rewardsData.discount_codes.length }}</span>
          </div>
          <button
            @click="showDiscountModal = true"
            class="btn-tg py-1.5 px-3 rounded-xl font-bold shadow text-xs flex items-center gap-1"
          >
            <span>➕</span>
            <span>کد تخفیف جدید</span>
          </button>
        </div>

        <div v-if="rewardsData.discount_codes.length" class="space-y-1.5 max-h-60 overflow-y-auto">
          <div
            v-for="d in rewardsData.discount_codes"
            :key="d.code"
            class="bg-tg p-2.5 rounded-xl border border-gray-700/30 flex justify-between items-center"
          >
            <div>
              <span class="font-mono font-bold text-sm text-blue-400 block">{{ d.code }}</span>
              <span class="text-[10px] text-tg-hint">
                {{ d.discount_type === 'PERCENT' ? (d.value + '% درصد') : (Number(d.value).toLocaleString('fa-IR') + ' تومان') }}
                <span v-if="d.max_uses > 0"> | ظرفیت: {{ d.max_uses }}</span>
                <span v-if="d.min_purchase > 0"> | حداقل خرید: {{ Number(d.min_purchase).toLocaleString('fa-IR') }}</span>
              </span>
            </div>
            <button
              @click="handleDeleteDiscount(d.code)"
              class="p-1.5 bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 rounded-lg text-xs"
              title="حذف کد"
            >
              🗑
            </button>
          </div>
        </div>
        <div v-else class="text-center py-4 text-tg-hint text-[10px] bg-tg rounded-xl">
          کد تخفیفی تعریف نشده است.
        </div>
      </div>

      <!-- Gift Codes Box -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <h4 class="font-bold text-sm text-tg">🎁 کدهای شارژ هدیه کیف پول</h4>
            <span class="text-[10px] text-tg-hint">تعداد فعال: {{ rewardsData.gift_codes.length }}</span>
          </div>
          <button
            @click="showGiftModal = true"
            class="btn-tg py-1.5 px-3 rounded-xl font-bold shadow text-xs flex items-center gap-1"
          >
            <span>➕</span>
            <span>کد هدیه جدید</span>
          </button>
        </div>

        <div v-if="rewardsData.gift_codes.length" class="space-y-1.5 max-h-60 overflow-y-auto">
          <div
            v-for="g in rewardsData.gift_codes"
            :key="g.code"
            class="bg-tg p-2.5 rounded-xl border border-gray-700/30 flex justify-between items-center"
          >
            <div>
              <span class="font-mono font-bold text-sm text-emerald-400 block">{{ g.code }}</span>
              <span class="text-[10px] text-tg-hint">
                مبلغ: {{ Number(g.amount).toLocaleString('fa-IR') }} تومان | سقف استفاده: {{ g.max_uses }}
              </span>
            </div>
            <button
              @click="handleDeleteGift(g.code)"
              class="p-1.5 bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 rounded-lg text-xs"
              title="حذف کد"
            >
              🗑
            </button>
          </div>
        </div>
        <div v-else class="text-center py-4 text-tg-hint text-[10px] bg-tg rounded-xl">
          کد هدیه‌ای تعریف نشده است.
        </div>
      </div>
    </div>

    <!-- ==================== Tab: Affiliate & Referrals ==================== -->
    <div v-if="activeTab === 'affiliate'" class="space-y-3 text-xs">
      <!-- Stats Summary -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
          <span class="text-tg-hint text-[10px] block">کاربران دعوت‌شده</span>
          <span class="text-sm font-bold text-tg mt-0.5 block">{{ Number(affiliateData.total_referrals).toLocaleString('fa-IR') }}</span>
        </div>
        <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
          <span class="text-tg-hint text-[10px] block">تعداد پورسانت‌ها</span>
          <span class="text-sm font-bold text-blue-400 mt-0.5 block">{{ Number(affiliateData.total_commissions_count).toLocaleString('fa-IR') }}</span>
        </div>
        <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
          <span class="text-tg-hint text-[10px] block">مجموع پورسانت‌ها</span>
          <span class="text-sm font-bold text-emerald-400 mt-0.5 block">{{ Number(affiliateData.total_commissions_amount).toLocaleString('fa-IR') }} تومان</span>
        </div>
        <div class="bg-tg-sec p-3 rounded-2xl border border-gray-700/30">
          <span class="text-tg-hint text-[10px] block">مانده کل کیف پول‌ها</span>
          <span class="text-sm font-bold text-amber-400 mt-0.5 block">{{ Number(affiliateData.total_wallet_balance).toLocaleString('fa-IR') }} تومان</span>
        </div>
      </div>

      <!-- Settings Box -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <h4 class="font-bold text-sm text-tg">⚙️ تنظیمات همکاری در فروش (Affiliate)</h4>

        <div class="flex items-center justify-between p-2.5 bg-tg rounded-xl border border-gray-700/30">
          <div>
            <span class="font-bold block">فعال بودن سیستم معرفی و دعوت</span>
            <span class="text-[10px] text-tg-hint">در صورت فعال بودن، کاربران لینک اختصاصی دریافت می‌کنند</span>
          </div>
          <button
            @click="affiliateData.enabled = !affiliateData.enabled"
            class="px-3 py-1.5 rounded-xl text-xs font-bold transition"
            :class="affiliateData.enabled ? 'bg-emerald-600 text-white shadow' : 'bg-rose-600/30 text-rose-300'"
          >
            {{ affiliateData.enabled ? 'فعال ✓' : 'غیرفعال ✕' }}
          </button>
        </div>

        <div>
          <label class="block text-[10px] text-tg-hint mb-1">درصد پورسانت معرف از هر خرید (%):</label>
          <div class="flex gap-2">
            <input
              type="number"
              step="0.5"
              min="0"
              max="100"
              v-model.number="affiliateData.percent"
              class="w-32 bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-center"
            />
            <button
              @click="handleSaveAffiliate"
              :disabled="savingAffiliate"
              class="btn-tg py-2 px-4 rounded-xl font-bold text-xs shadow flex-1"
            >
              {{ savingAffiliate ? 'ذخیره...' : 'ذخیره تنظیمات همکاری 💾' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Top Referrers Leaderboard -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <h4 class="font-bold text-sm text-tg">🏆 ۱۰ معرف برتر سیستم</h4>

        <div v-if="affiliateData.top_referrers.length" class="space-y-1.5">
          <div
            v-for="(r, idx) in affiliateData.top_referrers"
            :key="r.referrer_id"
            class="bg-tg p-2.5 rounded-xl border border-gray-700/30 flex justify-between items-center"
          >
            <div class="flex items-center gap-2">
              <span class="font-bold w-5 text-center text-tg-hint">{{ idx + 1 }}.</span>
              <div>
                <span class="font-mono font-bold block">{{ r.referrer_id }}</span>
                <span class="text-[10px] text-tg-hint">خریداران مستقیم: {{ r.buyers }} نفر</span>
              </div>
            </div>
            <span class="font-bold text-emerald-400 font-mono">{{ Number(r.earned).toLocaleString('fa-IR') }} تومان</span>
          </div>
        </div>
        <div v-else class="text-center py-4 text-tg-hint text-[10px] bg-tg rounded-xl">
          هنوز پورسانتی ثبت نشده است.
        </div>
      </div>
    </div>

    
    <!-- ==================== Tab: Content & Security ==================== -->
    <div v-if="activeTab === 'content'" class="space-y-3 text-xs">
      <!-- Welcome Message & FAQ -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <h4 class="font-bold text-sm text-tg">📝 پیام خوش‌آمدگویی و راهنما</h4>

        <div>
          <label class="block text-[10px] text-tg-hint mb-1">متن پیام شروع ربات (Welcome Text):</label>
          <textarea
            v-model="contentSecurity.welcome_text"
            rows="3"
            class="w-full bg-tg border border-gray-700/40 rounded-xl p-3 text-xs leading-relaxed"
            placeholder="سلام به ربات ما خوش آمدید..."
          ></textarea>
        </div>

        <div>
          <label class="block text-[10px] text-tg-hint mb-1">متن بخش سوالات متداول و راهنما (FAQ Text):</label>
          <textarea
            v-model="contentSecurity.faq_text"
            rows="4"
            class="w-full bg-tg border border-gray-700/40 rounded-xl p-3 text-xs leading-relaxed"
            placeholder="راهنمای خرید و اتصال..."
          ></textarea>
        </div>
      </div>

      <!-- Security & Channel Lock -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <h4 class="font-bold text-sm text-tg">🔐 امنیت و قفل کانال تلگرام</h4>

        <div class="flex items-center justify-between p-2.5 bg-tg rounded-xl border border-gray-700/30">
          <div>
            <span class="font-bold block">احراز هویت با شماره تماس</span>
            <span class="text-[10px] text-tg-hint">کاربران قبل از دسترسی باید شماره موبایل تلگرام خود را ارسال کنند</span>
          </div>
          <button
            @click="contentSecurity.phone_verification_required = !contentSecurity.phone_verification_required"
            class="px-3 py-1.5 rounded-xl text-xs font-bold transition"
            :class="contentSecurity.phone_verification_required ? 'bg-emerald-600 text-white shadow' : 'bg-gray-700 text-tg-hint'"
          >
            {{ contentSecurity.phone_verification_required ? 'اجباری ✓' : 'اختیاری' }}
          </button>
        </div>

        <div class="flex items-center justify-between p-2.5 bg-tg rounded-xl border border-gray-700/30">
          <div>
            <span class="font-bold block">عضویت اجباری در کانال (Channel Lock)</span>
            <span class="text-[10px] text-tg-hint">ربات تا قبل از عضویت در کانال قفل خواهد بود (ربات باید ادمین کانال باشد)</span>
          </div>
          <button
            @click="contentSecurity.membership_required = !contentSecurity.membership_required"
            class="px-3 py-1.5 rounded-xl text-xs font-bold transition"
            :class="contentSecurity.membership_required ? 'bg-emerald-600 text-white shadow' : 'bg-gray-700 text-tg-hint'"
          >
            {{ contentSecurity.membership_required ? 'فعال ✓' : 'غیرفعال' }}
          </button>
        </div>

        <div v-if="contentSecurity.membership_required" class="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">شناسه یا آیدی کانال:</label>
            <input
              type="text"
              v-model="contentSecurity.required_channel"
              placeholder="@MyChannel یا -1001234567890"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-left"
              dir="ltr"
            />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">لینک عضویت کانال:</label>
            <input
              type="text"
              v-model="contentSecurity.required_channel_url"
              placeholder="https://t.me/MyChannel"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-left"
              dir="ltr"
            />
          </div>
        </div>
      </div>

      <!-- Service Username Generation Mode & Periodic Check -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <h4 class="font-bold text-sm text-tg">⚙️ الگوی نام کاربری سرویس‌ها و بررسی دوره‌ای</h4>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">الگوی نام کاربری در سنائی:</label>
            <select
              v-model="contentSecurity.service_username_mode"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs"
            >
              <option value="telegram_tx">شناسه تلگرام و تراکنش (یکتا و منظم)</option>
              <option value="random">نام کاربری تصادفی و ناشناس (Random UUID)</option>
            </select>
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">فاصله زمانی بررسی وضعیت سرویس‌ها (دقیقه):</label>
            <input
              type="number"
              min="5"
              max="1440"
              v-model.number="contentSecurity.service_notification_interval"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-center"
            />
          </div>
        </div>

        <div class="pt-1 flex items-center justify-between border-t border-gray-700/30">
          <span class="text-[10px] text-tg-hint">می‌توانید بررسی حجم و انقضا را فوراً اجرا کنید:</span>
          <button
            @click="handleCheckNotificationsNow"
            :disabled="checkingNotifications"
            class="px-3 py-1.5 bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 rounded-xl font-bold transition text-xs flex items-center gap-1"
          >
            <span>🚀</span>
            <span>{{ checkingNotifications ? 'در حال بررسی...' : 'بررسی اعلان‌ها همین الان' }}</span>
          </button>
        </div>
      </div>

      <!-- Service Notifications -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <h4 class="font-bold text-sm text-tg">🔔 اعلان‌های هوشمند سرویس</h4>

        <div class="flex items-center justify-between p-2.5 bg-tg rounded-xl border border-gray-700/30">
          <div>
            <span class="font-bold block">ارسال خودکار پیام هشدار پایان حجم / زمان</span>
            <span class="text-[10px] text-tg-hint">هشدار به کاربران تلگرام قبل از قطعی سرویس جهت تمدید سریع</span>
          </div>
          <button
            @click="contentSecurity.service_notifications_enabled = !contentSecurity.service_notifications_enabled"
            class="px-3 py-1.5 rounded-xl text-xs font-bold transition"
            :class="contentSecurity.service_notifications_enabled ? 'bg-emerald-600 text-white shadow' : 'bg-gray-700 text-tg-hint'"
          >
            {{ contentSecurity.service_notifications_enabled ? 'فعال ✓' : 'غیرفعال' }}
          </button>
        </div>

        <div v-if="contentSecurity.service_notifications_enabled" class="grid grid-cols-2 gap-2 pt-1">
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">درصد هشدار مصرف حجم:</label>
            <input
              type="number"
              min="50"
              max="99"
              v-model.number="contentSecurity.service_volume_warning_percent"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-center"
            />
            <span class="text-[9px] text-tg-hint block mt-0.5">مثلاً ۹۰ یعنی با مصرف ۹۰٪ حجم، پیام هشدار ارسال می‌شود.</span>
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">هشدار انقضا (ساعت قبل از پایان):</label>
            <input
              type="number"
              min="1"
              max="168"
              v-model.number="contentSecurity.service_expiry_warning_hours"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-center"
            />
            <span class="text-[9px] text-tg-hint block mt-0.5">مثلاً ۲۴ یعنی یک روز قبل از انقضا به کاربر پیام می‌دهد.</span>
          </div>
        </div>
      </div>

      <button
        @click="handleSaveContentSecurity"
        :disabled="savingContentSec"
        class="w-full btn-tg font-bold py-2.5 rounded-xl text-xs transition shadow"
      >
        {{ savingContentSec ? 'در حال ذخیره‌سازی...' : 'ذخیره متن‌ها، اعلان‌ها و امنیت 💾' }}
      </button>
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
          <div class="col-span-full pt-1">
            <label class="block text-[10px] text-tg-hint mb-1">تصویر کارت یا بارکد QR پرداخت (آدرس تصویر یا File ID):</label>
            <input type="text" v-model="paymentsConfig.card.card_photo" dir="ltr" placeholder="https://example.com/card.jpg یا File ID تلگرام" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
            <div v-if="paymentsConfig.card.card_photo" class="mt-2 flex items-center gap-3">
              <img :src="paymentsConfig.card.card_photo" class="w-20 h-20 object-cover rounded-xl border border-gray-700/40" @error="$event.target.style.display='none'" />
              <span class="text-[10px] text-tg-hint">پیش‌نمایش تصویر کارت یا بارکد پرداخت</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. Telegram Stars Payment -->
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
            <label class="block text-[10px] text-tg-hint mb-1">کد مرچنت زیبال (Merchant ID):</label>
            <input type="text" v-model="paymentsConfig.zibal.merchant" dir="ltr" placeholder="zibal" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
          </div>
          <div class="flex items-center gap-2">
            <input type="checkbox" id="zibalSandbox" v-model="paymentsConfig.zibal.sandbox" class="rounded" />
            <label for="zibalSandbox" class="text-[10px] text-tg-hint">حالت تست زیبال (Sandbox / آزمایشگاهی)</label>
          </div>
        </div>
      </div>

      <!-- 4. Zarinpal Gateway -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3 text-xs">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-2">
            <span class="text-xl">🟡</span>
            <div>
              <h4 class="font-bold text-sm text-tg">درگاه پرداخت زرین‌پال (ZarinPal)</h4>
              <span class="text-[10px] text-tg-hint">درگاه پرداخت اینترنتی شاپرک</span>
            </div>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="paymentsConfig.zarinpal.enabled" class="sr-only peer" />
            <div class="w-9 h-5 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-yellow-500"></div>
          </label>
        </div>

        <div v-if="paymentsConfig.zarinpal.enabled" class="space-y-2 pt-2 border-t border-gray-700/30">
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">کد مرچنت زرین‌پال (Merchant ID):</label>
            <input type="text" v-model="paymentsConfig.zarinpal.merchant" dir="ltr" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
          </div>
          <div class="flex items-center gap-2">
            <input type="checkbox" id="zarinSandbox" v-model="paymentsConfig.zarinpal.sandbox" class="rounded" />
            <label for="zarinSandbox" class="text-[10px] text-tg-hint">حالت تست زرین‌پال (Sandbox / آزمایشگاهی)</label>
          </div>
        </div>
      </div>

      <button
        @click="handleSavePayments"
        :disabled="savingPayments"
        class="w-full btn-tg font-bold py-2.5 rounded-xl text-xs transition shadow"
      >
        {{ savingPayments ? 'در حال ذخیره‌سازی...' : 'ذخیره تنظیمات روش‌های پرداخت 💾' }}
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

      <!-- Snapshot Section -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <div>
            <h4 class="font-bold text-sm text-tg">📸 اسنپ‌شات وضعیت و دیتابیس پنل</h4>
            <span class="text-[10px] text-tg-hint">مشاهده گزارش جامع و ارسال مستقیم فایل اسنپ‌شات به چت تلگرام مدیر</span>
          </div>
          <div class="flex gap-2">
            <button
              @click="handleGetSnapshot"
              :disabled="loadingSnapshot"
              class="px-3 py-1.5 bg-blue-500/20 text-blue-300 rounded-xl font-bold hover:bg-blue-500/30 transition text-xs"
            >
              {{ loadingSnapshot ? 'در حال دریافت...' : 'مشاهده آمار 📊' }}
            </button>
            <button
              @click="handleSendSnapshot"
              :disabled="sendingSnapshot"
              class="btn-tg py-1.5 px-3 rounded-xl font-bold shadow text-xs"
            >
              {{ sendingSnapshot ? 'در حال ارسال...' : 'ارسال به تلگرام 📤' }}
            </button>
          </div>
        </div>

        <div v-if="snapshotInfo" class="p-3 bg-tg rounded-xl border border-gray-700/30 space-y-1 font-mono text-[10px]">
          <div class="flex justify-between"><span>نسخه سیستم:</span><span class="text-sky-400 font-bold">v{{ snapshotInfo.version }}</span></div>
          <div class="flex justify-between"><span>زمان اسنپ‌شات:</span><span>{{ snapshotInfo.timestamp }}</span></div>
          <div class="flex justify-between"><span>کل کاربران:</span><span>{{ snapshotInfo.users?.total_users }}</span></div>
          <div class="flex justify-between"><span>کل سفارش‌ها:</span><span>{{ snapshotInfo.orders?.total_orders }}</span></div>
        </div>
      </div>
    </div>

    <!-- ==================== Tab: Audit Log (لاگ حسابرسی) ==================== -->
    <div v-if="activeTab === 'audit'" class="space-y-4 text-xs">
      <!-- Audit Settings -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center border-b border-gray-700/30 pb-2">
          <div>
            <h4 class="font-bold text-sm text-tg">🧾 ثبت وقایع و لاگ حسابرسی (Audit Trail)</h4>
            <span class="text-[10px] text-tg-hint">ثبت کلیه عملیات‌های حساس مالی، مدیریتی و ساخت سرویس‌ها</span>
          </div>
          <button
            @click="auditSettings.enabled = !auditSettings.enabled"
            class="px-3 py-1.5 rounded-xl font-bold transition shadow"
            :class="auditSettings.enabled ? 'bg-emerald-600 text-white' : 'bg-gray-700 text-tg-hint'"
          >
            {{ auditSettings.enabled ? 'لاگ حسابرسی فعال ✓' : 'غیرفعال' }}
          </button>
        </div>

        <div v-if="auditSettings.enabled" class="space-y-2">
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">شناسه کانال یا گروه تلگرام حسابرسی (Audit Chat ID):</label>
            <input
              type="text"
              v-model="auditSettings.audit_chat_id"
              placeholder="-1001234567890 یا خالی"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-left"
              dir="ltr"
            />
            <span class="text-[9px] text-tg-hint block mt-0.5">
              در صورت تنظیم شناسه کانال، پیام‌های حسابرسی مستقیماً به آن کانال ارسال می‌شوند (ربات باید در کانال ادمین باشد).
            </span>
          </div>
        </div>

        <button
          @click="handleSaveAuditSettings"
          :disabled="savingAudit"
          class="w-full btn-tg font-bold py-2 rounded-xl text-xs transition shadow"
        >
          {{ savingAudit ? 'در حال ذخیره‌سازی...' : 'ذخیره تنظیمات حسابرسی 💾' }}
        </button>
      </div>

      <!-- Events List -->
      <div class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <h4 class="font-bold text-sm text-tg">آخرین رویدادهای سیستمی</h4>
          <button @click="loadAuditEvents" class="text-xs text-tg-button hover:underline">
            🔄 بروزرسانی
          </button>
        </div>

        <div v-if="auditEvents.length" class="space-y-1.5 max-h-96 overflow-y-auto">
          <div
            v-for="ev in auditEvents"
            :key="ev.id"
            class="bg-tg p-2.5 rounded-xl border border-gray-700/30 text-xs space-y-1"
          >
            <div class="flex justify-between items-center">
              <span class="font-bold font-mono text-emerald-400">{{ ev.event_type }}</span>
              <span class="text-[10px] text-tg-hint font-mono">{{ ev.created_at }}</span>
            </div>
            <div class="text-[10px] text-tg-hint flex gap-3">
              <span v-if="ev.actor_id">مجری: <code>{{ ev.actor_id }}</code></span>
              <span v-if="ev.target_id">هدف: <code>{{ ev.target_id }}</code></span>
            </div>
            <p v-if="ev.details" class="text-[10px] text-tg/80 font-mono bg-tg-sec/50 p-1.5 rounded-lg">
              {{ ev.details }}
            </p>
          </div>
        </div>
        <div v-else class="text-center py-6 text-tg-hint text-[10px]">
          رویدادی ثبت نشده است.
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
    <div v-if="activeTab === 'branding'" class="bg-tg-sec p-4 rounded-2xl border border-gray-700/30 space-y-4 text-xs">
      <div class="flex items-center gap-2">
        <span class="text-lg">🎨</span>
        <div>
          <span class="font-bold block text-sm">نام، عنوان و منوی مشتریان</span>
          <span class="text-[10px] text-tg-hint">شخصی‌سازی ظاهر وب‌اپلیکیشن و دکمه‌های منوی ربات تلگرام</span>
        </div>
      </div>

      <div class="space-y-1">
        <label class="block text-xs font-medium text-tg">عنوان و نام وب‌اپ (Web UI Title):</label>
        <input
          type="text"
          v-model="uiTitle"
          placeholder="مثال: فروشگاه من"
          class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-tg-button font-medium"
        />
      </div>

      <!-- Customer Menu Visibility Toggles -->
      <div class="space-y-2 pt-2 border-t border-gray-700/30">
        <label class="block text-xs font-semibold text-tg">دکمه‌های منوی ربات تلگرام مشتریان (کیبورد اصلی):</label>
        <span class="text-[10px] text-tg-hint block">انتخاب کنید کدام دکمه‌ها در منوی ربات به مشتریان نمایش داده شوند</span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
          <button
            v-for="(label, key) in customerMenuLabels"
            :key="key"
            type="button"
            @click="customerMenu[key] = !customerMenu[key]"
            class="p-2 rounded-xl text-xs font-medium border transition flex items-center justify-between"
            :class="customerMenu[key] ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300' : 'bg-tg border-gray-700/40 text-tg-hint'"
          >
            <span>{{ label }}</span>
            <span class="text-[10px]">{{ customerMenu[key] ? '✓' : '✕' }}</span>
          </button>
        </div>
      </div>

      <button
        @click="handleSaveBranding"
        :disabled="savingBranding || !uiTitle.trim()"
        class="w-full btn-tg font-bold py-2.5 rounded-xl text-xs transition active:scale-95 shadow"
      >
        {{ savingBranding ? 'در حال ذخیره‌سازی...' : 'ذخیره تنظیمات عنوان و منو 💾' }}
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
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">دسته‌بندی پلن:</label>
              <select v-model="planForm.category_id" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs">
                <option :value="null">پیش‌فرض (عمومی)</option>
                <option v-for="cat in categoriesList" :key="cat.id" :value="cat.id">
                  {{ cat.icon || '📦' }} {{ cat.name }}
                </option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">نام گروه سنائی (Group Name):</label>
              <input
                type="text"
                list="xuiGroupsList"
                v-model="planForm.group_name"
                placeholder="مثلاً Customers یا VIP"
                class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs font-mono"
              />
              <datalist id="xuiGroupsList">
                <option v-for="g in xuiGroups" :key="g.name" :value="g.name" />
              </datalist>
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

    <!-- Modal 6: Create Discount Code -->
    <div v-if="showDiscountModal" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-sm w-full p-4 space-y-3 text-xs shadow-2xl">
        <h4 class="font-bold text-sm">ایجاد کد تخفیف جدید</h4>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">کد تخفیف (انگلیسی):</label>
          <input type="text" v-model="discountForm.code" placeholder="OFF30" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-left uppercase" dir="ltr" />
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">نوع تخفیف:</label>
            <select v-model="discountForm.discount_type" class="w-full bg-tg border border-gray-700/40 rounded-xl px-2 py-2 text-xs">
              <option value="PERCENT">درصدی (%)</option>
              <option value="FIXED">مبلغ ثابت (تومان)</option>
            </select>
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">مقدار تخفیف:</label>
            <input type="number" v-model.number="discountForm.value" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">حداقل خرید (تومان):</label>
            <input type="number" v-model.number="discountForm.min_purchase" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">سقف استفاده (0=نامحدود):</label>
            <input type="number" v-model.number="discountForm.max_uses" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
          </div>
        </div>
        <div class="flex gap-2 pt-1">
          <button @click="handleCreateDiscount" class="flex-1 btn-tg py-2 rounded-xl font-bold shadow">
            ثبت کد تخفیف 💾
          </button>
          <button @click="showDiscountModal = false" class="px-4 bg-gray-700/40 text-tg-hint rounded-xl">
            انصراف
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 7: Create Gift Code -->
    <div v-if="showGiftModal" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-sm w-full p-4 space-y-3 text-xs shadow-2xl">
        <h4 class="font-bold text-sm">ایجاد کد هدیه کیف پول</h4>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">کد هدیه (انگلیسی):</label>
          <input type="text" v-model="giftForm.code" placeholder="GIFT50" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs text-left uppercase" dir="ltr" />
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">مبلغ هدیه (تومان):</label>
            <input type="number" v-model.number="giftForm.amount" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-1">ظرفیت استفاده:</label>
            <input type="number" v-model.number="giftForm.max_uses" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
          </div>
        </div>
        <div class="flex gap-2 pt-1">
          <button @click="handleCreateGift" class="flex-1 btn-tg py-2 rounded-xl font-bold shadow">
            ثبت کد هدیه 🎁
          </button>
          <button @click="showGiftModal = false" class="px-4 bg-gray-700/40 text-tg-hint rounded-xl">
            انصراف
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 8: Plan Inbounds Selector Modal (NEW) -->
    <div v-if="showPlanInboundsModal" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-md w-full p-4 space-y-3 text-xs shadow-2xl">
        <div class="flex justify-between items-center border-b border-gray-700/30 pb-2">
          <div>
            <h4 class="font-bold text-sm">مسیریابی اینباندهای پلن: {{ selectedPlanForInbounds?.name }}</h4>
            <span class="text-[10px] text-tg-hint">کلاینت‌های این پلن روی اینباندهای فعال ساخته خواهند شد</span>
          </div>
          <button @click="showPlanInboundsModal = false" class="text-tg-hint hover:text-tg text-sm">✕</button>
        </div>

        <div v-if="loadingPlanInbounds" class="text-center py-6 text-tg-hint">
          در حال دریافت اینباندها...
        </div>
        <div v-else-if="planInboundsList.length" class="space-y-2 max-h-72 overflow-y-auto">
          <div
            v-for="inb in planInboundsList"
            :key="inb.id"
            class="p-2.5 rounded-xl border flex items-center justify-between transition cursor-pointer"
            :class="inb.selected ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-tg border-gray-700/30 opacity-70'"
            @click="handleTogglePlanInbound(inb.id)"
          >
            <div>
              <span class="font-bold block">{{ inb.tag || ('اینباند #' + inb.id) }}</span>
              <span class="text-[10px] text-tg-hint font-mono">{{ inb.protocol }} : {{ inb.port }}</span>
            </div>
            <span
              class="px-2.5 py-1 rounded-lg text-[10px] font-bold"
              :class="inb.selected ? 'bg-emerald-600 text-white' : 'bg-gray-700 text-tg-hint'"
            >
              {{ inb.selected ? 'فعال ✓' : 'خاموش' }}
            </span>
          </div>
        </div>
        <div v-else class="text-center py-6 text-tg-hint">
          اینباندی در پنل یافت نشد.
        </div>

        <div class="flex gap-2 pt-2 border-t border-gray-700/30">
          <button @click="handleResetPlanInbounds" class="px-3 bg-amber-500/20 text-amber-300 rounded-xl font-bold">
            بازنشانی به همه 🔄
          </button>
          <button @click="showPlanInboundsModal = false" class="flex-1 btn-tg py-2 rounded-xl font-bold">
            بستن
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 9: Category Create/Edit Modal (NEW) -->
    <div v-if="showCategoryModal" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-sm w-full p-4 space-y-3 text-xs shadow-2xl">
        <div class="flex justify-between items-center border-b border-gray-700/30 pb-2">
          <h4 class="font-bold text-sm">{{ isEditingCategory ? 'ویرایش دسته‌بندی' : 'افزودن دسته‌بندی جدید' }}</h4>
          <button @click="showCategoryModal = false" class="text-tg-hint hover:text-tg text-sm">✕</button>
        </div>

        <div class="space-y-2">
          <div class="grid grid-cols-4 gap-2">
            <div class="col-span-1">
              <label class="block text-[10px] text-tg-hint mb-0.5">آیکون:</label>
              <input type="text" v-model="categoryForm.icon" placeholder="📦" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-center text-sm" />
            </div>
            <div class="col-span-3">
              <label class="block text-[10px] text-tg-hint mb-0.5">نام دسته‌بندی:</label>
              <input type="text" v-model="categoryForm.name" placeholder="مثلاً: سرویس‌های گیمینگ یا VIP" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2" />
            </div>
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">توضیحات کوتاه:</label>
            <input type="text" v-model="categoryForm.description" placeholder="سرویس‌های اختصاصی با پینگ پایین" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2" />
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">ترتیب نمایش:</label>
              <input type="number" v-model.number="categoryForm.sort_order" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
            </div>
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">وضعیت:</label>
              <select v-model.number="categoryForm.is_active" class="w-full bg-tg border border-gray-700/40 rounded-xl px-2 py-2">
                <option :value="1">فعال</option>
                <option :value="0">غیرفعال</option>
              </select>
            </div>
          </div>
        </div>

        <div class="flex gap-2 pt-2">
          <button @click="handleSaveCategory" class="flex-1 btn-tg py-2 rounded-xl font-bold shadow">
            ذخیره دسته‌بندی 💾
          </button>
          <button @click="showCategoryModal = false" class="px-4 bg-gray-700/40 text-tg-hint rounded-xl">
            انصراف
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 10: Volume Pack Create/Edit Modal (NEW) -->
    <div v-if="showVolumePackModal" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-sm w-full p-4 space-y-3 text-xs shadow-2xl">
        <div class="flex justify-between items-center border-b border-gray-700/30 pb-2">
          <h4 class="font-bold text-sm">{{ isEditingVolumePack ? 'ویرایش بسته حجم اضافه' : 'افزودن بسته حجم اضافه' }}</h4>
          <button @click="showVolumePackModal = false" class="text-tg-hint hover:text-tg text-sm">✕</button>
        </div>

        <div class="space-y-2">
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">حجم بسته (گیگابایت):</label>
              <input type="number" step="0.5" v-model.number="volumePackForm.volume_gb" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
            </div>
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">قیمت (تومان):</label>
              <input type="number" v-model.number="volumePackForm.price" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">مدت اعتبار افزوده (روز):</label>
              <input type="number" v-model.number="volumePackForm.duration_days" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
            </div>
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">وضعیت:</label>
              <select v-model.number="volumePackForm.is_active" class="w-full bg-tg border border-gray-700/40 rounded-xl px-2 py-2">
                <option :value="1">فعال</option>
                <option :value="0">غیرفعال</option>
              </select>
            </div>
          </div>
        </div>

        <div class="flex gap-2 pt-2">
          <button @click="handleSaveVolumePack" class="flex-1 btn-tg py-2 rounded-xl font-bold shadow">
            ذخیره بسته 💾
          </button>
          <button @click="showVolumePackModal = false" class="px-4 bg-gray-700/40 text-tg-hint rounded-xl">
            انصراف
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 11: Add Trial Override Modal (NEW) -->
    <div v-if="showTrialOverrideModal" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-sm w-full p-4 space-y-3 text-xs shadow-2xl">
        <h4 class="font-bold text-sm">افزودن استثنای تست رایگان</h4>
        <div class="space-y-2">
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">شناسه عددی تلگرام کاربر:</label>
            <input type="number" v-model.number="trialOverrideForm.user_id" placeholder="12345678" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
          </div>
          <div class="grid grid-cols-3 gap-2">
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">حجم (GB):</label>
              <input type="number" step="0.5" v-model.number="trialOverrideForm.volume_gb" class="w-full bg-tg border border-gray-700/40 rounded-xl px-2 py-2 font-mono text-center" />
            </div>
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">مدت (روز):</label>
              <input type="number" v-model.number="trialOverrideForm.days" class="w-full bg-tg border border-gray-700/40 rounded-xl px-2 py-2 font-mono text-center" />
            </div>
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">کاربر (IP):</label>
              <input type="number" v-model.number="trialOverrideForm.ip_limit" class="w-full bg-tg border border-gray-700/40 rounded-xl px-2 py-2 font-mono text-center" />
            </div>
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">یادداشت / علت اعطا:</label>
            <input type="text" v-model="trialOverrideForm.note" placeholder="مثلاً: تست یوتیوبر یا همکار" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2" />
          </div>
        </div>

        <div class="flex gap-2 pt-2">
          <button @click="handleSaveTrialOverride" class="flex-1 btn-tg py-2 rounded-xl font-bold shadow">
            ثبت استثنا 💾
          </button>
          <button @click="showTrialOverrideModal = false" class="px-4 bg-gray-700/40 text-tg-hint rounded-xl">
            انصراف
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 12: Reject Service Claim Modal (NEW) -->
    <div v-if="showRejectClaimModal" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-sm w-full p-4 space-y-3 text-xs shadow-2xl">
        <h4 class="font-bold text-sm text-rose-400">رد درخواست اتصال سرویس</h4>
        <div>
          <label class="block text-[10px] text-tg-hint mb-1">دلیل رد درخواست (برای کاربر ارسال می‌شود):</label>
          <textarea
            v-model="rejectClaimReason"
            rows="3"
            class="w-full bg-tg border border-gray-700/40 rounded-xl p-3 text-xs leading-relaxed"
            placeholder="اشتراک در پنل یافت نشد یا معتبر نیست."
          ></textarea>
        </div>
        <div class="flex gap-2 pt-1">
          <button @click="handleConfirmRejectClaim" class="flex-1 bg-rose-600 hover:bg-rose-500 text-white py-2 rounded-xl font-bold shadow">
            رد قطعی درخواست ✕
          </button>
          <button @click="showRejectClaimModal = false" class="px-4 bg-gray-700/40 text-tg-hint rounded-xl">
            انصراف
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 13: Add Guide Item Modal (NEW) -->
    <div v-if="showAddGuideModal" class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div class="bg-tg-sec border border-gray-700/50 rounded-2xl max-w-md w-full p-4 space-y-3 text-xs shadow-2xl max-h-[90vh] overflow-y-auto">
        <div class="flex justify-between items-center border-b border-gray-700/30 pb-2">
          <h4 class="font-bold text-sm">افزودن آموزش راهنمای اتصال</h4>
          <button @click="showAddGuideModal = false" class="text-tg-hint hover:text-tg text-sm">✕</button>
        </div>

        <div class="p-3 bg-blue-500/10 border border-blue-500/30 rounded-xl space-y-2">
          <div class="flex items-center justify-between">
            <span class="font-bold text-blue-300">📲 ارسال مطلب مستقیم در چت ربات تلگرام:</span>
            <span class="text-[10px] bg-blue-600/30 text-blue-300 px-2 py-0.5 rounded-full font-bold">پیشنهادی</span>
          </div>
          <p class="text-[10px] text-tg-hint leading-relaxed">
            به جای تایپ دستی، می‌توانید درخواست را به ربات بفرستید تا مطلب کامل (شامل متن بلند، تصویر و ویدیو همراه کپشن) را مستقیماً از تلگرام به عنوان راهنما دریافت و ذخیره کند.
          </p>
          <button
            @click="handlePromptGuideBot(guideForm.platform, guideForm.app_name)"
            :disabled="promptingBot"
            class="w-full bg-blue-600 hover:bg-blue-500 text-white py-2 rounded-xl font-bold text-xs shadow transition flex items-center justify-center gap-1.5"
          >
            <span>🚀</span>
            <span>{{ promptingBot ? 'در حال ارسال پیام به ربات...' : 'ارسال درخواست ثبت راهنما به تلگرام من' }}</span>
          </button>
        </div>

        <div class="flex items-center gap-2 pt-1">
          <div class="h-px bg-gray-700/40 flex-1"></div>
          <span class="text-[10px] text-tg-hint">یا ثبت دستی در پنل وب:</span>
          <div class="h-px bg-gray-700/40 flex-1"></div>
        </div>

        <div class="space-y-2">
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">سیستم عامل / پلتفرم:</label>
              <select v-model="guideForm.platform" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs">
                <option value="android">اندروید (Android) 📱</option>
                <option value="ios">آیفون و آیپد (iOS) 🍏</option>
                <option value="windows">ویندوز (Windows) 💻</option>
                <option value="macos">مک (macOS) 🖥</option>
                <option value="linux">لینوکس (Linux) 🐧</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] text-tg-hint mb-0.5">نوع محتوا:</label>
              <select v-model="guideForm.media_type" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs font-mono">
                <option value="TEXT">متن ساده (TEXT)</option>
                <option value="PHOTO">تصویر آموزشی (PHOTO)</option>
                <option value="VIDEO">ویدیو آموزشی (VIDEO)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between items-center mb-0.5">
              <label class="block text-[10px] text-tg-hint">نام نرم‌افزار / اپلیکیشن:</label>
              <span class="text-[9px] text-blue-400">پیشنهادها را انتخاب یا دستی بنویسید</span>
            </div>
            <input
              type="text"
              v-model="guideForm.app_name"
              placeholder="مثلاً: V2RayNG یا Streisand یا Hiddify"
              class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 text-xs font-medium"
            />
            <div v-if="platformSuggestedApps[guideForm.platform]" class="flex gap-1.5 flex-wrap mt-1.5">
              <button
                v-for="sApp in platformSuggestedApps[guideForm.platform]"
                :key="sApp"
                type="button"
                @click="guideForm.app_name = sApp"
                class="text-[10px] px-2 py-0.5 rounded-lg border transition"
                :class="guideForm.app_name === sApp ? 'bg-blue-600 text-white border-blue-500' : 'bg-gray-800 text-gray-300 border-gray-700 hover:border-gray-500'"
              >
                {{ sApp }}
              </button>
            </div>
          </div>

          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">عنوان آموزش:</label>
            <input type="text" v-model="guideForm.title" placeholder="مثلاً: راهنمای نصب نرم‌افزار v2rayNG" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2" />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">متن توضیحات و آموزش:</label>
            <textarea
              v-model="guideForm.body"
              rows="4"
              class="w-full bg-tg border border-gray-700/40 rounded-xl p-3 text-xs leading-relaxed"
              placeholder="لینک دانلود برنامه و مراحل اتصال..."
            ></textarea>
          </div>
          <div v-if="guideForm.media_type !== 'TEXT'">
            <label class="block text-[10px] text-tg-hint mb-0.5">شناسه فایل تلگرام (File ID) یا لینک فایل:</label>
            <input type="text" v-model="guideForm.media_file_id" dir="ltr" placeholder="AgACAgIAAxkBA..." class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono text-xs" />
          </div>
          <div>
            <label class="block text-[10px] text-tg-hint mb-0.5">ترتیب نمایش:</label>
            <input type="number" v-model.number="guideForm.sort_order" class="w-full bg-tg border border-gray-700/40 rounded-xl px-3 py-2 font-mono" />
          </div>
        </div>

        <div class="flex gap-2 pt-2">
          <button @click="handleSaveGuide" class="flex-1 btn-tg py-2 rounded-xl font-bold shadow">
            ثبت آموزش 💾
          </button>
          <button @click="showAddGuideModal = false" class="px-4 bg-gray-700/40 text-tg-hint rounded-xl">
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
  saveAdminBranding,
  getAdminXuiGroups,
  reconcileAdminXuiGroups,
  testAdminXui,
  replaceAdminDomain,
  deleteAdminPanelClient,
  getAdminRewards,
  saveAdminCashback,
  createAdminDiscount,
  deleteAdminDiscount,
  createAdminGift,
  deleteAdminGift,
  getAdminAffiliate,
  saveAdminAffiliate,
  getAdminContentSecurity,
  saveAdminContentSecurity,
  // NEW API methods
  getAdminPlanInbounds,
  toggleAdminPlanInbound,
  resetAdminPlanInbounds,
  getAdminCategories,
  createAdminCategory,
  updateAdminCategory,
  deleteAdminCategory,
  getAdminVolumePacks,
  createAdminVolumePack,
  updateAdminVolumePack,
  deleteAdminVolumePack,
  toggleAdminVolumePack,
  getAdminTrialSettings,
  saveAdminTrialSettings,
  toggleAdminTrialInbound,
  resetAdminTrialInbounds,
  getAdminTrialOverrides,
  saveAdminTrialOverride,
  deleteAdminTrialOverride,
  getAdminCrm,
  saveAdminCrmSettings,
  approveAdminClaim,
  rejectAdminClaim,
  getAdminGuides,
  createAdminGuide,
  deleteAdminGuide,
  toggleAdminGuides,
  promptAdminGuideBot,
  getAdminAudit,
  saveAdminAuditSettings,
  getAdminSnapshot,
  sendAdminSnapshot,
  checkAdminNotifications
} from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const appVersion = computed(() => auth.appVersion || stats.value?.version || '26.1.0')

// Navigation Tabs
const activeTab = ref('orders')
const tabs = computed(() => [
  { id: 'orders', label: 'سفارش‌ها', icon: '📑', badge: orders.value.length || null },
  { id: 'plans', label: 'پلان‌ها و دسته‌ها', icon: '📦' },
  { id: 'trial', label: 'تست رایگان', icon: '🎁', badge: trialSettings.value.enabled ? 'فعال' : null },
  { id: 'crm', label: 'CRM و اتصال', icon: '📈', badge: pendingClaims.value.length || null },
  { id: 'guides', label: 'راهنمای اتصال', icon: '📲' },
  { id: 'xui', label: 'سنائی و گروه‌ها', icon: '🌐' },
  { id: 'rewards', label: 'تخفیف و پاداش', icon: '🎟' },
  { id: 'affiliate', label: 'همکاری در فروش', icon: '🤝' },
  { id: 'content', label: 'متن‌ها و امنیت', icon: '📝' },
  { id: 'builder', label: 'پلن‌ساز', icon: '🛠' },
  { id: 'users', label: 'کاربران', icon: '👥' },
  { id: 'blacklist', label: 'مسدودی', icon: '🚫' },
  { id: 'admins', label: 'مدیران', icon: '👑' },
  { id: 'payments', label: 'پرداخت و استارز', icon: '💳' },
  { id: 'backups', label: 'بکاپ و عملیات', icon: '💾' },
  { id: 'audit', label: 'لاگ حسابرسی', icon: '🧾' },
  { id: 'server', label: 'وضعیت سرور', icon: '🖥' },
  { id: 'broadcast', label: 'پیام همگانی', icon: '📢' },
  { id: 'branding', label: 'عنوان و منو', icon: '🎨' },
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

// Plans & Sub-tabs
const plansSubTab = ref('catalog')
const plansList = ref([])
const categoriesList = ref([])
const volumePacksList = ref([])
const showPlanModal = ref(false)
const isEditingPlan = ref(false)
const planForm = ref({ id: null, name: '', price: 100000, days: 30, volume_gb: 0, ip_limit: 1, active: 1, sort_order: 100, group_name: '', category_id: null })

// Categories Modal & Form
const showCategoryModal = ref(false)
const isEditingCategory = ref(false)
const categoryForm = ref({ id: null, name: '', icon: '📦', description: '', sort_order: 100, is_active: 1 })

// Volume Packs Modal & Form
const showVolumePackModal = ref(false)
const isEditingVolumePack = ref(false)
const volumePackForm = ref({ id: null, volume_gb: 10, price: 50000, duration_days: 30, is_active: 1 })

// Plan Inbounds Selector Modal
const showPlanInboundsModal = ref(false)
const selectedPlanForInbounds = ref(null)
const planInboundsList = ref([])
const loadingPlanInbounds = ref(false)

// Free Trial Management
const trialSettings = ref({
  enabled: false,
  volume_gb: 1.0,
  days: 1,
  ip_limit: 1,
  cooldown_days: 0,
  group_name: '',
  followup_enabled: true,
  followup_delay_hours: 2
})
const trialStats = ref({ total_trials: 0, active_trials: 0, expired_trials: 0 })
const trialInbounds = ref([])
const trialOverrides = ref([])
const savingTrialSettings = ref(false)
const showTrialOverrideModal = ref(false)
const trialOverrideForm = ref({ user_id: null, volume_gb: 2, days: 3, ip_limit: 1, note: '' })

// CRM & Claims
const crmSettings = ref({ survey_enabled: true, custom_name_enabled: true, existing_service_enabled: true })
const surveyStats = ref([])
const pendingClaims = ref([])
const savingCrm = ref(false)
const showRejectClaimModal = ref(false)
const rejectingClaimId = ref(null)
const rejectClaimReason = ref('')

// Connection Guides
const guidesEnabled = ref(true)
const guidesList = ref([])
const activeGuidePlatform = ref('android')
const guidePlatforms = [
  { id: 'android', label: 'اندروید', icon: '📱' },
  { id: 'ios', label: 'آیفون/آیپد', icon: '🍏' },
  { id: 'windows', label: 'ویندوز', icon: '💻' },
  { id: 'macos', label: 'مک', icon: '🖥' },
  { id: 'linux', label: 'لینوکس', icon: '🐧' },
]
const filteredGuides = computed(() =>
  guidesList.value.filter(g => (g.platform || '').toLowerCase() === activeGuidePlatform.value.toLowerCase())
)
const platformSuggestedApps = {
  android: ['V2RayNG', 'Hiddify', 'V2Box', 'Clash Meta', 'Sing-box', 'Happ'],
  ios: ['Streisand', 'V2Box', 'FoXray', 'Shadowrocket', 'Sing-box'],
  windows: ['v2rayN', 'Hiddify', 'Clash Verge', 'NekoRay', 'Happ'],
  macos: ['V2rayU', 'FoXray', 'Clash Verge', 'Hiddify', 'Happ'],
  linux: ['v2rayA', 'NekoRay', 'Clash Verge', 'Happ'],
}
const showAddGuideModal = ref(false)
const guideForm = ref({ platform: 'android', app_name: 'V2RayNG', title: '', body: '', media_type: 'TEXT', media_file_id: '', sort_order: 100 })
const promptingBot = ref(false)
const telegramBotUrl = ref('')

// Audit Log
const auditSettings = ref({ enabled: false, audit_chat_id: '' })
const auditEvents = ref([])
const savingAudit = ref(false)

// Snapshot
const snapshotInfo = ref(null)
const loadingSnapshot = ref(false)
const sendingSnapshot = ref(false)

// Notifications check
const checkingNotifications = ref(false)

// Customer Menu
const customerMenu = ref({
  buy: true,
  account: true,
  trial: true,
  affiliate: true,
  guide: true,
  faq: true,
  rewards: true,
  support: true
})
const customerMenuLabels = {
  buy: '🛍 خرید و مشاهده پلان‌ها',
  account: '👤 حساب و سرویس‌های من',
  trial: '🎁 دریافت تست رایگان',
  affiliate: '🤝 همکاری در فروش',
  guide: '📲 راهنمای اتصال',
  faq: '📚 راهنما و سوالات',
  rewards: '🎟 کد هدیه / تخفیف',
  support: '📞 پشتیبانی'
}

// Sanaei 3x-ui & Groups
const xuiGroups = ref([])
const loadingXui = ref(false)
const xuiDiagResult = ref('')
const runningDiag = ref(false)
const domainForm = ref({ old_domain: '', new_domain: '' })
const replacingDomain = ref(false)
const deleteClientEmail = ref('')
const deletingClient = ref(false)

// Rewards & Discounts
const rewardsData = ref({ cashback_percent: 0, discount_codes: [], gift_codes: [] })
const savingCashback = ref(false)
const showDiscountModal = ref(false)
const discountForm = ref({ code: '', discount_type: 'PERCENT', value: 10, min_purchase: 0, max_uses: 0, per_user_limit: 1 })
const showGiftModal = ref(false)
const giftForm = ref({ code: '', amount: 10000, max_uses: 1 })

// Affiliate & Referrals
const affiliateData = ref({
  enabled: true,
  percent: 10,
  total_referrals: 0,
  total_commissions_count: 0,
  total_commissions_amount: 0,
  total_wallet_balance: 0,
  top_referrers: [],
})
const savingAffiliate = ref(false)

// Content, Security & Notifications
const contentSecurity = ref({
  welcome_text: '',
  faq_text: '',
  phone_verification_required: false,
  membership_required: false,
  required_channel: '',
  required_channel_url: '',
  service_notifications_enabled: true,
  service_volume_warning_percent: 90,
  service_expiry_warning_hours: 24,
  service_username_mode: 'telegram_tx',
  service_notification_interval: 30
})
const savingContentSec = ref(false)

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
  card: { card_number: '', card_holder: '', bank_name: '', card_photo: '' },
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
    const [
      stRes, ordRes, plRes, uRes, bldRes, blRes, admRes, payRes,
      bkRes, srvRes, brRes, xuiRes, rewRes, affRes, csRes,
      catRes, volRes, triRes, crmRes, guiRes, audRes
    ] = await Promise.all([
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
      getAdminBranding().catch(() => ({ data: { webapp_title: '', customer_menu: {} } })),
      getAdminXuiGroups().catch(() => ({ data: { groups: [] } })),
      getAdminRewards().catch(() => ({ data: null })),
      getAdminAffiliate().catch(() => ({ data: null })),
      getAdminContentSecurity().catch(() => ({ data: null })),
      getAdminCategories().catch(() => ({ data: { categories: [] } })),
      getAdminVolumePacks().catch(() => ({ data: { packs: [] } })),
      getAdminTrialSettings().catch(() => ({ data: null })),
      getAdminCrm().catch(() => ({ data: null })),
      getAdminGuides().catch(() => ({ data: null })),
      getAdminAudit().catch(() => ({ data: null })),
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

    if (brRes?.data) {
      uiTitle.value = brRes.data.webapp_title || ''
      if (uiTitle.value) auth.setAppTitle(uiTitle.value)
      if (brRes.data.customer_menu) {
        customerMenu.value = { ...customerMenu.value, ...brRes.data.customer_menu }
      }
    }

    xuiGroups.value = xuiRes.data?.groups || []
    if (rewRes?.data) rewardsData.value = { ...rewardsData.value, ...rewRes.data }
    if (affRes?.data) affiliateData.value = { ...affiliateData.value, ...affRes.data }
    if (csRes?.data) contentSecurity.value = { ...contentSecurity.value, ...csRes.data }

    categoriesList.value = catRes.data?.categories || []
    volumePacksList.value = volRes.data?.packs || []

    if (triRes?.data) {
      trialSettings.value = {
        enabled: !!triRes.data.enabled,
        volume_gb: triRes.data.volume_gb ?? 1.0,
        days: triRes.data.days ?? 1,
        ip_limit: triRes.data.ip_limit ?? 1,
        cooldown_days: triRes.data.cooldown_days ?? 0,
        group_name: triRes.data.group_name || '',
        followup_enabled: triRes.data.followup_enabled ?? true,
        followup_delay_hours: triRes.data.followup_delay_hours ?? 2,
      }
      trialStats.value = triRes.data.stats || { total_trials: 0, active_trials: 0, expired_trials: 0 }
      trialInbounds.value = triRes.data.inbounds || []
    }

    if (crmRes?.data) {
      if (crmRes.data.settings) crmSettings.value = { ...crmSettings.value, ...crmRes.data.settings }
      surveyStats.value = crmRes.data.survey_stats || []
      pendingClaims.value = crmRes.data.pending_claims || []
    }

    if (guiRes?.data) {
      guidesEnabled.value = !!guiRes.data.enabled
      guidesList.value = guiRes.data.items || []
    }

    if (audRes?.data) {
      auditSettings.value = {
        enabled: !!audRes.data.enabled,
        audit_chat_id: audRes.data.audit_chat_id || ''
      }
      auditEvents.value = audRes.data.events || []
    }

    // Load trial overrides
    loadTrialOverrides()

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
  planForm.value = { id: null, name: '', price: 100000, days: 30, volume_gb: 0, ip_limit: 1, active: 1, sort_order: 100, group_name: '', category_id: null }
  showPlanModal.value = true
}

const openEditPlanModal = (plan) => {
  isEditingPlan.value = true
  planForm.value = { ...plan, group_name: plan.group_name || '', category_id: plan.category_id || null }
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

// ─── Plan Inbounds Handlers ──────────────────────────────────────────────────
const openPlanInboundsModal = async (plan) => {
  selectedPlanForInbounds.value = plan
  showPlanInboundsModal.value = true
  loadingPlanInbounds.value = true
  try {
    const res = await getAdminPlanInbounds(plan.id)
    planInboundsList.value = res.data?.inbounds || []
  } catch (err) {
    showNotify('خطا در دریافت اینباندهای پلن', false)
  } finally {
    loadingPlanInbounds.value = false
  }
}

const handleTogglePlanInbound = async (inboundId) => {
  if (!selectedPlanForInbounds.value) return
  try {
    const res = await toggleAdminPlanInbound(selectedPlanForInbounds.value.id, inboundId)
    const target = planInboundsList.value.find(i => i.id === inboundId)
    if (target) target.selected = res.data.selected
    showNotify('وضعیت اینباند برای پلن تغییر یافت.')
  } catch (err) {
    showNotify('خطا در تغییر اینباند', false)
  }
}

const handleResetPlanInbounds = async () => {
  if (!selectedPlanForInbounds.value) return
  try {
    await resetAdminPlanInbounds(selectedPlanForInbounds.value.id)
    planInboundsList.value.forEach(i => i.selected = false)
    showNotify('تمامی اینباندها برای این پلن فعال شدند (حالت پیش‌فرض).')
  } catch (err) {
    showNotify('خطا در بازنشانی اینباندها', false)
  }
}

// ─── Categories Handlers ─────────────────────────────────────────────────────
const getCategoryName = (catId) => {
  if (!catId) return null
  const cat = categoriesList.value.find(c => c.id === catId)
  return cat ? cat.name : null
}

const getCategoryIcon = (catId) => {
  if (!catId) return ''
  const cat = categoriesList.value.find(c => c.id === catId)
  return cat?.icon || '📦'
}

const openCreateCategoryModal = () => {
  isEditingCategory.value = false
  categoryForm.value = { id: null, name: '', icon: '📦', description: '', sort_order: 100, is_active: 1 }
  showCategoryModal.value = true
}

const openEditCategoryModal = (cat) => {
  isEditingCategory.value = true
  categoryForm.value = { ...cat }
  showCategoryModal.value = true
}

const handleSaveCategory = async () => {
  if (!categoryForm.value.name.trim()) return
  try {
    if (isEditingCategory.value) {
      await updateAdminCategory(categoryForm.value.id, categoryForm.value)
      showNotify('دسته‌بندی با موفقیت ویرایش شد.')
    } else {
      await createAdminCategory(categoryForm.value)
      showNotify('دسته‌بندی جدید با موفقیت ایجاد شد.')
    }
    showCategoryModal.value = false
    const res = await getAdminCategories()
    categoriesList.value = res.data?.categories || []
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ذخیره دسته‌بندی', false)
  }
}

const handleDeleteCategory = async (catId) => {
  if (!confirm('آیا از حذف این دسته‌بندی اطمینان دارید؟ پلن‌های مرتبط به حالت بدون دسته‌بندی منتقل می‌شوند.')) return
  try {
    await deleteAdminCategory(catId)
    categoriesList.value = categoriesList.value.filter(c => c.id !== catId)
    showNotify('دسته‌بندی حذف شد.')
  } catch (err) {
    showNotify('خطا در حذف دسته‌بندی', false)
  }
}

// ─── Volume Packs Handlers ───────────────────────────────────────────────────
const openCreateVolumePackModal = () => {
  isEditingVolumePack.value = false
  volumePackForm.value = { id: null, volume_gb: 10, price: 50000, duration_days: 30, is_active: 1 }
  showVolumePackModal.value = true
}

const openEditVolumePackModal = (pack) => {
  isEditingVolumePack.value = true
  volumePackForm.value = { ...pack }
  showVolumePackModal.value = true
}

const handleSaveVolumePack = async () => {
  try {
    if (isEditingVolumePack.value) {
      await updateAdminVolumePack(volumePackForm.value.id, volumePackForm.value)
      showNotify('بسته حجم ویرایش شد.')
    } else {
      await createAdminVolumePack(volumePackForm.value)
      showNotify('بسته حجم جدید ایجاد شد.')
    }
    showVolumePackModal.value = false
    const res = await getAdminVolumePacks()
    volumePacksList.value = res.data?.packs || []
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ذخیره بسته حجم', false)
  }
}

const handleToggleVolumePack = async (packId) => {
  try {
    const res = await toggleAdminVolumePack(packId)
    const target = volumePacksList.value.find(p => p.id === packId)
    if (target) target.is_active = res.data.is_active
    showNotify('وضعیت بسته حجم تغییر یافت.')
  } catch (err) {
    showNotify('خطا در تغییر وضعیت بسته حجم', false)
  }
}

const handleDeleteVolumePack = async (packId) => {
  if (!confirm('آیا از حذف این بسته حجم اطمینان دارید؟')) return
  try {
    await deleteAdminVolumePack(packId)
    volumePacksList.value = volumePacksList.value.filter(p => p.id !== packId)
    showNotify('بسته حجم حذف شد.')
  } catch (err) {
    showNotify('خطا در حذف بسته حجم', false)
  }
}

// ─── Free Trial Handlers ─────────────────────────────────────────────────────
const handleSaveTrialSettings = async () => {
  savingTrialSettings.value = true
  try {
    await saveAdminTrialSettings(trialSettings.value)
    showNotify('تنظیمات تست رایگان با موفقیت ذخیره شد.')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ذخیره تنظیمات تست رایگان', false)
  } finally {
    savingTrialSettings.value = false
  }
}

const handleToggleTrialInbound = async (inboundId) => {
  try {
    const res = await toggleAdminTrialInbound(inboundId)
    const target = trialInbounds.value.find(i => i.id === inboundId)
    if (target) target.selected = res.data.selected
    showNotify('اینباند تست بروزرسانی شد.')
  } catch (err) {
    showNotify('خطا در تغییر اینباند تست', false)
  }
}

const handleResetTrialInbounds = async () => {
  try {
    await resetAdminTrialInbounds()
    trialInbounds.value.forEach(i => i.selected = false)
    showNotify('اینباندهای تست رایگان به همه اینباندها بازنشانی شد.')
  } catch (err) {
    showNotify('خطا در بازنشانی اینباندهای تست', false)
  }
}

const loadTrialOverrides = async () => {
  try {
    const res = await getAdminTrialOverrides()
    trialOverrides.value = res.data?.overrides || []
  } catch (err) {
    console.error('Error loading trial overrides:', err)
  }
}

const openAddTrialOverrideModal = () => {
  trialOverrideForm.value = { user_id: null, volume_gb: 2, days: 3, ip_limit: 1, note: '' }
  showTrialOverrideModal.value = true
}

const handleSaveTrialOverride = async () => {
  if (!trialOverrideForm.value.user_id) return
  try {
    await saveAdminTrialOverride(trialOverrideForm.value)
    showNotify('استثنای تست رایگان کاربر ثبت شد.')
    showTrialOverrideModal.value = false
    loadTrialOverrides()
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ثبت استثنای کاربر', false)
  }
}

const handleDeleteTrialOverride = async (userId) => {
  if (!confirm(`آیا استثنای تست رایگان کاربر ${userId} حذف شود؟`)) return
  try {
    await deleteAdminTrialOverride(userId)
    trialOverrides.value = trialOverrides.value.filter(o => o.user_id !== userId)
    showNotify('استثنای کاربر حذف شد.')
  } catch (err) {
    showNotify('خطا در حذف استثنای کاربر', false)
  }
}

// ─── CRM & Claims Handlers ───────────────────────────────────────────────────
const handleSaveCrmSettings = async () => {
  savingCrm.value = true
  try {
    await saveAdminCrmSettings(crmSettings.value)
    showNotify('تنظیمات CRM با موفقیت ذخیره شد.')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ذخیره تنظیمات CRM', false)
  } finally {
    savingCrm.value = false
  }
}

const handleApproveClaim = async (claimId) => {
  try {
    await approveAdminClaim(claimId)
    pendingClaims.value = pendingClaims.value.filter(c => c.id !== claimId)
    showNotify('درخواست اتصال سرویس تایید شد ✓')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در تایید درخواست', false)
  }
}

const openRejectClaimModal = (claimId) => {
  rejectingClaimId.value = claimId
  rejectClaimReason.value = 'اشتراک در پنل یافت نشد یا معتبر نیست.'
  showRejectClaimModal.value = true
}

const handleConfirmRejectClaim = async () => {
  if (!rejectingClaimId.value) return
  try {
    await rejectAdminClaim(rejectingClaimId.value, rejectClaimReason.value)
    pendingClaims.value = pendingClaims.value.filter(c => c.id !== rejectingClaimId.value)
    showRejectClaimModal.value = false
    showNotify('درخواست اتصال سرویس رد شد.')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در رد درخواست', false)
  }
}

// ─── Guides Handlers ─────────────────────────────────────────────────────────
const handleToggleGuides = async () => {
  try {
    const res = await toggleAdminGuides()
    guidesEnabled.value = res.data.enabled
    showNotify(`بخش راهنما ${guidesEnabled.value ? 'فعال' : 'غیرفعال'} شد.`)
  } catch (err) {
    showNotify('خطا در تغییر وضعیت راهنما', false)
  }
}

const handlePromptGuideBot = async (platform, appName = null) => {
  promptingBot.value = true
  try {
    const res = await promptAdminGuideBot(platform || activeGuidePlatform.value, appName)
    showNotify(res.data?.message || 'دستور ثبت راهنما به چت تلگرام شما ارسال شد.')
    if (res.data?.bot_username) {
      telegramBotUrl.value = `https://t.me/${res.data.bot_username}`
    }
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ارسال پیام به ربات تلگرام', false)
  } finally {
    promptingBot.value = false
  }
}

const openAddGuideModal = () => {
  const defaultApps = {
    android: 'V2RayNG',
    ios: 'Streisand',
    windows: 'v2rayN',
    macos: 'V2rayU',
    linux: 'v2rayA'
  }
  guideForm.value = {
    platform: activeGuidePlatform.value,
    app_name: defaultApps[activeGuidePlatform.value] || 'V2RayNG',
    title: '',
    body: '',
    media_type: 'TEXT',
    media_file_id: '',
    sort_order: 100
  }
  showAddGuideModal.value = true
}

const handleSaveGuide = async () => {
  const bodyText = (guideForm.value.body || guideForm.value.title || '').trim()
  if (!bodyText) {
    showNotify('متن راهنما نمی‌تواند خالی باشد.', false)
    return
  }
  guideForm.value.body = bodyText
  try {
    await createAdminGuide(guideForm.value)
    showNotify('آموزش جدید با موفقیت ثبت شد.')
    showAddGuideModal.value = false
    const res = await getAdminGuides()
    guidesList.value = res.data?.items || []
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ثبت آموزش', false)
  }
}

const handleDeleteGuide = async (itemId) => {
  if (!confirm('آیا از حذف این آموزش اطمینان دارید؟')) return
  try {
    await deleteAdminGuide(itemId)
    guidesList.value = guidesList.value.filter(g => g.id !== itemId)
    showNotify('آموزش حذف شد.')
  } catch (err) {
    showNotify('خطا در حذف آموزش', false)
  }
}

const copiedFileId = ref('')
const copyFileId = async (id) => {
  if (!id) return
  try {
    await navigator.clipboard.writeText(id)
    copiedFileId.value = id
    setTimeout(() => {
      if (copiedFileId.value === id) copiedFileId.value = ''
    }, 2000)
  } catch (e) {
    console.error('Failed to copy', e)
  }
}

const getGuideMediaUrl = (item) => {
  if (item?.media_url) return item.media_url
  if (!item?.media_file_id) return ''
  const fid = item.media_file_id.trim()
  if (fid.startsWith('http://') || fid.startsWith('https://')) {
    return fid
  }
  return `/api/guides/${item.id}/media`
}

// ─── Audit Log Handlers ──────────────────────────────────────────────────────
const handleSaveAuditSettings = async () => {
  savingAudit.value = true
  try {
    await saveAdminAuditSettings(auditSettings.value)
    showNotify('تنظیمات حسابرسی ذخیره شد.')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ذخیره تنظیمات حسابرسی', false)
  } finally {
    savingAudit.value = false
  }
}

const loadAuditEvents = async () => {
  try {
    const res = await getAdminAudit()
    auditEvents.value = res.data?.events || []
    showNotify('لاگ‌های حسابرسی بروزرسانی شدند.')
  } catch (err) {
    showNotify('خطا در دریافت لاگ‌ها', false)
  }
}

// ─── Snapshot Handlers ───────────────────────────────────────────────────────
const handleGetSnapshot = async () => {
  loadingSnapshot.value = true
  try {
    const res = await getAdminSnapshot()
    snapshotInfo.value = res.data?.snapshot || res.data
    showNotify('اطلاعات اسنپ‌شات دریافت شد.')
  } catch (err) {
    showNotify('خطا در دریافت اسنپ‌شات', false)
  } finally {
    loadingSnapshot.value = false
  }
}

const handleSendSnapshot = async () => {
  sendingSnapshot.value = true
  try {
    const res = await sendAdminSnapshot()
    showNotify(res.data?.message || 'فایل اسنپ‌شات به چت تلگرام ارسال شد 📤')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ارسال اسنپ‌شات به تلگرام', false)
  } finally {
    sendingSnapshot.value = false
  }
}

// ─── Notifications Check Handler ─────────────────────────────────────────────
const handleCheckNotificationsNow = async () => {
  checkingNotifications.value = true
  try {
    const res = await checkAdminNotifications()
    showNotify(res.data?.message || 'بررسی سرویس‌ها و ارسال اعلان‌ها انجام شد ✓')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در بررسی اعلان‌ها', false)
  } finally {
    checkingNotifications.value = false
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
      card_photo: paymentsConfig.value.card.card_photo || '',
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
    await saveAdminBranding({
      webapp_title: uiTitle.value.trim(),
      customer_menu: customerMenu.value
    })
    auth.setAppTitle(uiTitle.value.trim())
    showNotify('تنظیمات عنوان و منوی مشتریان ذخیره شد.')
  } catch (err) {
    showNotify(err.response?.data?.detail || 'خطا در ذخیره عنوان', false)
  } finally {
    savingBranding.value = false
  }
}

// ─── Sanaei 3x-ui Handlers ──────────────────────────────────────────────────
const handleReconcileGroups = async () => {
  loadingXui.value = true
  try {
    const res = await reconcileAdminXuiGroups()
    showNotify(`همگام‌سازی گروه‌ها با موفقیت انجام شد ✓ (${res.data?.result?.updated || 0} کلاینت)`)
    const gRes = await getAdminXuiGroups()
    xuiGroups.value = gRes.data?.groups || []
  } catch (e) {
    showNotify(e.response?.data?.detail || 'خطا در همگام‌سازی گروه‌ها', false)
  } finally {
    loadingXui.value = false
  }
}

const handleRunXuiDiag = async () => {
  runningDiag.value = true
  xuiDiagResult.value = 'در حال تست ارتباط...'
  try {
    const res = await testAdminXui()
    xuiDiagResult.value = res.data?.result || 'تستی دریافت نشد.'
  } catch (e) {
    xuiDiagResult.value = '❌ خطا در تست ارتباط: ' + (e.response?.data?.detail || e.message)
  } finally {
    runningDiag.value = false
  }
}

const handleReplaceDomain = async () => {
  if (!domainForm.value.old_domain || !domainForm.value.new_domain) return
  replacingDomain.value = true
  try {
    const res = await replaceAdminDomain(domainForm.value.old_domain, domainForm.value.new_domain)
    showNotify(res.data?.message || 'تعویض دامنه با موفقیت انجام شد ✓')
    domainForm.value = { old_domain: '', new_domain: '' }
  } catch (e) {
    showNotify(e.response?.data?.detail || 'خطا در تعویض دامنه', false)
  } finally {
    replacingDomain.value = false
  }
}

const handleDeleteClient = async () => {
  if (!deleteClientEmail.value.trim()) return
  if (!confirm(`آیا از حذف اشتراک ${deleteClientEmail.value} از پنل اطمینان دارید؟`)) return
  deletingClient.value = true
  try {
    const res = await deleteAdminPanelClient(deleteClientEmail.value.trim())
    showNotify(res.data?.message || 'اشتراک از پنل حذف شد ✓')
    deleteClientEmail.value = ''
  } catch (e) {
    showNotify(e.response?.data?.detail || 'خطا در حذف اشتراک', false)
  } finally {
    deletingClient.value = false
  }
}

// ─── Rewards Handlers ────────────────────────────────────────────────────────
const handleSaveCashback = async () => {
  savingCashback.value = true
  try {
    await saveAdminCashback(rewardsData.value.cashback_percent)
    showNotify('درصد کش‌بک با موفقیت ذخیره شد.')
  } catch (e) {
    showNotify(e.response?.data?.detail || 'خطا در ذخیره کش‌بک', false)
  } finally {
    savingCashback.value = false
  }
}

const handleCreateDiscount = async () => {
  if (!discountForm.value.code) return
  try {
    await createAdminDiscount(discountForm.value)
    showNotify('کد تخفیف جدید ایجاد شد.')
    showDiscountModal.value = false
    discountForm.value = { code: '', discount_type: 'PERCENT', value: 10, min_purchase: 0, max_uses: 0, per_user_limit: 1 }
    const rRes = await getAdminRewards()
    if (rRes?.data) rewardsData.value = { ...rewardsData.value, ...rRes.data }
  } catch (e) {
    showNotify(e.response?.data?.detail || 'خطا در ایجاد کد تخفیف', false)
  }
}

const handleDeleteDiscount = async (code) => {
  if (!confirm(`آیا از حذف کد تخفیف ${code} اطمینان دارید؟`)) return
  try {
    await deleteAdminDiscount(code)
    showNotify('کد تخفیف حذف شد.')
    const rRes = await getAdminRewards()
    if (rRes?.data) rewardsData.value = { ...rewardsData.value, ...rRes.data }
  } catch (e) {
    showNotify(e.response?.data?.detail || 'خطا در حذف کد تخفیف', false)
  }
}

const handleCreateGift = async () => {
  if (!giftForm.value.code) return
  try {
    await createAdminGift(giftForm.value)
    showNotify('کد هدیه جدید ایجاد شد.')
    showGiftModal.value = false
    giftForm.value = { code: '', amount: 10000, max_uses: 1 }
    const rRes = await getAdminRewards()
    if (rRes?.data) rewardsData.value = { ...rewardsData.value, ...rRes.data }
  } catch (e) {
    showNotify(e.response?.data?.detail || 'خطا در ایجاد کد هدیه', false)
  }
}

const handleDeleteGift = async (code) => {
  if (!confirm(`آیا از حذف کد هدیه ${code} اطمینان دارید؟`)) return
  try {
    await deleteAdminGift(code)
    showNotify('کد هدیه حذف شد.')
    const rRes = await getAdminRewards()
    if (rRes?.data) rewardsData.value = { ...rewardsData.value, ...rRes.data }
  } catch (e) {
    showNotify(e.response?.data?.detail || 'خطا در حذف کد هدیه', false)
  }
}

// ─── Affiliate Handlers ──────────────────────────────────────────────────────
const handleSaveAffiliate = async () => {
  savingAffiliate.value = true
  try {
    await saveAdminAffiliate({
      enabled: affiliateData.value.enabled,
      percent: affiliateData.value.percent,
    })
    showNotify('تنظیمات همکاری در فروش ذخیره شد.')
  } catch (e) {
    showNotify(e.response?.data?.detail || 'خطا در ذخیره تنظیمات همکاری', false)
  } finally {
    savingAffiliate.value = false
  }
}

// ─── Content & Security Handlers ─────────────────────────────────────────────
const handleSaveContentSecurity = async () => {
  savingContentSec.value = true
  try {
    await saveAdminContentSecurity(contentSecurity.value)
    showNotify('تنظیمات متن‌ها و امنیت ذخیره شد.')
  } catch (e) {
    showNotify(e.response?.data?.detail || 'خطا در ذخیره متن‌ها و امنیت', false)
  } finally {
    savingContentSec.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>
