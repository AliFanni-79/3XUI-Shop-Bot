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
      <!-- Free Monthly Trial Card -->
      <div
        v-if="trialInfo && trialInfo.enabled"
        class="bg-gradient-to-br from-emerald-950/40 via-tg-sec to-tg-sec rounded-2xl p-4 border border-emerald-500/30 shadow-sm flex flex-col justify-between hover:border-emerald-500/50 transition relative overflow-hidden"
      >
        <div class="absolute -top-6 -left-6 w-20 h-20 bg-emerald-500/10 rounded-full blur-xl pointer-events-none"></div>

        <div>
          <div class="flex justify-between items-start mb-2">
            <div class="flex items-center gap-2">
              <span class="text-xl">🎁</span>
              <div>
                <div class="flex items-center gap-2">
                  <h3 class="font-bold text-sm text-tg">{{ trialInfo.name || 'تست رایگان ۱ روزه' }}</h3>
                  <span class="text-[10px] bg-emerald-500/20 text-emerald-400 font-bold px-2 py-0.5 rounded-full border border-emerald-500/30">
                    هدیه ماهانه
                  </span>
                </div>
                <span class="text-[10px] text-tg-hint block mt-0.5">
                  سهمیه هر کاربر: یک‌بار در ماه (هر ۳۰ روز)
                </span>
              </div>
            </div>
            <span class="text-xs bg-emerald-500/20 text-emerald-300 font-bold px-2.5 py-0.5 rounded-full border border-emerald-500/30">
              {{ trialInfo.volume_display || '300 مگابایت' }}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-2 text-xs text-tg-hint my-3">
            <div class="flex items-center gap-1.5 bg-tg/40 p-2 rounded-lg">
              <span>⏱</span>
              <span>مدت: {{ trialInfo.days || 1 }} روز</span>
            </div>
            <div class="flex items-center gap-1.5 bg-tg/40 p-2 rounded-lg">
              <span>👥</span>
              <span>کاربر: {{ trialInfo.ip_limit > 0 ? `${trialInfo.ip_limit} کاربر` : 'نامحدود' }}</span>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-between pt-2 border-t border-gray-700/30 mt-1">
          <div>
            <span class="text-xs text-tg-hint block">هزینه</span>
            <span class="text-sm font-bold text-emerald-400">رایگان (۰ تومان)</span>
          </div>

          <div v-if="trialInfo.eligible">
            <button
              @click="openTrialModal"
              class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-4 py-2 rounded-xl shadow active:scale-95 transition flex items-center gap-1.5"
            >
              <span>⚡️</span>
              <span>دریافت تست رایگان</span>
            </button>
          </div>
          <div v-else>
            <span class="text-[11px] text-tg-hint bg-tg/50 px-3 py-1.5 rounded-xl border border-gray-700/40 block text-center">
              {{ trialInfo.status === 'ACTIVE' ? 'سرویس تست فعال دارید' : `تست بعدی تا ${trialInfo.remaining_days} روز دیگر` }}
            </span>
          </div>
        </div>
      </div>

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

      <!-- 4. SERVER / INBOUND SELECTION -->
      <div v-if="builderConfig.servers && builderConfig.servers.length" class="bg-tg-sec rounded-2xl p-4 border border-gray-700/30 space-y-3">
        <div class="flex justify-between items-center">
          <label class="text-xs font-bold text-tg flex items-center gap-1.5">
            <span>🌐</span>
            <span>۴. انتخاب سرورها و موقعیت‌ها (Servers)</span>
          </label>
          <span class="text-[10px] text-tg-hint">{{ selectedServerIds.length ? selectedServerIds.length + ' سرور انتخاب شده' : 'پیش‌فرض (همه سرورها)' }}</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div
            v-for="server in builderConfig.servers"
            :key="server.id"
            @click="toggleServerSelection(server.id)"
            class="p-3 rounded-xl border transition cursor-pointer flex items-center justify-between"
            :class="selectedServerIds.includes(server.id) ? 'bg-tg-button/15 border-tg-button text-tg ring-1 ring-tg-button' : 'bg-tg border-gray-700/40 text-tg-hint hover:text-tg'"
          >
            <div class="space-y-0.5">
              <span class="font-bold text-xs block text-white">{{ server.name }}</span>
              <span v-if="server.contact_support" class="text-[10px] text-amber-300 font-bold block">
                💬 برای خرید به پشتیبانی مراجعه فرمایید
              </span>
              <span v-else class="text-[10px] text-emerald-400 font-medium block">
                {{ server.price > 0 ? `+${Number(server.price).toLocaleString('fa-IR')} تومان` : 'شامل پلن (رایگان)' }}
              </span>
            </div>
            <div
              class="w-5 h-5 rounded-lg border flex items-center justify-center text-xs transition"
              :class="selectedServerIds.includes(server.id) ? 'bg-tg-button border-tg-button text-white font-bold' : 'border-gray-600 bg-tg/40'"
            >
              <span v-if="selectedServerIds.includes(server.id)">✓</span>
            </div>
          </div>
        </div>

        <div v-if="hasSupportServerSelected" class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-300 flex items-center gap-2">
          <span>⚠️</span>
          <span>یکی از سرورهای انتخابی شما نیازمند هماهنگی با پشتیبانی است. امکان پرداخت آنلاین برای این سرور وجود ندارد.</span>
        </div>
      </div>

      <!-- 5. BRIEF SUMMARY & PRICE BREAKDOWN -->
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

          <div v-if="builderConfig.servers && builderConfig.servers.length" class="flex justify-between items-center">
            <span class="text-tg-hint">سرورهای انتخابی:</span>
            <span class="font-semibold" :class="hasSupportServerSelected ? 'text-amber-400' : ''">
              {{ hasSupportServerSelected ? 'نیاز به هماهنگی پشتیبانی' : (calculatedBrief.servers_price === 0 ? 'شامل پلن (رایگان)' : `+${Number(calculatedBrief.servers_price).toLocaleString('fa-IR')} تومان`) }}
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

        <div v-if="hasSupportServerSelected" class="pt-2">
          <button
            type="button"
            @click="handleSupportServerAction"
            class="w-full bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs py-3 rounded-xl shadow active:scale-95 transition flex items-center justify-center gap-2"
          >
            <span>{{ supportServerTarget?.support_target_type === 'link' ? 'ارتباط با پشتیبانی / کانال تلگرام 💬' : 'ارتباط با پشتیبانی داخلی ربات 📞' }}</span>
            <span>←</span>
          </button>
        </div>
        <button
          v-else
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
          <div v-if="appliedDiscount" class="flex justify-between">
            <span class="text-tg-hint">مبلغ اولیه:</span>
            <span class="line-through text-gray-500">{{ Number(activePlan.price).toLocaleString('fa-IR') }} تومان</span>
          </div>
          <div v-if="appliedDiscount" class="flex justify-between text-emerald-400">
            <span>تخفیف اعمال‌شده ({{ appliedDiscount.code }}):</span>
            <span class="font-bold">-{{ Number(appliedDiscount.discount_amount).toLocaleString('fa-IR') }} تومان</span>
          </div>
          <div class="flex justify-between" :class="appliedDiscount ? 'border-t border-gray-700/30 pt-1' : ''">
            <span class="text-tg-hint">مبلغ قابل پرداخت:</span>
            <span class="font-bold text-emerald-400 text-sm">{{ Number(finalPayablePrice).toLocaleString('fa-IR') }} تومان</span>
          </div>
        </div>

        <!-- Custom Config/Service Name Input -->
        <div>
          <label class="block text-xs text-tg-hint mb-1">نام دلخواه کانفیگ (اختیاری):</label>
          <input
            v-model="customServiceName"
            type="text"
            dir="ltr"
            placeholder="مثلاً: phone, laptop (اختیاری)"
            class="w-full bg-tg border border-gray-700/50 rounded-xl px-3 py-2 text-xs text-center tracking-wider focus:outline-none focus:border-tg-button"
          />
        </div>

        <!-- Discount Code / Gift Code Input -->
        <div>
          <label class="block text-xs text-tg-hint mb-1">کد تخفیف یا هدیه (اختیاری):</label>
          <div class="flex gap-2">
            <input
              v-model="discountCode"
              :disabled="appliedDiscount != null"
              type="text"
              dir="ltr"
              placeholder="کد تخفیف یا هدیه"
              class="flex-1 bg-tg border border-gray-700/50 rounded-xl px-3 py-2 text-xs text-center uppercase tracking-wider focus:outline-none focus:border-tg-button disabled:opacity-50"
              @keyup.enter="handleApplyCode"
            />
            <button
              v-if="!appliedDiscount"
              type="button"
              @click="handleApplyCode"
              :disabled="!discountCode.trim() || checkingCode"
              class="px-4 py-2 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1 shrink-0"
              :class="discountCode.trim() && !checkingCode ? 'btn-tg shadow active:scale-95' : 'bg-gray-700/30 text-gray-500 cursor-not-allowed'"
            >
              <span v-if="checkingCode" class="w-3.5 h-3.5 border-2 border-white/60 border-t-transparent rounded-full animate-spin"></span>
              <span v-else>اعمال</span>
            </button>
            <button
              v-else
              type="button"
              @click="handleRemoveDiscount"
              class="px-3 py-2 rounded-xl text-xs font-semibold bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 transition shrink-0"
            >
              حذف ✕
            </button>
          </div>

          <!-- Code Feedback message -->
          <div v-if="codeResult" class="mt-2 p-2.5 rounded-xl text-xs flex items-start gap-2 animate-fadeIn" :class="codeResultClass">
            <span class="text-sm shrink-0">{{ codeResultIcon }}</span>
            <span class="leading-relaxed">{{ codeResult.message }}</span>
          </div>
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

    <!-- ===================================================================== -->
    <!-- FREE TRIAL ACTIVATION MODAL                                           -->
    <!-- ===================================================================== -->
    <div
      v-if="trialModalOpen"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
      @click.self="closeTrialModal"
    >
      <div class="bg-tg-sec w-full max-w-sm rounded-2xl p-5 border border-gray-700/40 shadow-xl space-y-4">
        <div class="flex justify-between items-center pb-2 border-b border-gray-700/30">
          <h3 class="font-bold text-sm text-tg flex items-center gap-1.5">
            <span>🎁</span>
            <span>دریافت تست رایگان {{ trialInfo?.days ? trialInfo.days + ' روزه' : '' }}</span>
          </h3>
          <button @click="closeTrialModal" class="text-tg-hint hover:text-tg text-sm">✕</button>
        </div>

        <div class="space-y-3">
          <div class="bg-emerald-950/20 border border-emerald-500/20 rounded-xl p-3 text-xs text-tg space-y-1.5">
            <div class="flex justify-between font-semibold">
              <span>حجم هدیه:</span>
              <span class="text-emerald-400 font-bold">
                {{ trialInfo?.volume_display || (trialInfo?.volume_gb >= 1 ? trialInfo.volume_gb + ' گیگابایت' : (trialInfo?.volume_gb ? Math.round(trialInfo.volume_gb * 1024) + ' مگابایت' : '۳۰۰ مگابایت')) }}
              </span>
            </div>
            <div class="flex justify-between font-semibold">
              <span>مدت اعتبار:</span>
              <span>{{ trialInfo?.days ? trialInfo.days + ' روز' : '۱ روز' }}</span>
            </div>
            <div class="flex justify-between font-semibold">
              <span>محدودیت کاربر:</span>
              <span>{{ trialInfo?.ip_limit > 0 ? trialInfo.ip_limit + ' کاربر' : 'نامحدود' }}</span>
            </div>
            <div class="flex justify-between font-semibold pt-1 border-t border-emerald-500/20">
              <span>هزینه:</span>
              <span class="text-emerald-400 font-bold">۰ تومان (کاملاً رایگان)</span>
            </div>
          </div>

          <div>
            <label class="block text-xs text-tg-hint mb-1">نام دلخواه کانفیگ (اختیاری):</label>
            <input
              v-model="trialServiceName"
              type="text"
              dir="ltr"
              placeholder="مثلاً: test-phone, trial"
              class="w-full bg-tg border border-gray-700/50 rounded-xl px-3 py-2 text-xs text-center tracking-wider focus:outline-none focus:border-emerald-500"
            />
          </div>

          <p class="text-[11px] text-tg-hint">
            ⚠️ هر کاربر می‌تواند در هر ماه (هر ۳۰ روز) یک‌بار این تست رایگان را دریافت کند.
          </p>

          <div
            v-if="trialMessage"
            class="p-2.5 rounded-xl text-xs text-center border"
            :class="trialSuccess ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'bg-red-500/15 text-red-400 border-red-500/30'"
          >
            {{ trialMessage }}
          </div>

          <button
            @click="claimTrial"
            :disabled="submittingTrial"
            class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 rounded-xl text-xs shadow active:scale-95 transition disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <span v-if="submittingTrial" class="inline-block animate-spin">⏳</span>
            <span>{{ submittingTrial ? 'در حال فعال‌سازی...' : 'تأیید و فعال‌سازی تست رایگان' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  getPlans,
  getBuilderConfig,
  initCardOrder,
  initWalletOrder,
  initCustomCardOrder,
  initCustomWalletOrder,
  getActiveGateways,
  initGatewayOrder,
  initStarsOrder,
  claimFreeTrial,
  applyOrCheckCode
} from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

// State
const activeMode = ref('catalog') // 'catalog' | 'builder'
const categories = ref([])
const selectedCategoryId = ref(null)
const trialInfo = ref(null)
const trialModalOpen = ref(false)
const trialServiceName = ref('')
const submittingTrial = ref(false)
const trialMessage = ref('')
const trialSuccess = ref(false)
const activeGateways = ref({ card: true, wallet: true, zibal: false, zarinpal: false, stars: false, stars_rate: 1500 })

// Builder state
const selectedMonths = ref(1) // 1, 3, 6, 12
const isUnlimitedTraffic = ref(false)
const selectedGb = ref(50) // 5 .. 500
const selectedUsers = ref(1) // 1, 2, 3, 4, 5, 0 (unlimited)
const selectedServerIds = ref([])

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
  user_costs: { 1: 0, 2: 20000, 3: 35000, 4: 45000, 5: 50000, 0: 65000 },
  servers: []
})

