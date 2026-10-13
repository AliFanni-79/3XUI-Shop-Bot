<template>
  <div class="space-y-4">
    <div class="flex items-center gap-2">
      <span class="text-xl">📖</span>
      <h2 class="text-sm font-bold">راهنمای اتصال و نرم‌افزارها</h2>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="py-12 flex justify-center">
      <div class="w-6 h-6 border-2 border-tg-button border-t-transparent rounded-full animate-spin"></div>
    </div>

    <!-- Guides List -->
    <div v-else-if="guides.length" class="space-y-3">
      <div
        v-for="guide in guides"
        :key="guide.id"
        class="bg-tg-sec rounded-2xl p-4 border border-gray-700/30 space-y-2"
      >
        <div class="flex justify-between items-center">
          <span class="font-bold text-xs bg-tg px-2.5 py-1 rounded-lg border border-gray-700/40">
            {{ formatPlatform(guide.platform) }}
          </span>
          <span class="text-[10px] text-tg-hint">{{ guide.media_type }}</span>
        </div>

        <p class="text-xs text-tg/90 leading-relaxed whitespace-pre-line">
          {{ guide.body }}
        </p>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-12 bg-tg-sec/50 rounded-2xl border border-dashed border-gray-700/40">
      <p class="text-xs text-tg-hint">راهنمایی ثبت نشده است. از پشتیبانی چت تلگرام کمک بگیرید.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getGuides } from '@/api'

const guides = ref([])
const loading = ref(true)

const formatPlatform = (p) => {
  const map = {
    ANDROID: '📱 اندروید (V2rayNG)',
    IOS: '🍏 آیفون (Streisand / V2Box)',
    WINDOWS: '💻 ویندوز (v2rayN)',
    MAC: '🖥 مک (V2rayU / FoXray)',
    LINUX: '🐧 لینوکس'
  }
  return map[p?.toUpperCase()] || p
}

onMounted(async () => {
  try {
    const { data } = await getGuides()
    guides.value = data.guides || []
  } catch (err) {
    console.error('Failed to load guides:', err)
  } finally {
    loading.value = false
  }
})
</script>
