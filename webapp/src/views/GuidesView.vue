<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span class="text-xl">📖</span>
        <h2 class="text-sm font-bold">راهنمای اتصال و نرم‌افزارها</h2>
      </div>
      <span v-if="!loading && guides.length" class="text-[11px] text-tg-hint bg-tg-sec px-2 py-0.5 rounded-full border border-gray-700/40">
        {{ filteredGuides.length }} آموزش
      </span>
    </div>

    <!-- Platform Filter Pills -->
    <div v-if="!loading && guides.length" class="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none text-xs">
      <button
        v-for="p in platforms"
        :key="p.id"
        @click="selectPlatform(p.id)"
        class="px-3 py-1.5 rounded-xl whitespace-nowrap transition flex items-center gap-1 font-medium border text-[11px]"
        :class="selectedPlatform === p.id
          ? 'bg-tg-button text-white border-transparent shadow-sm'
          : 'bg-tg-sec text-tg-hint hover:text-tg border-gray-700/30'"
      >
        <span>{{ p.icon }}</span>
        <span>{{ p.label }}</span>
      </button>
    </div>

    <!-- App Sub-filter Pills (When current platform has multiple apps) -->
    <div v-if="availableApps.length > 1" class="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none text-xs">
      <button
        v-for="app in availableApps"
        :key="app"
        @click="selectedApp = app"
        class="px-2.5 py-1 rounded-lg whitespace-nowrap transition border text-[10px] font-medium"
        :class="selectedApp === app
          ? 'bg-blue-600 text-white border-transparent shadow-sm'
          : 'bg-tg-sec/80 text-tg-hint hover:text-tg border-gray-700/40'"
      >
        {{ app === 'all' ? 'همه برنامه‌ها' : app }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="py-12 flex justify-center">
      <div class="w-6 h-6 border-2 border-tg-button border-t-transparent rounded-full animate-spin"></div>
    </div>

    <!-- Guides List -->
    <div v-else-if="filteredGuides.length" class="space-y-3">
      <div
        v-for="guide in filteredGuides"
        :key="guide.id"
        class="bg-tg-sec rounded-2xl p-4 border border-gray-700/30 space-y-3"
      >
        <div class="flex justify-between items-center gap-2">
          <div class="flex items-center gap-1.5 flex-wrap">
            <span class="font-bold text-xs bg-tg px-2.5 py-1 rounded-lg border border-gray-700/40">
              {{ formatPlatform(guide.platform) }}
            </span>
            <span v-if="guide.app_name" class="font-bold text-xs bg-blue-500/20 text-blue-300 px-2.5 py-1 rounded-lg border border-blue-500/30">
              ⚡ {{ guide.app_name }}
            </span>
          </div>
          <span class="text-[10px] px-2 py-0.5 rounded-full font-mono shrink-0" :class="guide.media_type === 'VIDEO' ? 'bg-purple-500/20 text-purple-300' : (guide.media_type === 'PHOTO' ? 'bg-blue-500/20 text-blue-300' : 'bg-gray-700/30 text-tg-hint')">
            {{ guide.media_type }}
          </span>
        </div>

        <!-- Image Media -->
        <div
          v-if="guide.file_id && guide.media_type === 'PHOTO' && !failedMedia[guide.id]"
          class="rounded-xl overflow-hidden bg-black/40 border border-gray-700/40"
        >
          <img
            :src="getMediaUrl(guide)"
            :alt="formatPlatform(guide.platform)"
            class="w-full max-h-96 object-contain rounded-xl"
            loading="lazy"
            @error="handleMediaError(guide.id)"
          />
        </div>

        <!-- Video Media -->
        <div
          v-else-if="guide.file_id && guide.media_type === 'VIDEO' && !failedMedia[guide.id]"
          class="rounded-xl overflow-hidden bg-black/60 border border-gray-700/40"
        >
          <video
            controls
            playsinline
            preload="metadata"
            :src="getMediaUrl(guide)"
            class="w-full max-h-96 rounded-xl"
            @error="handleMediaError(guide.id)"
          ></video>
        </div>

        <!-- Media Error Fallback -->
        <div v-if="failedMedia[guide.id]" class="p-2.5 bg-amber-500/10 border border-amber-500/30 rounded-xl text-[11px] text-amber-300 flex items-center justify-between">
          <span>رسانه این راهنما به صورت مستقیم در دسترس نیست.</span>
          <span class="text-[10px] text-amber-400">مشاهده در تلگرام</span>
        </div>

        <!-- Guide Body Text -->
        <p v-if="guide.body" class="text-xs text-tg/90 leading-relaxed whitespace-pre-line">
          {{ guide.body }}
        </p>
      </div>
    </div>

    <!-- Empty State for Filter -->
    <div v-else-if="guides.length && !filteredGuides.length" class="text-center py-10 bg-tg-sec/50 rounded-2xl border border-dashed border-gray-700/40 space-y-2">
      <p class="text-xs text-tg-hint">برای فیلتر انتخاب شده راهنمایی ثبت نشده است.</p>
      <button @click="resetFilters" class="text-xs text-tg-button hover:underline">
        مشاهده همه راهنماها
      </button>
    </div>

    <!-- Empty State Global -->
    <div v-else class="text-center py-12 bg-tg-sec/50 rounded-2xl border border-dashed border-gray-700/40">
      <p class="text-xs text-tg-hint">راهنمایی ثبت نشده است. از پشتیبانی چت تلگرام کمک بگیرید.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getGuides } from '@/api'