// Checkout Modal state
const activePlan = ref(null)
const modalPrice = computed(() => Number(activePlan.value?.price || 0))
const isCustomPlan = ref(false)
const customServiceName = ref('')
const discountCode = ref('')
const submitting = ref(false)
const message = ref('')
const isSuccess = ref(false)

const checkingCode = ref(false)
const appliedDiscount = ref(null)
const codeResult = ref(null)

const finalPayablePrice = computed(() => {
  const base = Number(activePlan.value?.price || 0)
  if (appliedDiscount.value?.discount_amount) {
    return Math.max(0, base - appliedDiscount.value.discount_amount)
  }
  return base
})

const codeResultClass = computed(() => {
  if (!codeResult.value) return ''
  if (codeResult.value.type === 'error') return 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
  if (codeResult.value.type === 'gift') return 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
  return 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
})

const codeResultIcon = computed(() => {
  if (!codeResult.value) return ''
  if (codeResult.value.type === 'error') return '❌'
  if (codeResult.value.type === 'gift') return '🎁'
  return '🏷'
})

const handleApplyCode = async () => {
  const code = discountCode.value.trim()
  if (!code || checkingCode.value) return

  checkingCode.value = true
  codeResult.value = null

  try {
    const res = await applyOrCheckCode(code, activePlan.value?.price || 0)
    const data = res.data
    if (data.type === 'gift') {
      auth.balance = data.new_balance
      codeResult.value = {
        type: 'gift',
        message: data.message || `کد هدیه با موفقیت اعمال شد و مبلغ ${Number(data.amount).toLocaleString('fa-IR')} تومان به کیف پول اضافه شد.`
      }
      discountCode.value = ''
      appliedDiscount.value = null
    } else if (data.type === 'discount') {
      appliedDiscount.value = {
        code: data.code,
        discount_amount: data.discount_amount,
        final_price: data.final_price
      }
      codeResult.value = {
        type: 'discount',
        message: data.message || `کد تخفیف ${data.code} با موفقیت اعمال شد.`
      }
    }
  } catch (err) {
    codeResult.value = {
      type: 'error',
      message: err.response?.data?.detail || 'کد وارد شده معتبر نیست یا منقضی شده است.'
    }
  } finally {
    checkingCode.value = false
  }
}

