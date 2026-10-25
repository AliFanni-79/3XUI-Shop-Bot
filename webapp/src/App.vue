<template>
  <div class="min-h-screen bg-tg text-tg flex flex-col font-sans select-none pb-20">
    <!-- Header -->
    <header class="sticky top-0 z-30 bg-tg-sec border-b border-gray-700/30 px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-full bg-tg-button flex items-center justify-center font-bold text-white shadow">
          🚀
        </div>
        <div>
          <h1 class="text-sm font-bold leading-tight">{{ auth.appTitle || 'فروشگاه' }}</h1>
          <p class="text-xs text-tg-hint" v-if="auth.user">
            {{ auth.user.first_name }}
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <router-link
          v-if="auth.isAdmin"
          to="/admin"
          class="text-xs px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 font-medium hover:bg-amber-500/30 transition"
        >
          ⚙️ پنل ادمین
        </router-link>

        <div class="flex items-center gap-1 bg-tg px-2.5 py-1 rounded-full border border-gray-700/40 text-xs">
          <span>👛</span>
          <span class="font-semibold">{{ Number(auth.balance).toLocaleString('fa-IR') }}</span>
          <span class="text-tg-hint text-[10px]">تومان</span>
        </div>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="flex-1 p-4 max-w-lg w-full mx-auto">
      <div v-if="auth.loading" class="flex flex-col items-center justify-center py-20 gap-3">
        <div class="w-8 h-8 border-3 border-tg-button border-t-transparent rounded-full animate-spin"></div>
        <p class="text-xs text-tg-hint">در حال همگام‌سازی اطلاعات...</p>
      </div>

      <router-view v-else />
    </main>

    <!-- Bottom Navigation Bar -->
    <nav class="fixed bottom-0 left-0 right-0 z-40 bg-tg-sec border-t border-gray-700/30 px-2 py-1.5 flex justify-around items-center max-w-lg mx-auto">
      <router-link
        to="/"
        class="flex flex-col items-center py-1 px-3 rounded-xl transition text-xs"
        :class="$route.path === '/' ? 'text-tg-button font-bold' : 'text-tg-hint hover:text-tg'"
      >
        <span class="text-lg">🛍</span>
        <span>فروشگاه</span>
      </router-link>

      <router-link
        to="/services"
        class="flex flex-col items-center py-1 px-3 rounded-xl transition text-xs"
        :class="$route.path === '/services' ? 'text-tg-button font-bold' : 'text-tg-hint hover:text-tg'"
      >
        <span class="text-lg">📡</span>
        <span>سرویس‌های من</span>
      </router-link>

      <router-link
        to="/wallet"
        class="flex flex-col items-center py-1 px-3 rounded-xl transition text-xs"
        :class="$route.path === '/wallet' ? 'text-tg-button font-bold' : 'text-tg-hint hover:text-tg'"
      >
        <span class="text-lg">👛</span>
        <span>کیف پول</span>
      </router-link>

      <router-link
        to="/referral"
        class="flex flex-col items-center py-1 px-3 rounded-xl transition text-xs"
        :class="$route.path === '/referral' ? 'text-tg-button font-bold' : 'text-tg-hint hover:text-tg'"
      >
        <span class="text-lg">🤝</span>
        <span>دعوت دوستان</span>
      </router-link>

      <router-link
        v-if="auth.guidesEnabled"
        to="/guides"
        class="flex flex-col items-center py-1 px-3 rounded-xl transition text-xs"
        :class="$route.path === '/guides' ? 'text-tg-button font-bold' : 'text-tg-hint hover:text-tg'"
      >
        <span class="text-lg">📖</span>
        <span>راهنما</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

onMounted(async () => {
  await auth.fetchMe()
})
</script>