const guides = ref([])
const loading = ref(true)
const selectedPlatform = ref('all')
const selectedApp = ref('all')
const failedMedia = ref({})

const platforms = [
  { id: 'all', label: 'همه', icon: '🌐' },
  { id: 'android', label: 'اندروید', icon: '📱' },
  { id: 'ios', label: 'آیفون', icon: '🍏' },
  { id: 'windows', label: 'ویندوز', icon: '💻' },
  { id: 'macos', label: 'مک', icon: '🖥' },
  { id: 'linux', label: 'لینوکس', icon: '🐧' },
]

const formatPlatform = (p) => {
  const map = {
    ANDROID: '📱 اندروید',
    IOS: '🍏 آیفون',
    WINDOWS: '💻 ویندوز',
    MAC: '🖥 مک',
    MACOS: '🖥 مک',
    LINUX: '🐧 لینوکس',
    TV: '📺 تلویزیون'
  }
  return map[p?.toUpperCase()] || p
}

const selectPlatform = (platId) => {
  selectedPlatform.value = platId
  selectedApp.value = 'all'
}

const resetFilters = () => {
  selectedPlatform.value = 'all'
  selectedApp.value = 'all'
}

const filteredByPlatform = computed(() => {
  if (selectedPlatform.value === 'all') return guides.value
  return guides.value.filter(g => (g.platform || '').toLowerCase() === selectedPlatform.value)
})

const availableApps = computed(() => {
  const list = filteredByPlatform.value
  const set = new Set()
  for (const g of list) {
    if (g.app_name) set.add(g.app_name.trim())
  }
  if (set.size > 0) {
    return ['all', ...Array.from(set)]
  }
  return []
})

const filteredGuides = computed(() => {
  let list = filteredByPlatform.value
  if (selectedApp.value !== 'all') {
    list = list.filter(g => (g.app_name || '').toLowerCase() === selectedApp.value.toLowerCase())
  }
  return list
})

const getMediaUrl = (guide) => {
  if (guide?.media_url) return guide.media_url
  if (!guide?.file_id) return ''
  const fid = guide.file_id.trim()
  if (fid.startsWith('http://') || fid.startsWith('https://')) {
    return fid
  }
  return `/api/guides/${guide.id}/media`
}

const handleMediaError = (guideId) => {
  failedMedia.value[guideId] = true
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