const handleRemoveDiscount = () => {
  appliedDiscount.value = null
  discountCode.value = ''
  codeResult.value = null
}

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

const selectedServersList = computed(() => {
  const servers = builderConfig.value.servers || []
  return servers.filter(s => selectedServerIds.value.includes(s.id))
})

const serversPrice = computed(() => {
  return selectedServersList.value.reduce((acc, s) => acc + (s.price || 0), 0)
})

const hasSupportServerSelected = computed(() => {
  return selectedServersList.value.some(s => s.contact_support)
})

const supportServerTarget = computed(() => {
  return selectedServersList.value.find(s => s.contact_support) || null
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

  // Servers
  const sPrice = serversPrice.value

  const total = durFinal + trafFinal + uCost + sPrice

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
    servers_price: sPrice,
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
  appliedDiscount.value = null
  codeResult.value = null
  checkingCode.value = false
}

const toggleServerSelection = (id) => {
  const idx = selectedServerIds.value.indexOf(id)
  if (idx > -1) {
    selectedServerIds.value.splice(idx, 1)
  } else {
    selectedServerIds.value.push(id)
  }
}

const handleSupportServerAction = () => {
  const target = supportServerTarget.value
  if (!target) return
  if (target.support_target_type === 'link' && target.support_target_url) {
    let url = target.support_target_url.trim()
    if (!url.startsWith('http://') && !url.startsWith('https://') && !url.startsWith('tg://')) {
      if (url.startsWith('@')) {
        url = `https://t.me/${url.slice(1)}`
      } else {
        url = `https://t.me/${url}`
      }
    }
    if (window.Telegram?.WebApp?.openTelegramLink && (url.startsWith('https://t.me/') || url.startsWith('tg://'))) {
      window.Telegram.WebApp.openTelegramLink(url)
    } else if (window.Telegram?.WebApp?.openLink) {
      window.Telegram.WebApp.openLink(url)
    } else {
      window.open(url, '_blank')
    }
  } else {
    // Built-in bot support section
    const botUser = window.Telegram?.WebApp?.initDataUnsafe?.bot_username || ''
    if (botUser && window.Telegram?.WebApp?.openTelegramLink) {
      window.Telegram.WebApp.openTelegramLink(`https://t.me/${botUser}?start=support_server_${target.id}`)
    } else if (window.Telegram?.WebApp?.close) {
      window.Telegram.WebApp.close()
    } else {
      router.push('/support')
    }
  }
}

const openCustomCheckoutModal = () => {
  const brief = calculatedBrief.value
  const trafLabel = brief.traffic.is_unlimited ? 'نامحدود' : `${brief.traffic.volume_gb} گیگ`
  const userLabel = brief.user_limit.ip_limit === 0 ? 'نامحدود' : `${brief.user_limit.ip_limit} کاربر`
  const serverNames = selectedServersList.value.map(s => s.name).join('، ')
  const serversLabel = serverNames ? ` - سرور: ${serverNames}` : ''
  const planName = `پلن اختصاصی | ${brief.duration.months} ماهه - ${trafLabel} - ${userLabel}${serversLabel}`

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
  customServiceName.value = ''
  discountCode.value = ''
  appliedDiscount.value = null
  codeResult.value = null
  checkingCode.value = false
}

const payCard = async () => {
  submitting.value = true
  message.value = ''
  try {
    const sName = customServiceName.value.trim() || null
    const effCode = appliedDiscount.value ? appliedDiscount.value.code : (discountCode.value.trim() || null)
    if (isCustomPlan.value) {
      await initCustomCardOrder(
        selectedMonths.value,
        isUnlimitedTraffic.value ? 0 : selectedGb.value,
        selectedUsers.value,
        effCode,
        sName,
        selectedServerIds.value.length ? selectedServerIds.value : null
      )
    } else {
      await initCardOrder(activePlan.value.id, effCode, sName)
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
    const sName = customServiceName.value.trim() || null
    const effCode = appliedDiscount.value ? appliedDiscount.value.code : (discountCode.value.trim() || null)
    if (isCustomPlan.value) {
      await initCustomWalletOrder(
        selectedMonths.value,
        isUnlimitedTraffic.value ? 0 : selectedGb.value,
        selectedUsers.value,
        effCode,
        sName,
        selectedServerIds.value.length ? selectedServerIds.value : null
      )
    } else {
      await initWalletOrder(activePlan.value.id, effCode, sName)
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
    const sName = customServiceName.value.trim() || null
    const effCode = appliedDiscount.value ? appliedDiscount.value.code : (discountCode.value.trim() || null)
    let payload
    if (isCustomPlan.value) {
      payload = {
        gateway: gatewayName,
        months: selectedMonths.value,
        volume_gb: isUnlimitedTraffic.value ? 0 : selectedGb.value,
        ip_limit: selectedUsers.value,
        discount_code: effCode,
        custom_name: sName,
        server_ids: selectedServerIds.value.length ? selectedServerIds.value : null
      }
    } else {
      payload = {
        gateway: gatewayName,
        plan_id: activePlan.value.id,
        discount_code: effCode,
        custom_name: sName
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
    const sName = customServiceName.value.trim() || null
    const effCode = appliedDiscount.value ? appliedDiscount.value.code : (discountCode.value.trim() || null)
    let payload
    if (isCustomPlan.value) {
      payload = {
        custom_spec: {
          months: selectedMonths.value,
          volume_gb: isUnlimitedTraffic.value ? 0 : selectedGb.value,
          ip_limit: selectedUsers.value,
          server_ids: selectedServerIds.value.length ? selectedServerIds.value : null
        },
        discount_code: effCode,
        custom_name: sName
      }
    } else {
      payload = {
        plan_id: activePlan.value.id,
        discount_code: effCode,
        custom_name: sName
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

const openTrialModal = () => {
  trialModalOpen.value = true
  trialServiceName.value = ''
  trialMessage.value = ''
  trialSuccess.value = false
}

const closeTrialModal = () => {
  trialModalOpen.value = false
  submittingTrial.value = false
}

const claimTrial = async () => {
  submittingTrial.value = true
  trialMessage.value = ''
  try {
    const sName = trialServiceName.value.trim() || null
    await claimFreeTrial(sName)
    trialSuccess.value = true
    trialMessage.value = '🎉 تست رایگان با موفقیت فعال شد! در حال انتقال به بخش سرویس‌ها...'
    if (trialInfo.value) {
      trialInfo.value.eligible = false
      trialInfo.value.status = 'ACTIVE'
      trialInfo.value.remaining_days = 30
    }
    setTimeout(() => {
      trialModalOpen.value = false
      router.push('/services')
    }, 1200)
  } catch (err) {
    trialSuccess.value = false
    trialMessage.value = err.response?.data?.detail || 'خطا در فعال‌سازی تست رایگان'
  } finally {
    submittingTrial.value = false
  }
}

const applyRouteParams = () => {
  const query = route.query
  if (!query || Object.keys(query).length === 0) return

  if (query.mode === 'builder') {
    activeMode.value = 'builder'
    if (query.months) {
      const m = Number(query.months)
      if ([1, 3, 6, 12].includes(m)) selectedMonths.value = m
    }
    if (query.volume !== undefined) {
      const v = Number(query.volume)
      if (v === 0) {
        isUnlimitedTraffic.value = true
      } else if (v > 0) {
        isUnlimitedTraffic.value = false
        selectedGb.value = v
      }
    }
    if (query.ip !== undefined) {
      const ip = Number(query.ip)
      if ([0, 1, 2, 3, 4, 5].includes(ip)) selectedUsers.value = ip
    }
  } else if (query.mode === 'catalog' || query.plan_id) {
    activeMode.value = 'catalog'
    if (query.category_id) {
      const catId = Number(query.category_id)
      if (categories.value.some(c => c.id === catId)) {
        selectedCategoryId.value = catId
      }
    }
    if (query.plan_id) {
      const targetPid = Number(query.plan_id)
      for (const cat of categories.value) {
        const found = (cat.plans || []).find(p => p.id === targetPid)
        if (found) {
          selectedCategoryId.value = cat.id
          openCheckoutModal(found)
          break
        }
      }
    }
  }
}

watch(
  () => route.query,
  () => {
    applyRouteParams()
  },
  { deep: true }
)

onMounted(async () => {
  try {
    const [pRes, bRes, gRes] = await Promise.all([
      getPlans(),
      getBuilderConfig().catch(() => null),
      getActiveGateways().catch(() => null)
    ])
    categories.value = pRes.data.categories || []
    if (pRes.data?.trial_info) {
      trialInfo.value = pRes.data.trial_info
    }
    if (categories.value.length) {
      selectedCategoryId.value = categories.value[0].id
    }
    if (bRes && bRes.data) {
      builderConfig.value = { ...builderConfig.value, ...bRes.data }
    }
    if (gRes && gRes.data) {
      activeGateways.value = { ...activeGateways.value, ...gRes.data }
    }

    applyRouteParams()
  } catch (err) {
    console.error('Failed to load store data:', err)
  }
})
</script>
